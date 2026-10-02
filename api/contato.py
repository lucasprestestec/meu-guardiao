"""Captura de contato (LGPD), pedido de conversa com o especialista e eventos do funil.

    GET  /v1/lead/textos                          textos e versão dos consentimentos
    POST /v1/leads                                contato + 2 consentimentos separados (antes do Mapa)
    POST /v1/eventos                              evento do funil (medir abandono)
    POST /v1/pedidos-especialista                 cliente pede para conversar com o especialista
    GET  /v1/backoffice/pedidos-especialista     fila de pedidos (+ contagem do funil)
    GET  /v1/backoffice/pedidos-especialista/{id} ficha: contato, motivos, recado e diagnóstico completo
    POST /v1/backoffice/pedidos-especialista/{id}/status

TEXTOS EM RASCUNHO: vêm de docs/LGPD-RASCUNHO.md e estão em revisão jurídica. A versão
("rascunho-...") fica gravada junto de cada consentimento; ao publicar o texto final, troque
a versão e os textos abaixo, e o registro antigo continua apontando para o texto que o cliente viu.
"""

from __future__ import annotations

import ipaddress
import os
import re
import uuid
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from psycopg.rows import dict_row
from pydantic import BaseModel, ConfigDict, Field, field_validator

from . import repositorio as repo
from .infra import conexao
from .solicitacoes import exigir_backoffice

router = APIRouter()

VERSAO_TEXTOS_LEAD = "rascunho-2026-10-v1"
TEXTO_ATENDIMENTO = (
    "Autorizo o uso das informações que forneci para calcular minha necessidade de proteção, "
    "apresentar opções de seguro e ser contatado sobre esta solicitação por e-mail, telefone ou "
    "WhatsApp. Li e concordo com a Política de Privacidade."
)
TEXTO_MARKETING = (
    "Quero receber conteúdos, novidades e ofertas por e-mail e WhatsApp. Posso cancelar quando quiser."
)

MOTIVOS = {
    "CAPITAL_MAIOR": "Quero capital maior do que o site permite",
    "DUVIDAS_COBERTURAS": "Tenho dúvidas sobre as coberturas",
    "REVISAR_SEGURO": "Quero revisar o seguro que já tenho",
}
ETAPAS_FUNIL = {"contato_visto", "contato_enviado", "especialista_aberto", "especialista_enviado"}
STATUS_PEDIDO = ("NOVO", "EM_CONTATO", "CONCLUIDO")


class _Estrito(BaseModel):
    model_config = ConfigDict(extra="forbid")


def _texto_apoio() -> str:
    email = os.environ.get("EMAIL_ENCARREGADO", "").strip()
    base = "Você pode retirar seu consentimento, pedir acesso ou exclusão dos seus dados a qualquer momento"
    return f"{base} pelo e-mail {email}." if email else f"{base}."


def _ip(req: Request) -> Optional[str]:
    bruto = (req.headers.get("x-forwarded-for") or "").split(",")[0].strip() or (
        req.client.host if req.client else "")
    try:
        return str(ipaddress.ip_address(bruto))
    except ValueError:
        return None


def _uuid_ou_none(v: Optional[str], o_que: str) -> Optional[str]:
    if v is None:
        return None
    try:
        return str(uuid.UUID(v))
    except ValueError:
        raise HTTPException(422, f"{o_que} inválido")


class _Pessoa(_Estrito):
    nome: str = Field(min_length=2, max_length=120)
    email: str = Field(max_length=200)
    celular: str

    @field_validator("nome")
    @classmethod
    def _nome(cls, v):
        return " ".join(v.split())

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


class LeadIn(_Pessoa):
    necessidade_id: Optional[str] = None
    consentimento_atendimento: bool
    consentimento_marketing: bool = False


class EventoIn(_Estrito):
    etapa: str
    sessao: str = Field(min_length=8, max_length=64)


class PedidoEspecialistaIn(_Pessoa):
    motivos: List[str] = []
    mensagem: Optional[str] = Field(None, max_length=2000)
    lead_id: Optional[str] = None
    necessidade_id: Optional[str] = None
    cotacao_id: Optional[str] = None


@router.get("/v1/lead/textos")
def textos():
    return {"versao": VERSAO_TEXTOS_LEAD, "atendimento": TEXTO_ATENDIMENTO, "marketing": TEXTO_MARKETING,
            "apoio": _texto_apoio(), "politica_url": "/privacidade", "motivos": MOTIVOS}


@router.post("/v1/leads", status_code=201)
def criar_lead(req: LeadIn, request: Request):
    # A primeira caixa é condição para continuar; a segunda é livre e nunca bloqueia o resultado.
    if not req.consentimento_atendimento:
        raise HTTPException(422, "o consentimento para cálculo e contato é obrigatório para continuar")
    nid = _uuid_ou_none(req.necessidade_id, "necessidade_id")
    ip, ua = _ip(request), (request.headers.get("user-agent") or "")[:300]
    with conexao() as conn:
        if nid is not None:
            achou = conn.execute("SELECT cliente_id FROM necessidade WHERE id=%s", (nid,)).fetchone()
            if achou is None:
                raise HTTPException(404, "diagnóstico não encontrado")
            conn.execute("UPDATE cliente SET nome=%s, email=%s WHERE id=%s", (req.nome, req.email, achou[0]))
        lid = conn.execute(
            "INSERT INTO lead_contato (necessidade_id, nome, email, celular) VALUES (%s,%s,%s,%s) RETURNING id",
            (nid, req.nome, req.email, req.celular)).fetchone()[0]
        for tipo, aceito, texto in (("ATENDIMENTO", True, TEXTO_ATENDIMENTO),
                                    ("MARKETING", req.consentimento_marketing, TEXTO_MARKETING)):
            conn.execute(
                "INSERT INTO consentimento_lead (lead_id, tipo, aceito, texto_versao, texto, ip, user_agent) "
                "VALUES (%s,%s,%s,%s,%s,%s,%s)", (lid, tipo, aceito, VERSAO_TEXTOS_LEAD, texto, ip, ua))
    return {"id": str(lid)}


@router.post("/v1/eventos", status_code=204)
def registrar_evento(req: EventoIn):
    if req.etapa not in ETAPAS_FUNIL:
        raise HTTPException(422, "etapa desconhecida")
    with conexao() as conn:
        conn.execute("INSERT INTO evento_funil (etapa, sessao) VALUES (%s,%s)", (req.etapa, req.sessao))


@router.post("/v1/pedidos-especialista", status_code=201)
def pedir_especialista(req: PedidoEspecialistaIn):
    invalidos = [m for m in req.motivos if m not in MOTIVOS]
    if invalidos:
        raise HTTPException(422, f"motivos desconhecidos: {invalidos}")
    if not req.motivos and not (req.mensagem or "").strip():
        raise HTTPException(422, "marque ao menos um motivo ou escreva uma mensagem")
    lead = _uuid_ou_none(req.lead_id, "lead_id")
    nid = _uuid_ou_none(req.necessidade_id, "necessidade_id")
    cot = _uuid_ou_none(req.cotacao_id, "cotacao_id")
    with conexao() as conn:
        for tabela, valor in (("lead_contato", lead), ("necessidade", nid), ("cotacao", cot)):
            if valor and conn.execute(f"SELECT 1 FROM {tabela} WHERE id=%s", (valor,)).fetchone() is None:
                raise HTTPException(404, f"{tabela} não encontrado")
        pid = conn.execute(
            "INSERT INTO pedido_especialista (lead_id, necessidade_id, cotacao_id, nome, email, celular, "
            "motivos, mensagem) VALUES (%s,%s,%s,%s,%s,%s,%s,%s) RETURNING id",
            (lead, nid, cot, req.nome, req.email, req.celular, req.motivos,
             (req.mensagem or "").strip() or None)).fetchone()[0]
    return {"id": str(pid), "status": "NOVO"}


# ---------------------------------------------------------------------------
# Backoffice
# ---------------------------------------------------------------------------


@router.get("/v1/backoffice/pedidos-especialista", dependencies=[Depends(exigir_backoffice)])
def fila_pedidos(status: Optional[str] = Query(None)):
    if status is not None and status not in STATUS_PEDIDO:
        raise HTTPException(422, "status inválido")
    with conexao() as conn:
        cur = conn.cursor(row_factory=dict_row)
        cur.execute(
            "SELECT id, nome, celular, email, motivos, mensagem, status, criado_em, "
            "(necessidade_id IS NOT NULL) AS tem_diagnostico FROM pedido_especialista "
            "WHERE (%s::text IS NULL OR status = %s) ORDER BY (status='CONCLUIDO'), criado_em DESC LIMIT 200",
            (status, status))
        linhas = cur.fetchall()
        funil = dict(conn.execute(
            "SELECT etapa, count(DISTINCT sessao) FROM evento_funil WHERE em > now() - interval '30 days' "
            "GROUP BY etapa").fetchall())
    return {
        "pedidos": [{**r, "id": str(r["id"]), "motivos": [MOTIVOS.get(m, m) for m in r["motivos"]]}
                    for r in linhas],
        "funil_30_dias": {e: int(funil.get(e, 0)) for e in sorted(ETAPAS_FUNIL)},
    }


@router.get("/v1/backoffice/pedidos-especialista/{pid}", dependencies=[Depends(exigir_backoffice)])
def ficha_pedido(pid: str):
    _uuid_ou_none(pid, "id")
    with conexao() as conn:
        cur = conn.cursor(row_factory=dict_row)
        cur.execute("SELECT * FROM pedido_especialista WHERE id=%s", (pid,))
        p = cur.fetchone()
        if p is None:
            raise HTTPException(404, "pedido não encontrado")
        diag = None
        if p["necessidade_id"]:
            cur.execute("SELECT entradas, calculado_em FROM necessidade WHERE id=%s", (p["necessidade_id"],))
            n = cur.fetchone()
            achado = repo.carregar_necessidade(conn, str(p["necessidade_id"]))
            if n and achado:
                diag = {"entradas": n["entradas"], "calculado_em": n["calculado_em"],
                        "mapa": achado[0].to_dict()}
        cotacao = None
        if p["cotacao_id"]:
            cur.execute("SELECT capitais_escolhidos, recado, idade, sexo, fumante, criada_em FROM cotacao "
                        "WHERE id=%s", (p["cotacao_id"],))
            cotacao = cur.fetchone()
        consent = []
        if p["lead_id"]:
            cur.execute("SELECT tipo, aceito, texto_versao, aceito_em, ip, revogado_em FROM consentimento_lead "
                        "WHERE lead_id=%s ORDER BY tipo", (p["lead_id"],))
            consent = cur.fetchall()
    return {
        "id": pid, "status": p["status"], "criado_em": p["criado_em"],
        "contato": {"nome": p["nome"], "email": p["email"], "celular": p["celular"]},
        "motivos": [MOTIVOS.get(m, m) for m in p["motivos"]], "mensagem": p["mensagem"],
        "diagnostico": diag, "cotacao": cotacao, "consentimentos": consent,
    }


class StatusPedidoIn(_Estrito):
    status: str


@router.post("/v1/backoffice/pedidos-especialista/{pid}/status", dependencies=[Depends(exigir_backoffice)])
def mudar_status_pedido(pid: str, req: StatusPedidoIn):
    _uuid_ou_none(pid, "id")
    if req.status not in STATUS_PEDIDO:
        raise HTTPException(422, "status inválido")
    with conexao() as conn:
        r = conn.execute("UPDATE pedido_especialista SET status=%s, atualizado_em=now() WHERE id=%s RETURNING id",
                         (req.status, pid)).fetchone()
    if r is None:
        raise HTTPException(404, "pedido não encontrado")
    return {"id": pid, "status": req.status}
