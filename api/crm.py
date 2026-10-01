"""Envio do WhatsApp pelo CRM DeskComm (caixa de saída `notificacao`, canal WHATSAPP).

Dois passos na API do DeskComm, autenticados por token de servidor (`dsk_...`, escopo
`mcp:write`, criado em Configurações > Tokens de API do CRM):

    POST {DESKCOMM_URL}/api/v1/conversations/open-with-contact   {phone_number, name}
         -> {"data": {"conversation_id": ..., "contact_id": ...}}
    POST {DESKCOMM_URL}/api/v1/messages                          {conversation_id, type, body}
         cabeçalho Idempotency-Key = UUID estável da notificação

A chave de idempotência torna o reenvio seguro: se a resposta se perder e a mensagem for
tentada de novo, o CRM devolve o mesmo envio em vez de duplicar. Qualquer falha (rede, 4xx,
429 do ritmo de envio) deixa a notificação pendente para a próxima rodada.

Variáveis: DESKCOMM_URL (ex.: https://crm.seudominio.com.br), DESKCOMM_TOKEN,
DESKCOMM_CHANNEL_SESSION_ID (opcional: número de WhatsApp a usar; sem ele o CRM escolhe).
"""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
import uuid
from typing import Optional, Tuple

from .infra import conexao

_NS = uuid.UUID("6f1b6b0e-5a47-4d7e-9c0b-3e9c1c2f7a11")  # namespace fixo do Meu Guardião


class ErroCrm(Exception):
    pass


def crm_configurado() -> bool:
    return bool(os.environ.get("DESKCOMM_URL") and os.environ.get("DESKCOMM_TOKEN"))


def chave_idempotencia(notificacao_id: int) -> str:
    return str(uuid.uuid5(_NS, f"notificacao-{notificacao_id}"))


def _post(caminho: str, corpo: dict, extra_headers: Optional[dict] = None) -> dict:
    url = os.environ["DESKCOMM_URL"].rstrip("/") + caminho
    req = urllib.request.Request(
        url, data=json.dumps(corpo).encode("utf-8"), method="POST",
        headers={"Content-Type": "application/json",
                 "Authorization": f"Bearer {os.environ['DESKCOMM_TOKEN']}", **(extra_headers or {})})
    try:
        with urllib.request.urlopen(req, timeout=20) as r:
            return json.loads(r.read().decode("utf-8") or "{}")
    except urllib.error.HTTPError as e:
        raise ErroCrm(f"CRM respondeu {e.code} em {caminho}") from None
    except (urllib.error.URLError, TimeoutError, ValueError) as e:
        raise ErroCrm(f"CRM inacessível em {caminho}: {type(e).__name__}") from None


def enviar_whatsapp(celular: str, nome: str, mensagem: str, notificacao_id: int) -> None:
    """`celular` com DDD, só dígitos (formato do banco). Levanta ErroCrm em qualquer falha."""
    corpo = {"phone_number": f"+55{celular}", "name": nome}
    sessao = os.environ.get("DESKCOMM_CHANNEL_SESSION_ID")
    if sessao:
        corpo["channel_session_id"] = sessao
    conversa = _post("/api/v1/conversations/open-with-contact", corpo)
    conversa_id = (conversa.get("data") or {}).get("conversation_id")
    if not conversa_id:
        raise ErroCrm("CRM não devolveu a conversa")
    _post("/api/v1/messages", {"conversation_id": conversa_id, "type": "text", "body": mensagem},
          {"Idempotency-Key": chave_idempotencia(notificacao_id)})


def despachar_whatsapp(limite: int = 50) -> Tuple[int, int]:
    """Envia os WhatsApps pendentes pelo CRM. Devolve (enviados, falhas)."""
    if not crm_configurado():
        return 0, 0
    enviados = falhas = 0
    with conexao() as conn:
        pend = conn.execute(
            "SELECT n.id, n.mensagem, s.nome, s.celular FROM notificacao n "
            "JOIN solicitacao s ON s.id = n.solicitacao_id "
            "WHERE n.canal = 'WHATSAPP' AND n.enviada_em IS NULL "
            "ORDER BY n.id LIMIT %s FOR UPDATE OF n SKIP LOCKED", (limite,)).fetchall()
        for nid, mensagem, nome, celular in pend:
            try:
                enviar_whatsapp(celular, nome, mensagem, nid)
            except ErroCrm:
                falhas += 1
                continue
            conn.execute("UPDATE notificacao SET enviada_em = now() WHERE id = %s", (nid,))
            enviados += 1
    return enviados, falhas
