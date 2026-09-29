"""Contratação: solicitação do cliente, régua de status e backoffice mínimo.

    POST /v1/solicitacoes                       cliente solicita a contratação
    GET  /v1/solicitacoes/{id}                  cliente acompanha (o UUID é a chave de acesso)
    GET  /v1/backoffice/resumo                  contadores do painel
    GET  /v1/backoffice/solicitacoes            fila de trabalho
    GET  /v1/backoffice/solicitacoes/{id}       ficha da solicitação
    POST /v1/backoffice/solicitacoes/{id}/status  muda o status (dispara notificações)

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
from typing import List, Optional

from fastapi import APIRouter, Depends, Header, HTTPException, Query
from psycopg.rows import dict_row
from pydantic import BaseModel, ConfigDict, Field, field_validator

from .infra import conexao, permitir_ficticios

router = APIRouter()

# ---------------------------------------------------------------------------
# Régua de status
# ---------------------------------------------------------------------------

REGUA = [
    ("RECEBIDA", "Solicitação recebida", "Recebemos o seu pedido."),
    ("EM_PREPARACAO", "Proposta em preparação", "Estamos montando a sua proposta."),
    ("ENVIADA", "Enviada à seguradora", "Sua proposta foi enviada à seguradora."),
    ("EM_ANALISE", "Em análise", "A seguradora está analisando as informações."),
    ("APROVADA", "Aprovada", "Você receberá a confirmação da aprovação."),
    ("EMITIDA", "Apólice emitida", "Sua apólice foi emitida."),
]
_POSICAO = {c: i for i, (c, _, _) in enumerate(REGUA)}
_POSICAO["PENDENCIA"] = _POSICAO["EM_ANALISE"]

TRANSICOES = {
    "RECEBIDA": {"EM_PREPARACAO", "CANCELADA"},
    "EM_PREPARACAO": {"ENVIADA", "PENDENCIA", "CANCELADA"},
    "ENVIADA": {"EM_ANALISE", "PENDENCIA", "CANCELADA"},
    "EM_ANALISE": {"APROVADA", "PENDENCIA", "RECUSADA", "CANCELADA"},
    "PENDENCIA": {"EM_PREPARACAO", "ENVIADA", "EM_ANALISE", "CANCELADA"},
    "APROVADA": {"EMITIDA", "CANCELADA"},
    "EMITIDA": set(), "RECUSADA": set(), "CANCELADA": set(),
}

# De quem é a vez de agir — é o que ordena a fila do backoffice.
COM_QUEM = {
    "RECEBIDA": "NOS", "EM_PREPARACAO": "NOS", "PENDENCIA": "CLIENTE",
    "ENVIADA": "SEGURADORA", "EM_ANALISE": "SEGURADORA", "APROVADA": "SEGURADORA",
    "EMITIDA": "FIM", "RECUSADA": "FIM", "CANCELADA": "FIM",
}

MENSAGENS = {
    "RECEBIDA": "Oi, {nome}! Recebemos sua solicitação de contratação. "
                "Em breve enviaremos novas atualizações por aqui.",
    "EM_PREPARACAO": "{nome}, estamos montando a sua proposta.",
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


def _mensagem(status: str, nome: str, seguradora: str, pendencia=None, numero=None) -> str:
    return MENSAGENS[status].format(
        nome=_primeiro_nome(nome), seguradora=seguradora, pendencia=pendencia or "",
        numero=f" (nº {numero})" if numero else "",
    )


def _notificar(conn, sid, status, nome, seguradora, pendencia=None, numero=None):
    msg = _mensagem(status, nome, seguradora, pendencia, numero)
    for canal in ("WHATSAPP", "EMAIL"):
        conn.execute(
            "INSERT INTO notificacao (solicitacao_id, canal, status_destino, mensagem) "
            "VALUES (%s,%s,%s,%s)", (sid, canal, status, msg))


_SQL_FICHA = """
    SELECT s.*, ci.premio_mensal, ci.aderencia_total, ci.motivo_ranking,
           ci.premio_ano_10, ci.premio_ano_20, ci.premio_ano_30,
           p.nome_comercial AS produto, sg.nome AS seguradora, sg.id AS seguradora_id,
           pv.id AS produto_versao_id
    FROM solicitacao s
    JOIN cotacao_item ci ON ci.id = s.cotacao_item_id
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


@router.post("/v1/solicitacoes", status_code=201)
def criar_solicitacao(req: SolicitacaoIn):
    _uuid_ou_404(req.cotacao_id, "cotação não encontrada")
    _uuid_ou_404(req.produto_versao_id, "opção não encontrada")
    faltando = set(TEXTO_CONSENTIMENTOS) - set(req.consentimentos)
    if faltando or set(req.consentimentos) - set(TEXTO_CONSENTIMENTOS):
        raise HTTPException(422, f"consentimentos obrigatórios não aceitos: {sorted(faltando)}")

    with conexao() as conn:
        cur = conn.cursor(row_factory=dict_row)
        cur.execute(
            "SELECT ci.id AS item_id, ci.produto_versao_id, c.cliente_id, c.idade, pv.status, "
            "tv.fonte_tarifa, sg.nome AS seguradora FROM cotacao_item ci "
            "JOIN cotacao c ON c.id = ci.cotacao_id "
            "JOIN produto_versao pv ON pv.id = ci.produto_versao_id "
            "JOIN tarifa_versao tv ON tv.id = ci.tarifa_versao_id "
            "JOIN produto p ON p.id = pv.produto_id JOIN seguradora sg ON sg.id = p.seguradora_id "
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
        conn.execute("UPDATE cliente SET nome=%s, email=%s WHERE id=%s",
                     (d.nome, d.email, item["cliente_id"]))
        sid = conn.execute(
            "INSERT INTO solicitacao (cliente_id, cotacao_item_id, nome, cpf, data_nascimento, email, "
            "celular, profissao, faixa_renda, estado_civil, cidade, uf, demonstracao) "
            "VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s) RETURNING id",
            (item["cliente_id"], item["item_id"], d.nome, d.cpf, d.data_nascimento, d.email, d.celular,
             d.profissao, d.faixa_renda, d.estado_civil, d.cidade, d.uf, not real)).fetchone()[0]
        conn.execute("INSERT INTO solicitacao_historico (solicitacao_id, status, nota, por) "
                     "VALUES (%s,'RECEBIDA','Solicitação enviada pelo cliente','cliente')", (sid,))
        for tipo in TEXTO_CONSENTIMENTOS:
            conn.execute("INSERT INTO consentimento (solicitacao_id, tipo, texto_versao, texto) "
                         "VALUES (%s,%s,%s,%s)", (sid, tipo, VERSAO_TEXTOS, TEXTO_CONSENTIMENTOS[tipo]))
        _notificar(conn, sid, "RECEBIDA", d.nome, item["seguradora"])
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
            "ci.premio_mensal, p.nome_comercial AS produto, sg.nome AS seguradora "
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
            "com_quem": COM_QUEM[r["status"]], "demonstracao": r["demonstracao"],
        } for r in linhas],
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
    return {
        "id": sid, "status": f["status"], "status_desde": f["status_desde"],
        "com_quem": COM_QUEM[f["status"]], "pendencia": f["pendencia"],
        "numero_apolice": f["numero_apolice"], "demonstracao": f["demonstracao"],
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
    por: str = Field("backoffice", max_length=60)


@router.post("/v1/backoffice/solicitacoes/{sid}/status", dependencies=[Depends(exigir_backoffice)])
def mudar_status(sid: str, req: MudarStatusIn):
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

        conn.execute("UPDATE solicitacao SET status=%s, status_desde=now(), pendencia=%s, "
                     "numero_apolice=%s WHERE id=%s", (req.status, pendencia, numero, sid))
        conn.execute("INSERT INTO solicitacao_historico (solicitacao_id, status, nota, por) "
                     "VALUES (%s,%s,%s,%s)", (sid, req.status, req.nota or pendencia, req.por))
        _notificar(conn, sid, req.status, f["nome"], f["seguradora"], pendencia, numero)
        if req.status == "EMITIDA":
            _registrar_apolice(conn, f, numero)
    return {"id": sid, "status": req.status}


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
