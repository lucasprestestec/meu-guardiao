"""Contratação: solicitação do cliente, régua de status e backoffice mínimo.

    POST /v1/solicitacoes                       cliente solicita a contratação
    GET  /v1/solicitacoes/{id}                  cliente acompanha (o UUID é a chave de acesso)
    GET  /v1/backoffice/resumo                  contadores do painel
    GET  /v1/backoffice/solicitacoes            fila de trabalho
    GET  /v1/backoffice/solicitacoes/{id}       ficha da solicitação
    POST /v1/backoffice/solicitacoes/{id}/status  muda o status (dispara notificações)
    GET  /v1/backoffice/notificacoes/pendentes  caixa de saída (para o CRM enviar o WhatsApp)
    POST /v1/backoffice/notificacoes/{id}/enviada  confirma o envio de uma mensagem
    POST /v1/backoffice/notificacoes/enviar-email  despacha os e-mails pendentes (SMTP)
    POST /v1/backoffice/notificacoes/enviar-whatsapp  despacha os WhatsApps pendentes (CRM DeskComm)

O backoffice exige o cabeçalho X-Backoffice-Key igual à variável BACKOFFICE_KEY.
É uma proteção mínima de demonstração, não substitui login com perfis.
Sem BACKOFFICE_KEY definida, o backoffice fica desligado.
"""

from __future__ import annotations

import hmac
import json
import os
import re
import uuid
from datetime import date
from decimal import Decimal
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, BackgroundTasks, Depends, Header, HTTPException, Query, Request
from psycopg.rows import dict_row
from pydantic import BaseModel, ConfigDict, Field, field_validator

from .crm import crm_configurado, despachar_whatsapp
from .envio import despachar_emails, email_configurado
from .dps import (
    hash_dps, instantaneo, questionario_de, questionario_valido_para_producao, validar_respostas,
)
from .infra import conexao, permitir_ficticios
from .proposta import AZOS, COMUM, ICATU, PropostaIn, campos_da_seguradora, perfil_de, validar_proposta

router = APIRouter()

# ---------------------------------------------------------------------------
# Régua de status
# ---------------------------------------------------------------------------

REGUA = [
    ("RECEBIDA", "Solicitação recebida", "Recebemos o seu pedido."),
    ("EM_PREPARACAO", "Proposta em preparação", "Estamos montando a sua proposta."),
    ("AGUARDANDO_ASSINATURA", "Aguardando a sua assinatura",
     "Falta você assinar a proposta. O link chega ao seu e-mail."),
    ("ENVIADA", "Enviada à seguradora", "Sua proposta foi enviada à seguradora."),
    ("EM_ANALISE", "Em análise", "A seguradora está analisando as informações."),
    ("AGUARDANDO_PAGAMENTO", "Aguardando o pagamento",
     "Falta o pagamento. Ele é feito no ambiente da seguradora."),
    ("APROVADA", "Aprovada", "Você receberá a confirmação da aprovação."),
    ("EMITIDA", "Apólice emitida", "Sua apólice foi emitida."),
]
_POSICAO = {c: i for i, (c, _, _) in enumerate(REGUA)}
_POSICAO["PENDENCIA"] = _POSICAO["EM_ANALISE"]

# Estados em que quem precisa agir é o cliente, com data-limite (prazo_acao).
AGUARDANDO_CLIENTE = ("AGUARDANDO_ASSINATURA", "AGUARDANDO_PAGAMENTO")

TRANSICOES = {
    "RECEBIDA": {"EM_PREPARACAO", "CANCELADA"},
    "EM_PREPARACAO": {"AGUARDANDO_ASSINATURA", "ENVIADA", "PENDENCIA", "CANCELADA"},
    # A ordem real varia por seguradora (Icatu: assinatura -> análise -> pagamento; Azos: o
    # pagamento pode vir antes da aceitação), por isso há mais de uma saída.
    "AGUARDANDO_ASSINATURA": {"ENVIADA", "EM_ANALISE", "AGUARDANDO_PAGAMENTO", "RECUSADA", "CANCELADA"},
    "ENVIADA": {"EM_ANALISE", "PENDENCIA", "CANCELADA"},
    "EM_ANALISE": {"AGUARDANDO_PAGAMENTO", "APROVADA", "PENDENCIA", "RECUSADA", "CANCELADA"},
    "PENDENCIA": {"EM_PREPARACAO", "AGUARDANDO_ASSINATURA", "ENVIADA", "EM_ANALISE",
                  "AGUARDANDO_PAGAMENTO", "CANCELADA"},
    "AGUARDANDO_PAGAMENTO": {"APROVADA", "EMITIDA", "RECUSADA", "CANCELADA"},
    "APROVADA": {"AGUARDANDO_PAGAMENTO", "EMITIDA", "CANCELADA"},
    "EMITIDA": set(), "RECUSADA": set(), "CANCELADA": set(),
}

# De quem é a vez de agir — é o que ordena a fila do backoffice.
COM_QUEM = {
    "RECEBIDA": "NOS", "EM_PREPARACAO": "NOS", "PENDENCIA": "CLIENTE",
    "AGUARDANDO_ASSINATURA": "CLIENTE", "AGUARDANDO_PAGAMENTO": "CLIENTE",
    "ENVIADA": "SEGURADORA", "EM_ANALISE": "SEGURADORA", "APROVADA": "SEGURADORA",
    "EMITIDA": "FIM", "RECUSADA": "FIM", "CANCELADA": "FIM",
}

# {prazo} é preenchido só quando o backoffice informa a data-limite da seguradora.
MENSAGENS = {
    "RECEBIDA": "Oi, {nome}! Recebemos sua solicitação de contratação. "
                "Em breve enviaremos novas atualizações por aqui.",
    "EM_PREPARACAO": "{nome}, estamos montando a sua proposta.",
    "AGUARDANDO_ASSINATURA": "{nome}, falta a sua assinatura para a proposta seguir. A {seguradora} "
                             "enviou o link para o seu e-mail.{prazo}",
    "AGUARDANDO_PAGAMENTO": "{nome}, falta o pagamento para a proposta seguir. Ele é feito no "
                            "ambiente da {seguradora}, não aqui no nosso site.{prazo}",
    "ENVIADA": "{nome}, sua proposta foi enviada à {seguradora}.",
    "EM_ANALISE": "{nome}, a {seguradora} está analisando a sua proposta.",
    "PENDENCIA": "{nome}, precisamos de uma informação para continuar: {pendencia}",
    "APROVADA": "{nome}, sua proposta foi aprovada pela {seguradora}. Falta a emissão da apólice.",
    "EMITIDA": "{nome}, sua apólice foi emitida{numero}. A partir de agora você está protegido(a).",
    "RECUSADA": "{nome}, a {seguradora} não aceitou a proposta desta vez. Nossa equipe vai "
                "entrar em contato para explicar e apresentar alternativas.",
    "CANCELADA": "{nome}, sua solicitação foi cancelada.",
}

TEXTO_CONSENTIMENTOS = {
    "VERACIDADE": "Confirmo que as informações prestadas são verdadeiras.",
    "TRATAMENTO_DADOS": "Autorizo o tratamento dos meus dados para fins de cotação e contratação.",
    "TERMOS": "Li e concordo com os termos e condições.",
    "VALORES_SUJEITOS_ANALISE": "Entendo que os valores dependem da análise da seguradora.",
}
# Só exigido (e gravado) quando o cliente responde a DPS. TEXTO PROVISÓRIO: revisão da advogada pendente.
TEXTO_CONSENTIMENTO_DPS = {
    "DPS_CONFERENCIA": "Conferi as minhas respostas de saúde e confirmo que estão corretas e completas. "
                       "Entendo que omissão ou falsidade pode anular a proposta e a cobertura.",
}
VERSAO_TEXTOS = "2026-09-v1"


# ---------------------------------------------------------------------------
# Validação
# ---------------------------------------------------------------------------


def cpf_valido(cpf: str) -> bool:
    if len(cpf) != 11 or not cpf.isdigit() or cpf == cpf[0] * 11:
        return False
    for n in (9, 10):
        soma = sum(int(cpf[i]) * (n + 1 - i) for i in range(n))
        if int(cpf[n]) != (soma * 10 % 11) % 10:
            return False
    return True


def _idade(nasc: date, hoje: Optional[date] = None) -> int:
    hoje = hoje or date.today()
    return hoje.year - nasc.year - ((hoje.month, hoje.day) < (nasc.month, nasc.day))


class _Estrito(BaseModel):
    model_config = ConfigDict(extra="forbid")


class DadosIn(_Estrito):
    nome: str = Field(min_length=3, max_length=120)
    cpf: str
    data_nascimento: date
    email: str = Field(max_length=200)
    celular: str
    profissao: Optional[str] = Field(None, max_length=80)
    faixa_renda: Optional[str] = Field(None, max_length=40)
    estado_civil: Optional[str] = Field(None, max_length=30)
    cidade: Optional[str] = Field(None, max_length=80)
    uf: Optional[str] = Field(None, pattern="^[A-Z]{2}$")

    @field_validator("nome")
    @classmethod
    def _nome(cls, v):
        v = " ".join(v.split())
        if len(v.split()) < 2:
            raise ValueError("informe nome e sobrenome")
        return v

    @field_validator("cpf")
    @classmethod
    def _cpf(cls, v):
        v = re.sub(r"\D", "", v)
        if not cpf_valido(v):
            raise ValueError("CPF inválido")
        return v

    @field_validator("celular")
    @classmethod
    def _cel(cls, v):
        v = re.sub(r"\D", "", v)
        if not re.fullmatch(r"[0-9]{10,11}", v):
            raise ValueError("celular deve ter DDD e 10 ou 11 dígitos")
        return v

    @field_validator("email")
    @classmethod
    def _email(cls, v):
        v = v.strip().lower()
        if not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", v):
            raise ValueError("e-mail inválido")
        return v


class SolicitacaoIn(_Estrito):
    cotacao_id: str
    produto_versao_id: str
    dados: DadosIn
    consentimentos: List[str]
    recado: Optional[str] = Field(None, max_length=1000)  # observação livre para o especialista
    # Campos que a seguradora exige na proposta (rodada 3). Ausente só é aceito enquanto
    # PROPOSTA_OBRIGATORIA não for "1" (compatibilidade com quem ainda não envia).
    proposta: Optional[PropostaIn] = None
    # Respostas da DPS da seguradora escolhida: {id da pergunta: resposta}. Ver api/dps.py.
    dps: Optional[Dict[str, Any]] = None


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _uuid_ou_404(v: str, o_que: str = "não encontrada"):
    try:
        uuid.UUID(v)
    except ValueError:
        raise HTTPException(404, o_que)


def _primeiro_nome(nome: str) -> str:
    return nome.split()[0].capitalize()


def _mensagem(status: str, nome: str, seguradora: str, pendencia=None, numero=None,
              prazo: Optional[date] = None) -> str:
    return MENSAGENS[status].format(
        nome=_primeiro_nome(nome), seguradora=seguradora, pendencia=pendencia or "",
        numero=f" (nº {numero})" if numero else "",
        prazo=(f" Faça isso até {prazo:%d/%m/%Y}: depois dessa data a seguradora pode cancelar "
               "a proposta.") if prazo else "",
    )


def _mensagem_recebida(nome: str, seguradora: str, produto: str, url_cg: Optional[str]) -> str:
    """Primeira mensagem pós-contratação: confirmação, régua, condições gerais, contato.

    As condições gerais são obrigação regulatória. Sem link cadastrado, a mensagem promete o
    envio no mesmo dia e a ficha do backoffice mostra o alerta para a equipe cumprir.
    CANAL_CONTATO_TEXTO vem do ambiente: depende do cliente. Nenhuma etapa promete prazo.
    """
    etapas = " → ".join(rotulo for _, rotulo, _ in REGUA)
    partes = [
        f"Oi, {_primeiro_nome(nome)}! Recebemos sua solicitação de contratação do seguro "
        f"{produto} ({seguradora}).",
        "O que acontece agora: sua proposta será enviada à seguradora e você receberá as "
        "atualizações a cada mudança de status.",
        f"Etapas: {etapas}.",
    ]
    # Sem prazo, de propósito: depende da seguradora e da saúde do segurado (exames, sobretaxa,
    # recusa de cobertura). Qualquer prazo vira promessa quebrada na primeira proposta complexa.
    partes.append(
        f"Condições gerais do seguro: {url_cg}" if url_cg else
        "As condições gerais do seguro serão enviadas a você hoje, por esta mesma conversa.")
    contato = os.environ.get("CANAL_CONTATO_TEXTO", "").strip()
    if contato:
        partes.append(f"Dúvidas? {contato}")
    return "\n\n".join(partes)


def _notificar(conn, sid, status, nome, seguradora, pendencia=None, numero=None,
               produto=None, url_cg=None, prazo: Optional[date] = None):
    if status == "RECEBIDA" and produto:
        msg = _mensagem_recebida(nome, seguradora, produto, url_cg)
    else:
        msg = _mensagem(status, nome, seguradora, pendencia, numero, prazo)
    for canal in ("WHATSAPP", "EMAIL"):
        conn.execute(
            "INSERT INTO notificacao (solicitacao_id, canal, status_destino, mensagem) "
            "VALUES (%s,%s,%s,%s)", (sid, canal, status, msg))


_SQL_FICHA = """
    SELECT s.*, ci.premio_mensal, ci.aderencia_total, ci.motivo_ranking,
           ci.premio_ano_10, ci.premio_ano_20, ci.premio_ano_30,
           p.nome_comercial AS produto, sg.nome AS seguradora, sg.id AS seguradora_id,
           pv.id AS produto_versao_id, cg.url_documento AS url_cg, cg.versao AS versao_cg,
           ct.recado AS recado_personalizacao
    FROM solicitacao s
    JOIN cotacao_item ci ON ci.id = s.cotacao_item_id
    JOIN cotacao ct ON ct.id = ci.cotacao_id
    LEFT JOIN condicoes_gerais_versao cg ON cg.id = ci.condicoes_gerais_versao_id
    JOIN produto_versao pv ON pv.id = ci.produto_versao_id
    JOIN produto p ON p.id = pv.produto_id
    JOIN seguradora sg ON sg.id = p.seguradora_id
    WHERE s.id = %s
"""


def _ficha(conn, sid):
    cur = conn.cursor(row_factory=dict_row)
    cur.execute(_SQL_FICHA, (sid,))
    return cur.fetchone()


# Recebida e Aprovada são fatos já cumpridos: o passo seguinte é que está em andamento.
_EVENTOS = {"RECEBIDA", "APROVADA"}


def _regua(status: str, historico: list) -> list:
    pos = _POSICAO.get(status)
    if pos is not None and status in _EVENTOS:
        pos += 1
    quando = {}
    for h in historico:
        quando.setdefault(h["status"], h["em"])
    out = []
    for i, (cod, rotulo, desc) in enumerate(REGUA):
        if status == "EMITIDA" or (pos is not None and i < pos):
            estado = "CONCLUIDO"
        elif pos is not None and i == pos:
            estado = "EM_ANDAMENTO"
        else:
            estado = "AGUARDANDO"
        # em RECUSADA/CANCELADA nada fica "em andamento": pos None -> tudo aguardando
        # exceto o que já foi cumprido no histórico
        if pos is None and cod in quando:
            estado = "CONCLUIDO"
        out.append({"codigo": cod, "rotulo": rotulo, "descricao": desc, "estado": estado,
                    "em": quando.get(cod)})
    return out


def _plano(f) -> dict:
    d = f["motivo_ranking"] or {}
    return {
        "produto_versao_id": str(f["produto_versao_id"]),
        "seguradora": f["seguradora"], "produto": f["produto"],
        "premio_mensal": float(f["premio_mensal"]),
        "aderencia_total": float(f["aderencia_total"]) if f["aderencia_total"] is not None else None,
        "itens": [i for i in d.get("itens", [])],
        "projecao_premio": None if f["premio_ano_10"] is None else {
            "ano_10": float(f["premio_ano_10"]), "ano_20": float(f["premio_ano_20"]),
            "ano_30": float(f["premio_ano_30"])},
    }


def _historico(conn, sid):
    cur = conn.cursor(row_factory=dict_row)
    cur.execute("SELECT status, nota, por, em FROM solicitacao_historico "
                "WHERE solicitacao_id=%s ORDER BY em, id", (sid,))
    return cur.fetchall()


def _notificacoes(conn, sid, limite=6):
    cur = conn.cursor(row_factory=dict_row)
    cur.execute("SELECT canal, status_destino AS status, mensagem, criada_em FROM notificacao "
                "WHERE solicitacao_id=%s ORDER BY id DESC LIMIT %s", (sid, limite))
    return cur.fetchall()


# ---------------------------------------------------------------------------
# Cliente
# ---------------------------------------------------------------------------


_COLUNAS_PROPOSTA = (
    "nome_social", "sexo", "renda_mensal", "peso_kg", "altura_cm", "cep", "logradouro",
    "numero_endereco", "complemento", "bairro", "pep", "fumante_24_meses", "aposentado",
    "nacionalidade", "pais_nascimento", "pais_residencia", "pais_residencia_fiscal",
    "us_person", "origem_recurso", "beneficiarios_legais",
)


def _gravar_proposta(conn, sid, p: PropostaIn) -> None:
    valores = p.model_dump(include=set(_COLUNAS_PROPOSTA))
    conn.execute(
        "UPDATE solicitacao SET " + ", ".join(f"{c}=%s" for c in _COLUNAS_PROPOSTA) + " WHERE id=%s",
        [valores[c] for c in _COLUNAS_PROPOSTA] + [sid])
    for b in p.beneficiarios:
        conn.execute(
            "INSERT INTO beneficiario (solicitacao_id, nome, data_nascimento, parentesco, percentual) "
            "VALUES (%s,%s,%s,%s,%s)", (sid, b.nome, b.data_nascimento, b.parentesco, b.percentual))


def _questionario(seguradora: str, demonstracao: bool):
    """Questionário da seguradora. Produto fictício (demonstração) de seguradora sem DPS própria pode
    usar o de uma real, só para mostrar a jornada: DPS_PERFIL_DEMONSTRACAO=AZOS|ICATU."""
    perfil = perfil_de(seguradora)
    if perfil == COMUM and demonstracao:
        demo = os.environ.get("DPS_PERFIL_DEMONSTRACAO", "").strip().upper()
        if demo in (AZOS, ICATU):
            perfil = demo
    return questionario_de(perfil)


@router.get("/v1/dps/questionario")
def questionario_dps(seguradora: str = Query(..., min_length=1, max_length=120),
                     demonstracao: bool = False):
    """Perguntas da DPS da seguradora escolhida, com a redação dela (api/dps.py)."""
    q = _questionario(seguradora, demonstracao)
    if q is None:
        return {"existe": False}
    return {
        "existe": True, "perfil": q["perfil"], "versao": q["versao"], "confirmado": q["confirmado"],
        "perguntas": [{k: p[k] for k in ("id", "texto", "tipo", "opcoes", "exclusiva", "depende", "unidade")}
                      for p in q["perguntas"]],
    }


@router.get("/v1/proposta/campos")
def campos_da_proposta(seguradora: str = Query(..., min_length=1, max_length=120)):
    """O que o formulário deve pedir para a seguradora escolhida (campos, listas e regras)."""
    return campos_da_seguradora(seguradora)


def _preparar_dps(req: SolicitacaoIn, seguradora: str, real: bool):
    """(snapshot, hash, confirmada) da DPS a gravar, ou None. Levanta 422/409 se não puder seguir."""
    q = _questionario(seguradora, not real)
    obrigatoria = os.environ.get("DPS_OBRIGATORIA") == "1"
    if q is None or (req.dps is None and not obrigatoria):
        return None
    if req.dps is None:
        raise HTTPException(422, "responda as perguntas de saúde da seguradora")
    if real and not questionario_valido_para_producao(q) and os.environ.get("DPS_ACEITAR_NAO_CONFIRMADA") != "1":
        raise HTTPException(409, "o questionário de saúde desta seguradora ainda está em conferência "
                                 "e não pode ser usado em contratação real")
    erros, normalizadas = validar_respostas(q, req.dps)
    if erros:
        raise HTTPException(422, " ".join(erros))
    snap = instantaneo(q, normalizadas)
    return snap, hash_dps(snap), q["confirmado"]


@router.post("/v1/solicitacoes", status_code=201)
def criar_solicitacao(req: SolicitacaoIn, bg: BackgroundTasks, request: Request):
    _uuid_ou_404(req.cotacao_id, "cotação não encontrada")
    _uuid_ou_404(req.produto_versao_id, "opção não encontrada")
    textos = {**TEXTO_CONSENTIMENTOS, **(TEXTO_CONSENTIMENTO_DPS if req.dps is not None else {})}
    faltando = set(textos) - set(req.consentimentos)
    if faltando or set(req.consentimentos) - set(textos):
        raise HTTPException(422, f"consentimentos obrigatórios não aceitos: {sorted(faltando)}")

    with conexao() as conn:
        cur = conn.cursor(row_factory=dict_row)
        cur.execute(
            "SELECT ci.id AS item_id, ci.produto_versao_id, c.cliente_id, c.idade, "
            "c.sexo AS sexo_cotacao, c.fumante AS fumante_cotacao, pv.status, "
            "tv.fonte_tarifa, sg.nome AS seguradora, p.nome_comercial AS produto, "
            "cg.url_documento AS url_cg FROM cotacao_item ci "
            "JOIN cotacao c ON c.id = ci.cotacao_id "
            "JOIN produto_versao pv ON pv.id = ci.produto_versao_id "
            "JOIN tarifa_versao tv ON tv.id = ci.tarifa_versao_id "
            "JOIN produto p ON p.id = pv.produto_id JOIN seguradora sg ON sg.id = p.seguradora_id "
            "LEFT JOIN condicoes_gerais_versao cg ON cg.id = ci.condicoes_gerais_versao_id "
            "WHERE ci.cotacao_id = %s AND ci.produto_versao_id = %s",
            (req.cotacao_id, req.produto_versao_id))
        item = cur.fetchone()
        if item is None:
            raise HTTPException(404, "opção não encontrada nesta cotação")

        real = item["status"] == "PUBLICADO" and item["fonte_tarifa"] == "SEGURADORA"
        if not real and not permitir_ficticios():
            raise HTTPException(409, "este produto não está disponível para contratação")

        idade = _idade(req.dados.data_nascimento)
        if idade != item["idade"]:
            raise HTTPException(
                422, f"a data de nascimento indica {idade} anos, mas a cotação foi feita para "
                     f"{item['idade']}. Refaça a comparação com a idade correta, pois o preço muda.")

        d = req.dados
        p = req.proposta
        if p is None and os.environ.get("PROPOSTA_OBRIGATORIA") == "1":
            raise HTTPException(422, "informe os dados da proposta (endereço, beneficiários e demais)")
        if p is not None:
            campos = {**d.model_dump(), **p.model_dump(exclude={"beneficiarios", "beneficiarios_legais"})}
            erros = validar_proposta(
                perfil_de(item["seguradora"]), campos,
                [b.model_dump() for b in p.beneficiarios], p.beneficiarios_legais,
                item["sexo_cotacao"], item["fumante_cotacao"])
            if erros:
                raise HTTPException(422, " ".join(erros))
        dps = _preparar_dps(req, item["seguradora"], real)
        conn.execute("UPDATE cliente SET nome=%s, email=%s WHERE id=%s",
                     (d.nome, d.email, item["cliente_id"]))
        sid = conn.execute(
            "INSERT INTO solicitacao (cliente_id, cotacao_item_id, nome, cpf, data_nascimento, email, "
            "celular, profissao, faixa_renda, estado_civil, cidade, uf, demonstracao, recado) "
            "VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s) RETURNING id",
            (item["cliente_id"], item["item_id"], d.nome, d.cpf, d.data_nascimento, d.email, d.celular,
             d.profissao, d.faixa_renda, d.estado_civil, d.cidade, d.uf, not real,
             (req.recado or "").strip() or None)).fetchone()[0]
        if p is not None:
            _gravar_proposta(conn, sid, p)
        if dps is not None:
            snap, h, confirmada = dps
            conn.execute(
                "INSERT INTO dps_resposta (solicitacao_id, perfil, questionario_versao, redacao_confirmada, "
                "conteudo, hash_sha256, ip, user_agent) VALUES (%s,%s,%s,%s,%s::jsonb,%s,%s,%s)",
                (sid, snap["perfil"], snap["versao"], confirmada, json.dumps(snap, ensure_ascii=False), h,
                 request.client.host if request.client else None,
                 (request.headers.get("user-agent") or "")[:300] or None))
        conn.execute("INSERT INTO solicitacao_historico (solicitacao_id, status, nota, por) "
                     "VALUES (%s,'RECEBIDA','Solicitação enviada pelo cliente','cliente')", (sid,))
        for tipo in textos:
            conn.execute("INSERT INTO consentimento (solicitacao_id, tipo, texto_versao, texto) "
                         "VALUES (%s,%s,%s,%s)", (sid, tipo, VERSAO_TEXTOS, textos[tipo]))
        _notificar(conn, sid, "RECEBIDA", d.nome, item["seguradora"],
                   produto=item["produto"], url_cg=item["url_cg"])
    _agendar_envios(bg)
    return {"id": str(sid), "status": "RECEBIDA"}


@router.get("/v1/solicitacoes/{sid}")
def acompanhar(sid: str):
    _uuid_ou_404(sid)
    with conexao() as conn:
        f = _ficha(conn, sid)
        if f is None:
            raise HTTPException(404, "solicitação não encontrada")
        hist = _historico(conn, sid)
        notifs = _notificacoes(conn, sid, 2)
    return {
        "id": sid, "status": f["status"], "status_desde": f["status_desde"],
        "pendencia": f["pendencia"], "numero_apolice": f["numero_apolice"],
        "prazo_acao": f["prazo_acao"],
        "demonstracao": f["demonstracao"], "primeiro_nome": _primeiro_nome(f["nome"]),
        "criada_em": f["criada_em"], "regua": _regua(f["status"], hist),
        "plano": _plano(f),
        "notificacoes": [{"canal": n["canal"], "mensagem": n["mensagem"], "criada_em": n["criada_em"]}
                         for n in notifs],
    }


# ---------------------------------------------------------------------------
# Backoffice
# ---------------------------------------------------------------------------


def exigir_backoffice(x_backoffice_key: Optional[str] = Header(None)):
    chave = os.environ.get("BACKOFFICE_KEY")
    if not chave:
        raise HTTPException(503, "backoffice desligado: BACKOFFICE_KEY não configurada")
    if not x_backoffice_key or not hmac.compare_digest(x_backoffice_key, chave):
        raise HTTPException(401, "chave do backoffice inválida")


@router.get("/v1/backoffice/resumo", dependencies=[Depends(exigir_backoffice)])
def resumo():
    with conexao() as conn:
        r = conn.execute(
            "SELECT count(*) FILTER (WHERE criada_em >= date_trunc('day', now())), "
            "count(*) FILTER (WHERE status IN ('ENVIADA','EM_ANALISE')), "
            "count(*) FILTER (WHERE status = 'PENDENCIA'), "
            "count(*) FILTER (WHERE status = 'EMITIDA' AND status_desde >= now() - interval '30 days'), "
            "count(*) FILTER (WHERE status IN ('RECEBIDA','EM_PREPARACAO')) "
            "FROM solicitacao").fetchone()
    return {"hoje": r[0], "em_analise": r[1], "pendencias": r[2], "emitidas_30d": r[3],
            "para_nos": r[4]}


@router.get("/v1/backoffice/solicitacoes", dependencies=[Depends(exigir_backoffice)])
def fila(status: Optional[str] = None, seguradora: Optional[str] = None,
         q: Optional[str] = None, dias: int = Query(30, ge=1, le=3650)):
    if status is not None and status not in TRANSICOES:
        raise HTTPException(422, "status inválido")
    filtros, params = ["s.criada_em >= now() - make_interval(days => %s)"], [dias]
    if status:
        filtros.append("s.status = %s"); params.append(status)
    if seguradora:
        filtros.append("sg.nome = %s"); params.append(seguradora)
    if q:
        filtros.append("s.nome ILIKE %s"); params.append(f"%{q}%")
    with conexao() as conn:
        cur = conn.cursor(row_factory=dict_row)
        cur.execute(
            "SELECT s.id, s.nome, s.status, s.pendencia, s.status_desde, s.demonstracao, "
            "s.prazo_acao, ci.premio_mensal, p.nome_comercial AS produto, sg.nome AS seguradora "
            "FROM solicitacao s JOIN cotacao_item ci ON ci.id = s.cotacao_item_id "
            "JOIN produto_versao pv ON pv.id = ci.produto_versao_id "
            "JOIN produto p ON p.id = pv.produto_id JOIN seguradora sg ON sg.id = p.seguradora_id "
            "WHERE " + " AND ".join(filtros), params)
        linhas = cur.fetchall()
        seguradoras = [r[0] for r in conn.execute(
            "SELECT DISTINCT sg.nome FROM solicitacao s JOIN cotacao_item ci ON ci.id = s.cotacao_item_id "
            "JOIN produto_versao pv ON pv.id = ci.produto_versao_id JOIN produto p ON p.id = pv.produto_id "
            "JOIN seguradora sg ON sg.id = p.seguradora_id ORDER BY sg.nome")]
    ordem = {"NOS": 0, "CLIENTE": 1, "SEGURADORA": 2, "FIM": 3}
    linhas.sort(key=lambda r: (ordem[COM_QUEM[r["status"]]], r["status_desde"]))
    return {
        "seguradoras": seguradoras,
        "solicitacoes": [{
            "id": str(r["id"]), "nome": r["nome"], "seguradora": r["seguradora"],
            "produto": r["produto"], "premio_mensal": float(r["premio_mensal"]),
            "status": r["status"], "pendencia": r["pendencia"], "status_desde": r["status_desde"],
            "prazo_acao": r["prazo_acao"],
            "com_quem": COM_QUEM[r["status"]], "demonstracao": r["demonstracao"],
        } for r in linhas],
    }


def _proposta_da_ficha(f, beneficiarios) -> dict:
    """Campos da proposta para a equipe preencher o portal da seguradora. None = não informado."""
    def v(x):
        return float(x) if isinstance(x, Decimal) else x
    return {
        "perfil": perfil_de(f["seguradora"]),
        "campos": {c: v(f[c]) for c in _COLUNAS_PROPOSTA if c != "beneficiarios_legais"},
        "beneficiarios_legais": f["beneficiarios_legais"],
        "beneficiarios": [{"nome": b["nome"], "data_nascimento": b["data_nascimento"],
                           "parentesco": b["parentesco"], "percentual": float(b["percentual"])}
                          for b in beneficiarios],
    }


@router.get("/v1/backoffice/solicitacoes/{sid}", dependencies=[Depends(exigir_backoffice)])
def ficha(sid: str):
    _uuid_ou_404(sid)
    with conexao() as conn:
        f = _ficha(conn, sid)
        if f is None:
            raise HTTPException(404, "solicitação não encontrada")
        hist = _historico(conn, sid)
        notifs = _notificacoes(conn, sid)
        bens = conn.cursor(row_factory=dict_row)
        bens.execute("SELECT nome, data_nascimento, parentesco, percentual FROM beneficiario "
                     "WHERE solicitacao_id=%s ORDER BY id", (sid,))
        beneficiarios = bens.fetchall()
        d = conn.cursor(row_factory=dict_row)
        d.execute("SELECT perfil, questionario_versao, redacao_confirmada, conteudo, hash_sha256, respondido_em "
                  "FROM dps_resposta WHERE solicitacao_id=%s", (sid,))
        dps = d.fetchone()
    return {
        "id": sid, "status": f["status"], "status_desde": f["status_desde"],
        "com_quem": COM_QUEM[f["status"]], "pendencia": f["pendencia"],
        "prazo_acao": f["prazo_acao"],
        "proposta": _proposta_da_ficha(f, beneficiarios),
        # DPS como o cliente respondeu (imutável). A equipe transcreve daqui, nunca de memória.
        "dps": None if dps is None else {
            "perfil": dps["perfil"], "versao": dps["questionario_versao"],
            "redacao_confirmada": dps["redacao_confirmada"], "respondido_em": dps["respondido_em"],
            "hash": dps["hash_sha256"], "itens": dps["conteudo"]["itens"],
        },
        "numero_apolice": f["numero_apolice"], "demonstracao": f["demonstracao"],
        # sem link, a equipe precisa enviar as condições gerais manualmente no mesmo dia
        "condicoes_gerais": {"url": f["url_cg"], "versao": f["versao_cg"]},
        "recados": {"checkout": f["recado"], "personalizacao": f["recado_personalizacao"]},
        "proximos_status": sorted(TRANSICOES[f["status"]]),
        "cliente": {"nome": f["nome"], "celular": f["celular"], "email": f["email"],
                    "cidade": f["cidade"], "uf": f["uf"], "profissao": f["profissao"],
                    "faixa_renda": f["faixa_renda"], "estado_civil": f["estado_civil"],
                    "data_nascimento": f["data_nascimento"], "cpf_final": f["cpf"][-2:]},
        "plano": _plano(f), "regua": _regua(f["status"], hist),
        "historico": [{"status": h["status"], "nota": h["nota"], "por": h["por"], "em": h["em"]}
                      for h in hist],
        "notificacoes": [{"canal": n["canal"], "mensagem": n["mensagem"], "criada_em": n["criada_em"]}
                         for n in notifs],
    }


class MudarStatusIn(_Estrito):
    status: str
    nota: Optional[str] = Field(None, max_length=500)
    pendencia: Optional[str] = Field(None, max_length=300)
    numero_apolice: Optional[str] = Field(None, max_length=60)
    # Data-limite que a seguradora deu ao cliente; só para os status AGUARDANDO_*.
    prazo_acao: Optional[date] = None
    por: str = Field("backoffice", max_length=60)


@router.post("/v1/backoffice/solicitacoes/{sid}/status", dependencies=[Depends(exigir_backoffice)])
def mudar_status(sid: str, req: MudarStatusIn, bg: BackgroundTasks):
    _uuid_ou_404(sid)
    if req.status not in TRANSICOES:
        raise HTTPException(422, "status inválido")
    with conexao() as conn:
        f = _ficha(conn, sid)
        if f is None:
            raise HTTPException(404, "solicitação não encontrada")
        if req.status not in TRANSICOES[f["status"]]:
            raise HTTPException(
                409, f"não é possível ir de {f['status']} para {req.status}. "
                     f"Permitidos: {sorted(TRANSICOES[f['status']]) or 'nenhum (status final)'}")
        if req.status == "PENDENCIA" and not (req.pendencia or "").strip():
            raise HTTPException(422, "descreva a pendência")
        pendencia = req.pendencia.strip() if req.status == "PENDENCIA" else None
        numero = req.numero_apolice if req.status == "EMITIDA" else f["numero_apolice"]
        if req.prazo_acao is not None:
            if req.status not in AGUARDANDO_CLIENTE:
                raise HTTPException(422, "prazo_acao só vale para aguardando assinatura ou pagamento")
            if req.prazo_acao < date.today():
                raise HTTPException(422, "o prazo já passou")
        prazo = req.prazo_acao if req.status in AGUARDANDO_CLIENTE else None

        conn.execute("UPDATE solicitacao SET status=%s, status_desde=now(), pendencia=%s, "
                     "numero_apolice=%s, prazo_acao=%s WHERE id=%s",
                     (req.status, pendencia, numero, prazo, sid))
        conn.execute("INSERT INTO solicitacao_historico (solicitacao_id, status, nota, por) "
                     "VALUES (%s,%s,%s,%s)", (sid, req.status, req.nota or pendencia, req.por))
        _notificar(conn, sid, req.status, f["nome"], f["seguradora"], pendencia, numero, prazo=prazo)
        if req.status == "EMITIDA":
            _registrar_apolice(conn, f, numero)
    _agendar_envios(bg)
    return {"id": sid, "status": req.status}


def _agendar_envios(bg: BackgroundTasks):
    """Despacha e-mail e WhatsApp depois da resposta, só com NOTIFICACOES_ATIVAS=1."""
    if os.environ.get("NOTIFICACOES_ATIVAS") != "1":
        return
    if email_configurado():
        bg.add_task(despachar_emails)
    if crm_configurado():
        bg.add_task(despachar_whatsapp)


@router.get("/v1/backoffice/notificacoes/pendentes", dependencies=[Depends(exigir_backoffice)])
def notificacoes_pendentes(canal: str = Query("WHATSAPP", pattern="^(WHATSAPP|EMAIL)$"),
                           limite: int = Query(50, ge=1, le=200)):
    """Mensagens ainda não enviadas, na ordem de criação. Entrada para o CRM do corretor."""
    with conexao() as conn:
        cur = conn.cursor(row_factory=dict_row)
        cur.execute(
            "SELECT n.id, n.solicitacao_id, n.status_destino AS status, n.mensagem, n.criada_em, "
            "s.nome, s.celular, s.email FROM notificacao n JOIN solicitacao s ON s.id = n.solicitacao_id "
            "WHERE n.canal = %s AND n.enviada_em IS NULL ORDER BY n.id LIMIT %s", (canal, limite))
        linhas = cur.fetchall()
    return {"canal": canal, "pendentes": [
        {"id": r["id"], "solicitacao_id": str(r["solicitacao_id"]), "status": r["status"],
         "nome": r["nome"], "destino": f"55{r['celular']}" if canal == "WHATSAPP" else r["email"],
         "mensagem": r["mensagem"], "criada_em": r["criada_em"]} for r in linhas]}


@router.post("/v1/backoffice/notificacoes/{nid}/enviada", dependencies=[Depends(exigir_backoffice)])
def notificacao_enviada(nid: int):
    with conexao() as conn:
        r = conn.execute("UPDATE notificacao SET enviada_em = COALESCE(enviada_em, now()) "
                         "WHERE id = %s RETURNING id", (nid,)).fetchone()
    if r is None:
        raise HTTPException(404, "notificação não encontrada")
    return {"id": nid, "enviada": True}


@router.post("/v1/backoffice/notificacoes/enviar-email", dependencies=[Depends(exigir_backoffice)])
def enviar_emails_pendentes():
    if not email_configurado():
        raise HTTPException(409, "envio de e-mail não configurado (SMTP_HOST e EMAIL_REMETENTE)")
    enviados, falhas = despachar_emails()
    return {"enviados": enviados, "falhas": falhas}


@router.post("/v1/backoffice/notificacoes/enviar-whatsapp", dependencies=[Depends(exigir_backoffice)])
def enviar_whatsapps_pendentes():
    if not crm_configurado():
        raise HTTPException(409, "CRM não configurado (DESKCOMM_URL e DESKCOMM_TOKEN)")
    enviados, falhas = despachar_whatsapp()
    return {"enviados": enviados, "falhas": falhas}


def _registrar_apolice(conn, f, numero):
    """Apólice emitida entra no modelo 1 cliente -> N apólices -> N seguradoras."""
    aid = conn.execute(
        "INSERT INTO apolice (cliente_id, seguradora_id, produto_versao_id, numero_apolice, origem, "
        "inicio_vigencia, premio_mensal) VALUES (%s,%s,%s,%s,'EMITIDA',current_date,%s) RETURNING id",
        (f["cliente_id"], f["seguradora_id"], f["produto_versao_id"], numero, f["premio_mensal"])
    ).fetchone()[0]
    for item in (f["motivo_ranking"] or {}).get("itens", []):
        if not item.get("cobertura") or not item.get("capital_contratado"):
            continue
        diaria = item["necessidade"] == "NEC_RENDA"
        conn.execute(
            "INSERT INTO apolice_cobertura (apolice_id, codigo_cobertura, capital, valor_diaria, confianca) "
            "VALUES (%s,%s,%s,%s,'VERIFICADO') ON CONFLICT DO NOTHING",
            (aid, item["cobertura"], None if diaria else item["capital_contratado"],
             item["capital_contratado"] if diaria else None))
