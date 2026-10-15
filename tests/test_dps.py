"""DPS por seguradora (rodada 3): banco de perguntas, ramificação, validação e prova (hash). Sem banco."""
from api.dps import (
    hash_dps, instantaneo, perguntas_visiveis, questionario_de, questionario_valido_para_producao,
    validar_respostas,
)
from api.proposta import AZOS, COMUM, ICATU


def azos_ok():
    q = questionario_de(AZOS)
    r = {}
    for p in q["perguntas"]:
        r[p["id"]] = (p["opcoes"][-1] if p["tipo"] == "unica" else
                      [p["exclusiva"]] if p["tipo"] == "multipla" else False)
    return q, r


def icatu_ok(bebe=False):
    q = questionario_de(ICATU)
    r = {p["id"]: False for p in q["perguntas"] if p["tipo"] == "sim_nao" and p["depende"] is None}
    if bebe:
        r.update({"I9": True, "I9.1": False, "I9.1.1": 2, "I9.1.2": 1, "I9.1.3": 0})
    return q, r


def test_so_azos_e_icatu_tem_questionario():
    assert questionario_de(COMUM) is None
    assert len(questionario_de(AZOS)["perguntas"]) == 13
    # 12 perguntas principais (a 1, peso e altura, vem do cadastro da proposta) + 4 sub-perguntas da 9
    ids = [p["id"] for p in questionario_de(ICATU)["perguntas"]]
    assert len([i for i in ids if "." not in i]) == 12 and len(ids) == 16


def test_questionarios_tem_ids_unicos_e_opcoes_coerentes():
    for perfil in (AZOS, ICATU):
        ps = questionario_de(perfil)["perguntas"]
        assert len({p["id"] for p in ps}) == len(ps)
        for p in ps:
            if p["tipo"] in ("unica", "multipla"):
                assert p["opcoes"] and len(set(p["opcoes"])) == len(p["opcoes"])
            if p["tipo"] == "multipla":
                assert p["exclusiva"] in p["opcoes"]


def test_azos_completa_passa():
    q, r = azos_ok()
    erros, norm = validar_respostas(q, r)
    assert erros == [] and set(norm) == {p["id"] for p in q["perguntas"]}


def test_ramificacao_da_icatu_dose_de_bebida_so_para_quem_bebe():
    q, r = icatu_ok(bebe=False)
    assert "I9.1.1" not in {p["id"] for p in perguntas_visiveis(q, r)}
    erros, norm = validar_respostas(q, {**r, "I9.1.1": 5})  # resposta a pergunta oculta é descartada
    assert erros == [] and "I9.1.1" not in norm
    q, r2 = icatu_ok(bebe=True)
    assert "I9.1.1" in {p["id"] for p in perguntas_visiveis(q, r2)}
    assert validar_respostas(q, r2)[0] == []
    assert any("I9.1" in e for e in validar_respostas(q, {**r2, "I9.1": None})[0])  # passa a ser obrigatória


def test_resposta_faltando_ou_invalida_e_apontada():
    q, r = azos_ok()
    assert any("A6" in e for e in validar_respostas(q, {k: v for k, v in r.items() if k != "A6"})[0])
    assert any("A3" in e for e in validar_respostas(q, {**r, "A3": "Talvez"})[0])
    e = validar_respostas(q, {**r, "A2": ["Nenhuma dessas.", "Paralisia cerebral."]})[0]
    assert any("não pode vir junto" in m for m in e)
    assert validar_respostas(q, {**r, "A2": ["Paralisia cerebral."]})[0] == []
    assert any("Pergunta desconhecida" in m for m in validar_respostas(q, {**r, "ZZ": 1})[0])
    assert validar_respostas(q, {**r, "A7": []})[0]  # múltipla não pode ficar vazia


def test_numero_nao_aceita_negativo_nem_booleano():
    q, r = icatu_ok(bebe=True)
    assert validar_respostas(q, {**r, "I9.1.1": -1})[0]
    assert validar_respostas(q, {**r, "I9.1.1": True})[0]


def test_instantaneo_guarda_o_texto_exato_e_o_hash_muda_com_qualquer_resposta():
    q, r = azos_ok()
    norm = validar_respostas(q, r)[1]
    s = instantaneo(q, norm)
    assert s["itens"][0]["pergunta"] == q["perguntas"][0]["texto"] and len(s["itens"]) == 13
    h1 = hash_dps(s)
    assert h1 == hash_dps(instantaneo(q, norm)) and len(h1) == 64
    assert hash_dps(instantaneo(q, {**norm, "A6": True})) != h1


def test_nenhum_questionario_com_pergunta_nao_confirmada_vale_para_producao():
    # Verdade hoje: a Azos tem o enunciado do bloco 1 deduzido; a Icatu tem 5 perguntas por confirmar.
    assert not questionario_valido_para_producao(questionario_de(AZOS))
    assert not questionario_valido_para_producao(questionario_de(ICATU))
    assert {p["id"] for p in questionario_de(ICATU)["perguntas"] if not p["confirmada"]} == \
        {"I4", "I7", "I9", "I9.1", "I13"}
    assert [p["id"] for p in questionario_de(AZOS)["perguntas"] if not p["confirmada"]] == ["A1"]


# --- regras de entrada na criação da solicitação (sem banco) -----------------------------------

from datetime import date  # noqa: E402

import pytest  # noqa: E402
from fastapi import HTTPException  # noqa: E402

from api.solicitacoes import SolicitacaoIn, _preparar_dps  # noqa: E402

_BASE = dict(cotacao_id="x", produto_versao_id="y", consentimentos=[],
             dados=dict(nome="Ana Silva", cpf="52998224725", data_nascimento=date(1988, 1, 1),
                        email="a@b.co", celular="11987654321"))


def test_dps_ausente_so_e_aceita_enquanto_nao_for_obrigatoria(monkeypatch):
    monkeypatch.delenv("DPS_OBRIGATORIA", raising=False)
    assert _preparar_dps(SolicitacaoIn(**_BASE), "Azos", False) is None
    monkeypatch.setenv("DPS_OBRIGATORIA", "1")
    with pytest.raises(HTTPException) as e:
        _preparar_dps(SolicitacaoIn(**_BASE), "Azos", False)
    assert e.value.status_code == 422


def test_seguradora_sem_dps_nao_exige_nada(monkeypatch):
    monkeypatch.setenv("DPS_OBRIGATORIA", "1")
    assert _preparar_dps(SolicitacaoIn(**_BASE), "Exemplo Seguros", False) is None


def test_produto_real_com_questionario_nao_confirmado_e_barrado(monkeypatch):
    monkeypatch.delenv("DPS_ACEITAR_NAO_CONFIRMADA", raising=False)
    q, r = azos_ok()
    with pytest.raises(HTTPException) as e:
        _preparar_dps(SolicitacaoIn(**_BASE, dps=r), "Azos", True)
    assert e.value.status_code == 409 and "conferência" in e.value.detail
    monkeypatch.setenv("DPS_ACEITAR_NAO_CONFIRMADA", "1")  # liberação consciente, a equipe decide
    snap, h, confirmada = _preparar_dps(SolicitacaoIn(**_BASE, dps=r), "Azos", True)
    assert confirmada is False and len(h) == 64 and len(snap["itens"]) == 13


def test_demonstracao_pode_usar_o_questionario_de_uma_seguradora_real(monkeypatch):
    q, r = azos_ok()
    monkeypatch.delenv("DPS_PERFIL_DEMONSTRACAO", raising=False)
    assert _preparar_dps(SolicitacaoIn(**_BASE, dps=r), "Exemplo Seguros", True) is None
    monkeypatch.setenv("DPS_PERFIL_DEMONSTRACAO", "AZOS")
    snap, _, _ = _preparar_dps(SolicitacaoIn(**_BASE, dps=r), "Exemplo Seguros", False)
    assert snap["perfil"] == "AZOS"


def test_respostas_invalidas_viram_422_com_a_lista_de_erros():
    with pytest.raises(HTTPException) as e:
        _preparar_dps(SolicitacaoIn(**_BASE, dps={"A6": "talvez"}), "Azos", False)
    assert e.value.status_code == 422 and "A6" in e.value.detail and "A1" in e.value.detail
