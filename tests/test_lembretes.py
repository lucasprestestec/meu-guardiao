"""Lembretes de prazo (rodada 3): lógica pura, sem banco."""
from datetime import date, datetime

from api.lembretes import lembretes_devidos, mensagem_lembrete

HOJE = date(2026, 10, 20)


def linha(status="AGUARDANDO_ASSINATURA", prazo=date(2026, 10, 23), desde=datetime(2026, 10, 15, 10, 0)):
    return {"id": "x", "nome": "Ana Silva", "status": status, "prazo_acao": prazo, "status_desde": desde,
            "seguradora": "Azos"}


def janelas(prazo, hoje=HOJE, **kw):
    return [d["tipo"].rsplit(":", 1)[1] for d in lembretes_devidos(hoje, [linha(prazo=prazo, **kw)])]


def test_gera_lembrete_3_dias_antes_1_dia_antes_e_no_dia():
    assert janelas(date(2026, 10, 23)) == ["D3"]
    assert janelas(date(2026, 10, 21)) == ["D1"]
    assert janelas(date(2026, 10, 20)) == ["D0"]


def test_se_o_agendador_falhou_o_lembrete_da_janela_perdida_sai_no_dia_seguinte():
    assert janelas(date(2026, 10, 22)) == ["D3"]  # faltam 2 dias: ainda é a janela de 3 que não saiu


def test_fora_da_janela_ou_sem_prazo_nao_gera():
    assert janelas(date(2026, 10, 30)) == []   # faltam 10 dias
    assert janelas(date(2026, 10, 19)) == []   # prazo já passou
    assert lembretes_devidos(HOJE, [linha(prazo=None)]) == []


def test_so_gera_quando_a_vez_e_do_cliente():
    for st in ("EM_ANALISE", "ENVIADA", "PENDENCIA", "EMITIDA", "CANCELADA"):
        assert lembretes_devidos(HOJE, [linha(status=st)]) == [], st
    assert len(lembretes_devidos(HOJE, [linha(status="AGUARDANDO_PAGAMENTO")])) == 1


def test_chave_do_lembrete_muda_quando_o_cliente_volta_ao_mesmo_status_depois():
    a = lembretes_devidos(HOJE, [linha(desde=datetime(2026, 10, 15))])[0]["tipo"]
    b = lembretes_devidos(HOJE, [linha(desde=datetime(2026, 10, 18))])[0]["tipo"]
    assert a != b


def test_mensagens_por_dia_e_por_status():
    p = date(2026, 10, 23)
    assert "assinatura" in mensagem_lembrete("AGUARDANDO_ASSINATURA", "ana silva", "Azos", p, 3)
    m = mensagem_lembrete("AGUARDANDO_PAGAMENTO", "ana silva", "Azos", p, 3)
    assert "pagamento" in m and "ambiente da seguradora" in m and "Faltam 3 dias" in m and "23/10/2026" in m
    assert "termina amanhã" in mensagem_lembrete("AGUARDANDO_ASSINATURA", "ana", "Azos", p, 1)
    assert "termina hoje" in mensagem_lembrete("AGUARDANDO_ASSINATURA", "ana", "Azos", p, 0)
    assert mensagem_lembrete("AGUARDANDO_ASSINATURA", "ana silva", "Azos", p, 3).startswith("Ana,")
