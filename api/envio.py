"""Envio de e-mail da caixa de saída (tabela `notificacao`).

Só e-mail é automático aqui. O WhatsApp sai pelo CRM do corretor: o CRM (ou uma
automação) lê as pendentes em GET /v1/backoffice/notificacoes/pendentes?canal=WHATSAPP
e confirma cada envio em POST /v1/backoffice/notificacoes/{id}/enviada.

Variáveis de ambiente (sem SMTP_HOST e EMAIL_REMETENTE o envio fica desligado):
    SMTP_HOST, SMTP_PORTA (587 padrão; 465 = SSL), SMTP_USUARIO, SMTP_SENHA,
    EMAIL_REMETENTE (ex.: "Meu Guardião <contato@dominio.com.br>"), EMAIL_ASSUNTO
"""

from __future__ import annotations

import os
import smtplib
from email.message import EmailMessage
from typing import Tuple

from .infra import conexao

ASSUNTO_PADRAO = "Atualização da sua solicitação de seguro"


def email_configurado() -> bool:
    return bool(os.environ.get("SMTP_HOST") and os.environ.get("EMAIL_REMETENTE"))


def enviar_email(destino: str, assunto: str, corpo: str) -> None:
    msg = EmailMessage()
    msg["From"], msg["To"], msg["Subject"] = os.environ["EMAIL_REMETENTE"], destino, assunto
    msg.set_content(corpo)
    host, porta = os.environ["SMTP_HOST"], int(os.environ.get("SMTP_PORTA", "587"))
    if porta == 465:
        smtp = smtplib.SMTP_SSL(host, porta, timeout=15)
    else:
        smtp = smtplib.SMTP(host, porta, timeout=15)
        smtp.starttls()
    with smtp:
        if os.environ.get("SMTP_USUARIO"):
            smtp.login(os.environ["SMTP_USUARIO"], os.environ.get("SMTP_SENHA", ""))
        smtp.send_message(msg)


def despachar_emails(limite: int = 50) -> Tuple[int, int]:
    """Envia os e-mails pendentes. Devolve (enviados, falhas). Uma falha não trava as demais."""
    if not email_configurado():
        return 0, 0
    enviados = falhas = 0
    assunto = os.environ.get("EMAIL_ASSUNTO", ASSUNTO_PADRAO)
    with conexao() as conn:
        pend = conn.execute(
            "SELECT n.id, n.mensagem, s.email FROM notificacao n JOIN solicitacao s ON s.id = n.solicitacao_id "
            "WHERE n.canal = 'EMAIL' AND n.enviada_em IS NULL ORDER BY n.id LIMIT %s "
            "FOR UPDATE OF n SKIP LOCKED", (limite,)
        ).fetchall()
        for nid, mensagem, email in pend:
            try:
                enviar_email(email, assunto, mensagem)
            except Exception:
                falhas += 1
                continue
            conn.execute("UPDATE notificacao SET enviada_em = now() WHERE id = %s", (nid,))
            enviados += 1
    return enviados, falhas
