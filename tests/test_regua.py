"""Régua de status (rodada 3): lógica pura, sem banco."""
from datetime import date, datetime

from api.solicitacoes import (
    AGUARDANDO_CLIENTE, COM_QUEM, MENSAGENS, REGUA, TRANSICOES, _mensagem, _regua,
)

CODIGOS = [c for c, _, _ in REGUA]


def _hist(*status):
    return [{"status": s, "em": datetime(2026, 10, 1, 10, i)} for i, s in enumerate(status)]


def test_regua_tem_os_dois_estados_em_que_o_cliente_age_na_ordem_do_documento():
    assert CODIGOS == ["RECEBIDA", "EM_PREPARACAO", "AGUARDANDO_ASSINATURA", "ENVIADA",
                       "EM_ANALISE", "AGUARDANDO_PAGAMENTO", "APROVADA", "EMITIDA"]
    assert all(COM_QUEM[s] == "CLIENTE" for s in AGUARDANDO_CLIENTE)


def test_todo_status_tem_transicao_vez_e_mensagem_e_nenhum_destino_e_desconhecido():
    todos = set(TRANSICOES)
    assert set(COM_QUEM) == todos
    assert set(MENSAGENS) == todos
    for origem, destinos in TRANSICOES.items():
        assert destinos <= todos, origem
    # status finais não saem
    assert not TRANSICOES["EMITIDA"] and not TRANSICOES["RECUSADA"] and not TRANSICOES["CANCELADA"]


def test_ninguem_fica_preso_todo_status_nao_final_chega_a_emitida():
    def alcanca(ini):
        visto, fila = {ini}, [ini]
        while fila:
            for d in TRANSICOES[fila.pop()]:
                if d not in visto:
                    visto.add(d)
                    fila.append(d)
        return visto
    for s in TRANSICOES:
        if TRANSICOES[s]:
            assert "EMITIDA" in alcanca(s), s


def test_fluxo_novo_passa_pelos_dois_estados_do_cliente():
    caminho = ["RECEBIDA", "EM_PREPARACAO", "AGUARDANDO_ASSINATURA", "ENVIADA", "EM_ANALISE",
               "AGUARDANDO_PAGAMENTO", "APROVADA", "EMITIDA"]
    for a, b in zip(caminho, caminho[1:]):
        assert b in TRANSICOES[a], f"{a} -> {b}"


def test_regua_marca_o_passo_do_cliente_como_em_andamento():
    estados = {p["codigo"]: p["estado"] for p in _regua(
        "AGUARDANDO_ASSINATURA", _hist("RECEBIDA", "EM_PREPARACAO", "AGUARDANDO_ASSINATURA"))}
    assert estados["EM_PREPARACAO"] == "CONCLUIDO"
    assert estados["AGUARDANDO_ASSINATURA"] == "EM_ANDAMENTO"
    assert estados["ENVIADA"] == "AGUARDANDO"


def test_pendencia_continua_dentro_da_analise_e_emitida_conclui_tudo():
    estados = {p["codigo"]: p["estado"] for p in _regua("PENDENCIA", _hist("RECEBIDA", "EM_ANALISE"))}
    assert estados["EM_ANALISE"] == "EM_ANDAMENTO"
    assert {p["estado"] for p in _regua("EMITIDA", [])} == {"CONCLUIDO"}


def test_mensagem_de_assinatura_e_pagamento_leva_prazo_so_quando_informado():
    sem = _mensagem("AGUARDANDO_ASSINATURA", "ana silva", "Icatu")
    com = _mensagem("AGUARDANDO_PAGAMENTO", "ana silva", "Azos", prazo=date(2026, 10, 28))
    assert "assinatura" in sem and "Icatu" in sem and "até" not in sem
    assert "28/10/2026" in com and "ambiente da Azos" in com and "não aqui no nosso site" in com


def test_etapas_da_primeira_mensagem_nao_prometem_prazo():
    # A primeira mensagem lista os rótulos da régua; nenhum pode falar de prazo ou dias.
    for _, rotulo, _ in REGUA:
        assert "prazo" not in rotulo.lower() and "dias" not in rotulo.lower()
