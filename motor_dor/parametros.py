"""
Parâmetros versionados do Motor DOR$.

REGRA ESTRUTURAL: nenhum número mágico existe fora deste arquivo.
Toda constante de cálculo vive aqui, com versão. Uma apólice vendida sob a
versão 1.0.0 precisa ser recalculável com a versão 1.0.0 daqui a dez anos.

Os valores abaixo são um PONTO DE PARTIDA plausível, não calibração final.
Cada um está marcado com [CALIBRAR] quando depende da metodologia do
especialista e ainda não foi validado contra casos reais.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict

VERSAO_MOTOR = "1.0.0"


@dataclass(frozen=True)
class Parametros:
    """Conjunto imutável de parâmetros de cálculo."""

    versao: str = VERSAO_MOTOR

    # --- Financeiro -------------------------------------------------------
    # Taxa real (acima da inflação) usada para trazer a valor presente a renda
    # futura que a família precisaria. [CALIBRAR]
    taxa_real_desconto_aa: float = 0.03

    # --- Horizontes -------------------------------------------------------
    idade_aposentadoria: int = 65
    idade_independencia_filho: int = 24
    horizonte_maximo_anos: int = 40
    horizonte_minimo_anos: int = 5

    # --- Morte ------------------------------------------------------------
    # Parcela do custo familiar mensal consumida pelo próprio segurado, que
    # deixa de existir na sua ausência. [CALIBRAR]
    share_consumo_do_segurado: float = 0.25
    # Custo de inventário/ITCMD sobre o patrimônio inventariável. Varia por
    # estado (ITCMD de 2% a 8%) mais custas e honorários. [CALIBRAR]
    custo_inventario_pct: float = 0.12
    # Fração do patrimônio declarado que é efetivamente líquida e utilizável
    # pela família no curto prazo. [CALIBRAR]
    liquidez_patrimonio_pct: float = 0.70

    # --- Invalidez --------------------------------------------------------
    # Na invalidez o segurado continua consumindo E gera custo adicional
    # (adaptação, cuidador, tratamento continuado). Acréscimo sobre o custo
    # familiar mensal. [CALIBRAR]
    acrescimo_custo_invalidez: float = 0.25
    # Custo de adaptação inicial (imóvel, veículo, equipamentos). [CALIBRAR]
    custo_adaptacao_invalidez: float = 120_000.00

    # --- Doença grave -----------------------------------------------------
    # Capital de travessia: meses de custo familiar durante o tratamento.
    meses_travessia_doenca_grave: int = 24
    # Reserva para o que o plano de saúde não cobre: medicação de alto custo,
    # segunda opinião, deslocamento, tratamento fora do rol. [CALIBRAR]
    reserva_tratamento_nao_coberto: float = 200_000.00
    # Queda de renda esperada durante o tratamento. [CALIBRAR]
    queda_renda_tratamento: float = 0.50

    # --- Renda / DIT ------------------------------------------------------
    # Teto da diária como fração da renda líquida diária. Acima disso a
    # seguradora normalmente recusa (risco moral).
    dit_teto_pct_renda: float = 1.00
    dit_dias_mes: int = 30
    # Meses de reserva a partir dos quais a DIT deixa de ser crítica.
    dit_meses_reserva_confortavel: int = 6

    # --- Score ------------------------------------------------------------
    peso_base: Dict[str, float] = field(
        default_factory=lambda: {
            "NEC_MORTE": 1.00,
            "NEC_INVALIDEZ": 1.00,
            "NEC_DOENCA_GRAVE": 0.70,
            "NEC_RENDA": 0.70,
        }
    )


PARAMETROS_V1 = Parametros()


# ---------------------------------------------------------------------------
# Perfis de risco profissional
# ---------------------------------------------------------------------------
# Não alteram o CAPITAL necessário: alteram o PESO de cada necessidade no
# Protection Score e na priorização. Um dentista que perde a função de pinça
# perde a renda sem morrer; um recém-pai tem exposição concentrada em morte.
#
# Multiplicadores aplicados sobre peso_base. [CALIBRAR com o especialista]

PERFIS_PROFISSIONAIS: Dict[str, Dict[str, float]] = {
    # Dependem de destreza fina / integridade física para gerar renda
    "MANUAL_ESPECIALIZADO": {  # dentista, cirurgião, músico, joalheiro
        "NEC_INVALIDEZ": 1.40,
        "NEC_RENDA": 1.50,
        "NEC_DOENCA_GRAVE": 1.10,
    },
    # Renda depende de presença física e não há afastamento remunerado
    "AUTONOMO": {
        "NEC_RENDA": 1.40,
        "NEC_INVALIDEZ": 1.20,
    },
    # Sócio de empresa: exposição a dívida empresarial e sucessão
    "EMPRESARIO": {
        "NEC_MORTE": 1.20,
        "NEC_DOENCA_GRAVE": 1.20,
    },
    "CLT": {
        "NEC_RENDA": 0.80,  # há afastamento pelo INSS/empresa
    },
    "OUTRO": {},
}

FASES_DE_VIDA: Dict[str, Dict[str, float]] = {
    "JOVEM_SEM_DEPENDENTES": {
        "NEC_MORTE": 0.30,
        "NEC_INVALIDEZ": 1.40,
        "NEC_DOENCA_GRAVE": 1.30,
        "NEC_RENDA": 1.30,
    },
    "CASAL_SEM_FILHOS": {
        "NEC_MORTE": 0.70,
        "NEC_INVALIDEZ": 1.20,
    },
    "FILHOS_PEQUENOS": {
        "NEC_MORTE": 1.50,
        "NEC_INVALIDEZ": 1.30,
    },
    "FILHOS_ADOLESCENTES": {
        "NEC_MORTE": 1.20,
    },
    "NINHO_VAZIO": {
        "NEC_MORTE": 0.80,
        "NEC_DOENCA_GRAVE": 1.30,
    },
}
