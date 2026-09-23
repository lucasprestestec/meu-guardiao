"""Testes do Motor DOR$ v1.0.

Três camadas:
  1. Funções financeiras isoladas.
  2. Invariantes que devem valer para QUALQUER entrada.
  3. Casos concretos (golden tests) que travam os números atuais. Se um
     número mudar sem que a versão do Motor mude, o teste quebra — que é
     exatamente o que queremos.
"""

from __future__ import annotations

import math

import pytest

from motor_dor import (
    Dependente,
    Diagnostico,
    Dividas,
    FaseDeVida,
    Projetos,
    SeguroAtual,
    SituacaoProfissional,
    calcular,
)
from motor_dor.financeiro import valor_presente_anuidade
from motor_dor.motor import calcular_horizonte, calcular_pesos
from motor_dor.parametros import PARAMETROS_V1

P = PARAMETROS_V1


# ---------------------------------------------------------------------------
# 1. Financeiro
# ---------------------------------------------------------------------------


def test_vp_anuidade_conhecida():
    # 10.000/ano por 10 anos a 3% real
    vp = valor_presente_anuidade(10_000, 10, 0.03)
    assert math.isclose(vp, 85_302.03, rel_tol=1e-4)


def test_vp_taxa_zero_degenera_para_soma_simples():
    assert valor_presente_anuidade(1_000, 20, 0.0) == pytest.approx(20_000)


def test_vp_valores_nao_positivos():
    assert valor_presente_anuidade(0, 10, 0.03) == 0.0
    assert valor_presente_anuidade(1_000, 0, 0.03) == 0.0


def test_vp_taxa_maior_reduz_valor_presente():
    assert valor_presente_anuidade(10_000, 20, 0.06) < valor_presente_anuidade(
        10_000, 20, 0.03
    )


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def diag_recem_pai() -> Diagnostico:
    """Persona: acabou de ter filho. Exposição concentrada em morte."""
    return Diagnostico(
        idade=34,
        renda_mensal_liquida=22_000,
        custo_familiar_mensal=15_000,
        situacao_profissional=SituacaoProfissional.CLT,
        dependentes=[Dependente(idade=1), Dependente(idade=34)],
        dividas=Dividas(imobiliaria=450_000, imobiliaria_tem_prestamista=True),
        projetos=Projetos(educacao_filhos=400_000),
        patrimonio_liquido=180_000,
        patrimonio_inventariavel=700_000,
        meses_de_reserva=4,
        seguro_atual=SeguroAtual(morte=500_000),
    )


def diag_dentista() -> Diagnostico:
    """Persona: dentista. Exposição concentrada em invalidez e renda."""
    return Diagnostico(
        idade=41,
        renda_mensal_liquida=35_000,
        custo_familiar_mensal=20_000,
        situacao_profissional=SituacaoProfissional.MANUAL_ESPECIALIZADO,
        dependentes=[Dependente(idade=9)],
        dividas=Dividas(empresarial=300_000),
        patrimonio_liquido=400_000,
        meses_de_reserva=2,
        seguro_atual=SeguroAtual(morte=1_000_000, invalidez=300_000),
    )


def diag_jovem_solteiro() -> Diagnostico:
    """Persona: jovem sem dependentes. Morte pesa pouco, invalidez pesa muito."""
    return Diagnostico(
        idade=27,
        renda_mensal_liquida=12_000,
        custo_familiar_mensal=6_000,
        situacao_profissional=SituacaoProfissional.AUTONOMO,
        fase_de_vida=FaseDeVida.JOVEM_SEM_DEPENDENTES,
        patrimonio_liquido=60_000,
        meses_de_reserva=5,
        seguro_atual=SeguroAtual(),
    )


# ---------------------------------------------------------------------------
# 2. Invariantes
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "d", [diag_recem_pai(), diag_dentista(), diag_jovem_solteiro()]
)
def test_nenhuma_necessidade_negativa(d):
    mapa = calcular(d)
    for n in mapa.necessidades:
        assert n.valor_necessario >= 0
        assert n.gap >= 0
        assert 0.0 <= n.cobertura <= 1.0


@pytest.mark.parametrize(
    "d", [diag_recem_pai(), diag_dentista(), diag_jovem_solteiro()]
)
def test_score_entre_zero_e_cem(d):
    assert 0 <= calcular(d).protection_score <= 100


@pytest.mark.parametrize(
    "d", [diag_recem_pai(), diag_dentista(), diag_jovem_solteiro()]
)
def test_determinismo(d):
    assert calcular(d).to_dict() == calcular(d).to_dict()


@pytest.mark.parametrize(
    "d", [diag_recem_pai(), diag_dentista(), diag_jovem_solteiro()]
)
def test_invalidez_nunca_menor_que_morte(d):
    """Na invalidez o segurado continua consumindo e gera custo extra."""
    mapa = calcular(d)
    assert (
        mapa.por_codigo("NEC_INVALIDEZ").valor_necessario
        >= mapa.por_codigo("NEC_MORTE").valor_necessario
    )


def test_mais_patrimonio_reduz_necessidade_de_morte():
    base = diag_recem_pai()
    rico = Diagnostico(**{**base.__dict__, "patrimonio_liquido": 2_000_000})
    assert (
        calcular(rico).por_codigo("NEC_MORTE").valor_necessario
        < calcular(base).por_codigo("NEC_MORTE").valor_necessario
    )


def test_mais_seguro_aumenta_score():
    base = diag_jovem_solteiro()
    coberto = Diagnostico(
        **{
            **base.__dict__,
            "seguro_atual": SeguroAtual(
                morte=500_000, invalidez=2_000_000, doenca_grave=400_000, dit_diaria=400
            ),
        }
    )
    assert calcular(coberto).protection_score > calcular(base).protection_score


def test_prestamista_reduz_necessidade_de_morte():
    sem = Diagnostico(
        **{
            **diag_recem_pai().__dict__,
            "dividas": Dividas(imobiliaria=450_000, imobiliaria_tem_prestamista=False),
        }
    )
    com = diag_recem_pai()
    delta = (
        calcular(sem).por_codigo("NEC_MORTE").valor_necessario
        - calcular(com).por_codigo("NEC_MORTE").valor_necessario
    )
    assert delta == pytest.approx(450_000)


def test_patrimonio_nao_desconta_doenca_grave():
    """Decisão metodológica explícita: DG não desconta patrimônio."""
    base = diag_dentista()
    rico = Diagnostico(**{**base.__dict__, "patrimonio_liquido": 5_000_000})
    assert (
        calcular(rico).por_codigo("NEC_DOENCA_GRAVE").valor_necessario
        == calcular(base).por_codigo("NEC_DOENCA_GRAVE").valor_necessario
    )


# ---------------------------------------------------------------------------
# Pesos por perfil — o que diferencia dentista de recém-pai
# ---------------------------------------------------------------------------


def test_dentista_prioriza_invalidez_e_renda():
    pesos = calcular_pesos(diag_dentista(), P)
    assert pesos["NEC_INVALIDEZ"] > pesos["NEC_MORTE"]
    assert pesos["NEC_RENDA"] > P.peso_base["NEC_RENDA"]


def test_recem_pai_prioriza_morte():
    pesos = calcular_pesos(diag_recem_pai(), P)
    assert pesos["NEC_MORTE"] > pesos["NEC_DOENCA_GRAVE"]


def test_jovem_solteiro_despriorizado_em_morte():
    pesos = calcular_pesos(diag_jovem_solteiro(), P)
    assert pesos["NEC_MORTE"] < pesos["NEC_INVALIDEZ"]


def test_reserva_maior_reduz_peso_da_renda():
    base = diag_dentista()
    folgado = Diagnostico(**{**base.__dict__, "meses_de_reserva": 12})
    assert (
        calcular_pesos(folgado, P)["NEC_RENDA"]
        < calcular_pesos(base, P)["NEC_RENDA"]
    )


# ---------------------------------------------------------------------------
# Horizonte
# ---------------------------------------------------------------------------


def test_horizonte_segue_o_dependente_mais_novo():
    h, _ = calcular_horizonte(diag_recem_pai(), P)
    assert h == pytest.approx(P.idade_independencia_filho - 1)


def test_horizonte_escolhido_pelo_cliente_tem_precedencia():
    d = Diagnostico(**{**diag_recem_pai().__dict__, "horizonte_protecao_anos": 10})
    h, origem = calcular_horizonte(d, P)
    assert h == 10 and "cliente" in origem


def test_horizonte_respeita_teto():
    d = Diagnostico(
        **{**diag_recem_pai().__dict__, "horizonte_protecao_anos": 999}
    )
    h, _ = calcular_horizonte(d, P)
    assert h == P.horizonte_maximo_anos


# ---------------------------------------------------------------------------
# Validação de entrada
# ---------------------------------------------------------------------------


def test_rejeita_idade_absurda():
    with pytest.raises(ValueError):
        calcular(Diagnostico(idade=0, renda_mensal_liquida=1, custo_familiar_mensal=1))


def test_rejeita_custo_desproporcional():
    with pytest.raises(ValueError, match="erro de"):
        calcular(
            Diagnostico(
                idade=40, renda_mensal_liquida=10_000, custo_familiar_mensal=90_000
            )
        )


def test_alerta_de_prestamista():
    d = Diagnostico(
        **{
            **diag_recem_pai().__dict__,
            "dividas": Dividas(imobiliaria=450_000, imobiliaria_tem_prestamista=False),
        }
    )
    assert any("prestamista" in a for a in calcular(d).alertas)


def test_alerta_de_diaria_acima_da_renda():
    d = Diagnostico(
        **{
            **diag_dentista().__dict__,
            "seguro_atual": SeguroAtual(dit_diaria=5_000),
        }
    )
    assert any("diária" in a.lower() for a in calcular(d).alertas)


# ---------------------------------------------------------------------------
# 3. Golden tests — travam os números da v1.0.0
# ---------------------------------------------------------------------------


def test_golden_recem_pai():
    mapa = calcular(diag_recem_pai())
    assert mapa.versao_motor == "1.0.0"
    assert mapa.por_codigo("NEC_MORTE").valor_necessario == pytest.approx(
        2_577_887.13, abs=0.5
    )
    assert mapa.por_codigo("NEC_DOENCA_GRAVE").valor_necessario == pytest.approx(
        464_000.00, abs=0.5
    )
    assert mapa.por_codigo("NEC_RENDA").valor_necessario == pytest.approx(
        733.33, abs=0.01
    )
    assert mapa.protection_score == 8
    # NOTA: o Motor aponta INVALIDEZ, não morte, como vulnerabilidade
    # principal deste recém-pai — morte tem peso maior (1.5 vs 1.3), mas já
    # tem R$ 500 mil contratados, enquanto invalidez está totalmente
    # descoberta. [VALIDAR com o especialista se a priorização está certa]
    assert mapa.vulnerabilidade_principal == "NEC_INVALIDEZ"


def test_golden_dentista():
    mapa = calcular(diag_dentista())
    assert mapa.vulnerabilidade_principal == "NEC_INVALIDEZ"
    assert mapa.por_codigo("NEC_RENDA").valor_necessario == pytest.approx(
        1_166.67, abs=0.01
    )


def test_golden_jovem_solteiro():
    mapa = calcular(diag_jovem_solteiro())
    assert mapa.protection_score == 0  # nenhum seguro contratado
    assert mapa.vulnerabilidade_principal == "NEC_INVALIDEZ"


def test_memoria_de_calculo_completa():
    """Todo número exibido precisa ser explicável."""
    mapa = calcular(diag_recem_pai())
    m = mapa.por_codigo("NEC_MORTE").memoria
    reconstruido = (
        m["vp_renda_familiar"]
        + m["dividas"]
        + m["projetos"]
        + m["custo_inventario"]
        - m["recursos_proprios_utilizaveis"]
    )
    assert reconstruido == pytest.approx(
        mapa.por_codigo("NEC_MORTE").valor_necessario, abs=0.01
    )


def test_formatacao_nao_destroi_virgulas_gramaticais():
    """Regressão: .replace(',', '.') global quebrava a pontuação do texto."""
    j = calcular(diag_recem_pai()).por_codigo("NEC_MORTE").justificativa
    assert "Na sua ausência, a família" in j
    assert "R$ 2.219.887" in j
    assert "3,0%" in j
    assert "(1 ano)" in j
