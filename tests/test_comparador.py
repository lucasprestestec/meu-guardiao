"""Testes do comparador. Provam que preço baixo não vira recomendação."""
import pytest

from motor_dor import Dependente, Diagnostico, calcular
from motor_dor.catalogo_ficticio import ACIDENTES, CATALOGO, DIGITAL, VITALICIA
from motor_dor.comparador import comparar, cotar, recomendados

CLIENTE = Diagnostico(idade=38, renda_mensal_liquida=25_000,
                      custo_familiar_mensal=18_000,
                      dependentes=[Dependente(idade=6)])
MAPA = calcular(CLIENTE)
ARGS = (MAPA, 38, "M", False)


def test_produto_mais_barato_nao_e_o_recomendado():
    """O núcleo do produto: barato e incompleto não vence."""
    cot = comparar(CATALOGO, *ARGS)
    r = recomendados(cot)
    assert r["menor_preco"].produto is ACIDENTES
    assert r["recomendado"].produto is not ACIDENTES


def test_produto_so_de_acidente_tem_aderencia_baixa():
    c = cotar(ACIDENTES, *ARGS)
    assert c.aderencia_total < 0.25
    assert "NEC_DOENCA_GRAVE" in c.coberturas_ausentes


def test_cobertura_ausente_e_sinalizada_e_nao_ignorada():
    c = cotar(ACIDENTES, *ARGS)
    item = next(i for i in c.itens if i.necessidade == "NEC_DOENCA_GRAVE")
    assert item.codigo_cobertura is None
    assert item.aderencia == 0.0
    assert item.premio_mensal == 0.0
    assert any("não oferece" in o for o in item.observacoes)


def test_invalidez_por_acidente_vale_menos_que_por_doenca():
    """IPA e IFPD não são a mesma coisa, ainda que o capital seja igual."""
    a = next(i for i in cotar(VITALICIA, *ARGS).itens
             if i.necessidade == "NEC_INVALIDEZ")
    b = next(i for i in cotar(ACIDENTES, *ARGS).itens
             if i.necessidade == "NEC_INVALIDEZ")
    assert a.qualidade_cobertura > b.qualidade_cobertura * 2


def test_rol_de_dg_afeta_aderencia():
    """32 doenças vs 10 doenças com o mesmo capital não são equivalentes."""
    a = next(i for i in cotar(VITALICIA, *ARGS).itens
             if i.necessidade == "NEC_DOENCA_GRAVE")
    b = next(i for i in cotar(DIGITAL, *ARGS).itens
             if i.necessidade == "NEC_DOENCA_GRAVE")
    assert a.capital_contratado == b.capital_contratado
    assert a.aderencia > b.aderencia


def test_teto_de_capital_limita_e_avisa():
    c = cotar(DIGITAL, *ARGS)
    item = next(i for i in c.itens if i.necessidade == "NEC_MORTE")
    assert item.capital_contratado == 3_000_000
    assert any("limitado" in o for o in item.observacoes)


def test_premio_cresce_com_a_idade():
    jovem = cotar(VITALICIA, MAPA, 25, "M", False).premio_mensal_total
    maduro = cotar(VITALICIA, MAPA, 55, "M", False).premio_mensal_total
    assert maduro > jovem


def test_tarifa_ficticia_sempre_alerta():
    """Trava de segurança: nada fictício pode ir ao consumidor."""
    for c in comparar(CATALOGO, *ARGS):
        assert any("FICTÍCIA" in a for a in c.alertas)


def test_ordenacao_por_aderencia():
    cot = comparar(CATALOGO, *ARGS)
    ader = [c.aderencia_total for c in cot]
    assert ader == sorted(ader, reverse=True)


def test_idade_fora_da_faixa_alerta():
    c = cotar(DIGITAL, MAPA, 63, "M", False)  # produto aceita até 60
    assert any("faixa de aceitação" in a for a in c.alertas)


def test_determinismo():
    a = [(c.produto.nome, round(c.premio_mensal_total, 2)) for c in comparar(CATALOGO, *ARGS)]
    b = [(c.produto.nome, round(c.premio_mensal_total, 2)) for c in comparar(CATALOGO, *ARGS)]
    assert a == b
