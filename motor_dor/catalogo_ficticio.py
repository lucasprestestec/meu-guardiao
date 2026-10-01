"""
CATÁLOGO FICTÍCIO — NÃO USAR COM CLIENTE.

Todos os números de tarifa aqui são INVENTADOS. Servem só para exercitar o
comparador enquanto os tarifários reais não chegam. A ESTRUTURA é real: é
exatamente o formato em que uma tabela de seguradora será carregada.

Os três produtos foram desenhados para representar arquétipos diferentes do
mercado, de propósito:
  - Vitalícia: cara, completa, capital nivelado, sem reenquadramento etário.
  - Digital: barata, temporária, renovação anual, DG de rol curto.
  - Acidentes: muito barata e parece competitiva no preço, mas só cobre
    acidente. É a armadilha que o comparador precisa expor.
"""

from .comparador import (CoberturaOfertada, Produto, Reajuste, TarifaLinha,
                         Temporalidade, TipoCapital)

_INF = float("inf")


def _faixas(codigo, base, passo, diaria=False, **kw):
    """Gera linhas de tarifa por faixa de 5 anos, encarecendo com a idade."""
    linhas = []
    for i, ini in enumerate(range(18, 76, 5)):
        valor = round(base * (1 + passo) ** i, 6)
        linhas.append(TarifaLinha(
            codigo_cobertura=codigo, idade_min=ini, idade_max=ini + 4,
            premio_por_unidade=valor if diaria else None,
            taxa_por_mil=None if diaria else valor, **kw))
    return linhas


VITALICIA = Produto(
    seguradora="Seguradora Alfa (fictícia)", nome="Vida Integral",
    idade_min=18, idade_max=65,
    coberturas={
        "MORTE_QC": CoberturaOfertada(
            "MORTE_QC", Temporalidade.VITALICIO, Reajuste.PREMIO_NIVELADO,
            TipoCapital.ATUALIZADO_INDICE, 100_000, 20_000_000),
        "IFPD": CoberturaOfertada(
            "IFPD", Temporalidade.ATE_IDADE, Reajuste.PREMIO_NIVELADO,
            idade_limite_cobertura=70, capital_maximo=10_000_000),
        "IPA": CoberturaOfertada(
            "IPA", Temporalidade.ATE_IDADE, Reajuste.PREMIO_NIVELADO,
            idade_limite_cobertura=70, capital_maximo=10_000_000),
        "DG": CoberturaOfertada(
            "DG", Temporalidade.ATE_IDADE, Reajuste.PREMIO_NIVELADO,
            idade_limite_cobertura=75, carencia_dias=90,
            escopo_dg_qtd_doencas=32, escopo_dg_estagio_inicial=True,
            limite_pct_de="MORTE_QC", limite_pct=0.50),
        "DIT": CoberturaOfertada(
            "DIT", Temporalidade.ATE_IDADE, Reajuste.PREMIO_NIVELADO,
            idade_limite_cobertura=65, carencia_dias=60, franquia_dias=15),
    },
    tarifas=(_faixas("MORTE_QC", 0.62, 0.30) + _faixas("IFPD", 0.48, 0.26)
             + _faixas("IPA", 0.07, 0.20)
             + _faixas("DG", 1.05, 0.34) + _faixas("DIT", 3.10, 0.14, diaria=True)),
)

DIGITAL = Produto(
    seguradora="Seguradora Beta (fictícia)", nome="Vida Simples",
    idade_min=18, idade_max=60,
    coberturas={
        "MORTE_QC": CoberturaOfertada(
            "MORTE_QC", Temporalidade.TEMPORARIO, Reajuste.MISTO,
            capital_maximo=3_000_000, renovacao_automatica=False),
        "IPT_LISTA": CoberturaOfertada(
            "IPT_LISTA", Temporalidade.ATE_IDADE, Reajuste.MISTO,
            idade_limite_cobertura=75, carencia_dias=60,
            capital_maximo=3_000_000, renovacao_automatica=False),
        "IPA": CoberturaOfertada(
            "IPA", Temporalidade.ATE_IDADE, Reajuste.MISTO,
            idade_limite_cobertura=75, capital_maximo=3_000_000,
            renovacao_automatica=False),
        "DG": CoberturaOfertada(
            "DG", Temporalidade.ATE_IDADE, Reajuste.MISTO,
            idade_limite_cobertura=75, carencia_dias=60,
            escopo_dg_qtd_doencas=10, escopo_dg_estagio_inicial=True,
            capital_maximo=1_000_000, renovacao_automatica=False),
        "DIT": CoberturaOfertada(
            "DIT", Temporalidade.ATE_IDADE, Reajuste.MISTO,
            idade_limite_cobertura=70, carencia_dias=60, franquia_dias=10,
            renovacao_automatica=False),
    },
    tarifas=(_faixas("MORTE_QC", 0.21, 0.33) + _faixas("IPT_LISTA", 0.17, 0.29)
             + _faixas("IPA", 0.04, 0.27)
             + _faixas("DG", 0.55, 0.36) + _faixas("DIT", 2.40, 0.16, diaria=True)),
)

ACIDENTES = Produto(
    seguradora="Seguradora Gama (fictícia)", nome="Proteção Acidentes",
    idade_min=18, idade_max=70,
    coberturas={
        "MORTE_QC": CoberturaOfertada(
            "MORTE_QC", Temporalidade.TEMPORARIO, Reajuste.FAIXA_ETARIA,
            TipoCapital.DECRESCENTE, capital_maximo=1_000_000,
            renovacao_automatica=True, renovacao_exige_nova_subscricao=True),
        "IPA": CoberturaOfertada(
            "IPA", Temporalidade.TEMPORARIO, Reajuste.FAIXA_ETARIA,
            capital_maximo=1_000_000, renovacao_exige_nova_subscricao=True),
        "DIT_A": CoberturaOfertada(
            "DIT_A", Temporalidade.TEMPORARIO, Reajuste.FAIXA_ETARIA,
            franquia_dias=15, renovacao_exige_nova_subscricao=True),
    },
    tarifas=(_faixas("MORTE_QC", 0.14, 0.31) + _faixas("IPA", 0.05, 0.12)
             + _faixas("DIT_A", 1.30, 0.13, diaria=True)),
)

CATALOGO = [VITALICIA, DIGITAL, ACIDENTES]
