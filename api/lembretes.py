"""Lembretes de prazo (rodada 3).

Quando a vez é do cliente (assinar ou pagar) e a seguradora deu uma data-limite, o sistema gera um lembrete
3 dias antes, 1 dia antes e no dia. Os lembretes entram na MESMA caixa de saída das demais mensagens: saem
sozinhos quando o envio automático estiver ligado (NOTIFICACOES_ATIVAS=1); até lá a equipe envia pelo painel.

    GET|POST /v1/backoffice/lembretes/gerar    gera os lembretes devidos hoje (idempotente)

Chamado todo dia pelo agendador da Vercel (vercel.json, com CRON_SECRET) ou à mão com a chave do backoffice.
"""

from __future__ import annotations

import hmac
import os
from datetime import date, datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, BackgroundTasks, Depends, Header, HTTPException
from psycopg.rows import dict_row

from .infra import conexao
from .solicitacoes import AGUARDANDO_CLIENTE, _agendar_envios, _primeiro_nome

router = APIRouter()

JANELAS = (3, 1, 0)  # dias que faltam para o prazo
_BRASIL = timezone(timedelta(hours=-3))  # sem horário de verão desde 2019


def hoje_no_brasil() -> date:
    return datetime.now(_BRASIL).date()


def lembretes_devidos(hoje: date, linhas: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Quais lembretes gerar hoje. Se o agendador falhou um dia, o lembrete da janela perdida sai no dia seguinte
    (usa a menor janela que ainda não passou); a chave única no banco impede repetir."""
    out = []
    for l in linhas:
        if l["status"] not in AGUARDANDO_CLIENTE or not l["prazo_acao"]:
            continue
        dias = (l["prazo_acao"] - hoje).days
        if not 0 <= dias <= max(JANELAS):
            continue
        janela = min(j for j in JANELAS if j >= dias)
        out.append({**l, "dias": dias,
                    "tipo": f"LEMBRETE:{l['status']}:{l['status_desde']:%Y%m%d}:D{janela}"})
    return out


def mensagem_lembrete(status: str, nome: str, seguradora: str, prazo: date, dias: int) -> str:
    quando = ("O prazo termina hoje" if dias == 0 else "O prazo termina amanhã" if dias == 1
              else f"Faltam {dias} dias")
    o_que = ("falta a sua assinatura para a proposta da " + seguradora + " seguir"
             if status == "AGUARDANDO_ASSINATURA"
             else f"falta o pagamento para a proposta da {seguradora} seguir. Ele é feito no ambiente da seguradora")
    return (f"{_primeiro_nome(nome)}, lembrete: {o_que}. {quando} ({prazo:%d/%m/%Y}). "
            "Depois dessa data a seguradora pode cancelar a proposta.")


def exigir_backoffice_ou_agendador(x_backoffice_key: Optional[str] = Header(None),
                                   authorization: Optional[str] = Header(None)):
    chave, cron = os.environ.get("BACKOFFICE_KEY"), os.environ.get("CRON_SECRET")
    if not chave and not cron:
        raise HTTPException(503, "desligado: BACKOFFICE_KEY e CRON_SECRET não configuradas")
    if chave and x_backoffice_key and hmac.compare_digest(x_backoffice_key, chave):
        return
    if cron and authorization and hmac.compare_digest(authorization, f"Bearer {cron}"):
        return
    raise HTTPException(401, "não autorizado")


def _gerar(hoje: date) -> Dict[str, int]:
    with conexao() as conn:
        cur = conn.cursor(row_factory=dict_row)
        cur.execute(
            "SELECT s.id, s.nome, s.status::text AS status, s.prazo_acao, s.status_desde, sg.nome AS seguradora "
            "FROM solicitacao s JOIN cotacao_item ci ON ci.id = s.cotacao_item_id "
            "JOIN produto_versao pv ON pv.id = ci.produto_versao_id JOIN produto p ON p.id = pv.produto_id "
            "JOIN seguradora sg ON sg.id = p.seguradora_id "
            "WHERE s.status IN ('AGUARDANDO_ASSINATURA','AGUARDANDO_PAGAMENTO') AND s.prazo_acao IS NOT NULL")
        devidos = lembretes_devidos(hoje, cur.fetchall())
        novas = 0
        for d in devidos:
            msg = mensagem_lembrete(d["status"], d["nome"], d["seguradora"], d["prazo_acao"], d["dias"])
            for canal in ("WHATSAPP", "EMAIL"):
                r = conn.execute(
                    "INSERT INTO notificacao (solicitacao_id, canal, status_destino, mensagem, tipo) "
                    "VALUES (%s,%s,%s,%s,%s) ON CONFLICT DO NOTHING",
                    (d["id"], canal, d["status"], msg, d["tipo"]))
                novas += r.rowcount
    return {"candidatos": len(devidos), "geradas": novas}


@router.api_route("/v1/backoffice/lembretes/gerar", methods=["GET", "POST"])
def gerar_lembretes(bg: BackgroundTasks, _=Depends(exigir_backoffice_ou_agendador)):
    r = _gerar(hoje_no_brasil())
    if r["geradas"]:
        _agendar_envios(bg)
    return {**r, "dia": hoje_no_brasil().isoformat()}
