"""Conferência do cliente depois da transcrição, e acesso registrado ao CPF inteiro (rodada 3).

    POST /v1/backoffice/solicitacoes/{id}/conferencia   equipe pede que o cliente confira o que foi informado
    GET  /v1/backoffice/solicitacoes/{id}/conferencia   histórico de conferências e acessos ao CPF
    POST /v1/backoffice/solicitacoes/{id}/cpf           mostra o CPF inteiro e REGISTRA o acesso
    GET  /v1/solicitacoes/{id}/conferencia              cliente vê o que foi informado à seguradora
    POST /v1/solicitacoes/{id}/conferencia              cliente confirma ou aponta o erro

A DPS que o cliente confere é o registro imutável (api/dps.py). O hash dela fica gravado no pedido de
conferência, para provar qual declaração foi conferida.
"""

from __future__ import annotations

import os
from typing import Literal, Optional

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request
from psycopg.rows import dict_row
from pydantic import BaseModel, ConfigDict, Field

from .infra import conexao
from .solicitacoes import (
    _agendar_envios, _ficha, _primeiro_nome, _proposta_da_ficha, _uuid_ou_404, exigir_backoffice,
)

router = APIRouter()


class _Estrito(BaseModel):
    model_config = ConfigDict(extra="forbid")


class PedidoConferenciaIn(_Estrito):
    por: str = Field("backoffice", max_length=60)


class RespostaConferenciaIn(_Estrito):
    acao: Literal["confirmar", "corrigir"]
    nota: Optional[str] = Field(None, max_length=1000)


def _mensagem_conferencia(nome: str, seguradora: str, sid: str) -> str:
    site = os.environ.get("SITE_URL", "").strip().rstrip("/")
    onde = f"{site}/acompanhar/{sid}" if site else "a página de acompanhamento da sua solicitação"
    return (f"{_primeiro_nome(nome)}, a nossa equipe passou as suas informações para a {seguradora}. "
            f"Confira se está tudo certo e confirme em {onde}.")


def _dps(conn, sid):
    cur = conn.cursor(row_factory=dict_row)
    cur.execute("SELECT conteudo, hash_sha256, respondido_em FROM dps_resposta WHERE solicitacao_id=%s", (sid,))
    return cur.fetchone()


def _ultima(conn, sid):
    cur = conn.cursor(row_factory=dict_row)
    cur.execute("SELECT * FROM solicitacao_conferencia WHERE solicitacao_id=%s ORDER BY id DESC LIMIT 1", (sid,))
    return cur.fetchone()


def _estado(c) -> str:
    if c is None:
        return "NENHUMA"
    return "AGUARDANDO" if c["resposta"] is None else c["resposta"]


# --------------------------------------------------------------------------- equipe


@router.post("/v1/backoffice/solicitacoes/{sid}/conferencia", status_code=201,
             dependencies=[Depends(exigir_backoffice)])
def pedir_conferencia(sid: str, req: PedidoConferenciaIn, bg: BackgroundTasks):
    _uuid_ou_404(sid)
    with conexao() as conn:
        f = _ficha(conn, sid)
        if f is None:
            raise HTTPException(404, "solicitação não encontrada")
        dps = _dps(conn, sid)
        if dps is None:
            raise HTTPException(409, "esta solicitação não tem DPS registrada para o cliente conferir")
        if _estado(_ultima(conn, sid)) == "AGUARDANDO":
            raise HTTPException(409, "já há uma conferência aguardando o cliente")
        cid = conn.execute(
            "INSERT INTO solicitacao_conferencia (solicitacao_id, dps_hash, solicitada_por) "
            "VALUES (%s,%s,%s) RETURNING id", (sid, dps["hash_sha256"], req.por)).fetchone()[0]
        msg = _mensagem_conferencia(f["nome"], f["seguradora"], sid)
        for canal in ("WHATSAPP", "EMAIL"):
            conn.execute(
                "INSERT INTO notificacao (solicitacao_id, canal, status_destino, mensagem, tipo) "
                "VALUES (%s,%s,%s,%s,%s)", (sid, canal, f["status"], msg, f"CONFERENCIA:{cid}"))
        conn.execute("INSERT INTO solicitacao_historico (solicitacao_id, status, nota, por) VALUES (%s,%s,%s,%s)",
                     (sid, f["status"], "Pedido de conferência enviado ao cliente", req.por))
    _agendar_envios(bg)
    return {"id": cid, "estado": "AGUARDANDO"}


@router.get("/v1/backoffice/solicitacoes/{sid}/conferencia", dependencies=[Depends(exigir_backoffice)])
def historico_conferencia(sid: str):
    _uuid_ou_404(sid)
    with conexao() as conn:
        if _ficha(conn, sid) is None:
            raise HTTPException(404, "solicitação não encontrada")
        cur = conn.cursor(row_factory=dict_row)
        cur.execute("SELECT id, solicitada_em, solicitada_por, resposta, respondida_em, nota "
                    "FROM solicitacao_conferencia WHERE solicitacao_id=%s ORDER BY id DESC", (sid,))
        confs = cur.fetchall()
        cur.execute("SELECT campo, por, em FROM acesso_dado_pessoal WHERE solicitacao_id=%s ORDER BY id DESC LIMIT 20",
                    (sid,))
        acessos = cur.fetchall()
        tem_dps = _dps(conn, sid) is not None
    return {"tem_dps": tem_dps, "estado": _estado(confs[0] if confs else None),
            "conferencias": confs, "acessos_cpf": [a for a in acessos if a["campo"] == "cpf"]}


@router.post("/v1/backoffice/solicitacoes/{sid}/cpf", dependencies=[Depends(exigir_backoffice)])
def mostrar_cpf(sid: str, req: PedidoConferenciaIn, request: Request):
    """CPF inteiro para a equipe preencher o portal da seguradora. Cada abertura fica registrada."""
    _uuid_ou_404(sid)
    with conexao() as conn:
        f = _ficha(conn, sid)
        if f is None:
            raise HTTPException(404, "solicitação não encontrada")
        conn.execute("INSERT INTO acesso_dado_pessoal (solicitacao_id, campo, por, ip) VALUES (%s,'cpf',%s,%s)",
                     (sid, req.por, request.client.host if request.client else None))
        n = conn.execute("SELECT count(*) FROM acesso_dado_pessoal WHERE solicitacao_id=%s AND campo='cpf'",
                         (sid,)).fetchone()[0]
    c = f["cpf"]
    return {"cpf": f"{c[:3]}.{c[3:6]}.{c[6:9]}-{c[9:]}", "acessos": n}


# --------------------------------------------------------------------------- cliente


@router.get("/v1/solicitacoes/{sid}/conferencia")
def ver_conferencia(sid: str):
    """O UUID da solicitação é a chave de acesso (como no acompanhamento)."""
    _uuid_ou_404(sid)
    with conexao() as conn:
        f = _ficha(conn, sid)
        if f is None:
            raise HTTPException(404, "solicitação não encontrada")
        c = _ultima(conn, sid)
        estado = _estado(c)
        base = {"estado": estado, "solicitada_em": c["solicitada_em"] if c else None,
                "respondida_em": c["respondida_em"] if c else None}
        if estado != "AGUARDANDO":
            return base
        dps = _dps(conn, sid)
        bens = conn.cursor(row_factory=dict_row)
        bens.execute("SELECT nome, data_nascimento, parentesco, percentual FROM beneficiario "
                     "WHERE solicitacao_id=%s ORDER BY id", (sid,))
        proposta = _proposta_da_ficha(f, bens.fetchall())
    return {**base, "seguradora": f["seguradora"], "proposta": proposta,
            "dps": [{"pergunta": i["pergunta"], "resposta": i["resposta_texto"]} for i in dps["conteudo"]["itens"]]}


@router.post("/v1/solicitacoes/{sid}/conferencia")
def responder_conferencia(sid: str, req: RespostaConferenciaIn, request: Request):
    _uuid_ou_404(sid)
    nota = (req.nota or "").strip()
    if req.acao == "corrigir" and not nota:
        raise HTTPException(422, "conte o que está errado para a equipe corrigir")
    with conexao() as conn:
        f = _ficha(conn, sid)
        if f is None:
            raise HTTPException(404, "solicitação não encontrada")
        c = _ultima(conn, sid)
        if _estado(c) != "AGUARDANDO":
            raise HTTPException(409, "não há conferência aguardando a sua resposta")
        resposta = "CONFIRMADA" if req.acao == "confirmar" else "CONTESTADA"
        conn.execute(
            "UPDATE solicitacao_conferencia SET resposta=%s, respondida_em=now(), nota=%s, ip=%s, user_agent=%s "
            "WHERE id=%s",
            (resposta, nota or None, request.client.host if request.client else None,
             (request.headers.get("user-agent") or "")[:300] or None, c["id"]))
        conn.execute(
            "INSERT INTO solicitacao_historico (solicitacao_id, status, nota, por) VALUES (%s,%s,%s,'cliente')",
            (sid, f["status"], "Cliente confirmou a conferência" if resposta == "CONFIRMADA"
             else f"Cliente apontou erro na conferência: {nota}"))
    return {"estado": resposta}
