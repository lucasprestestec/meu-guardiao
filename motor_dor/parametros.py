"""
Parâmetros versionados do Motor DOR$.

REGRA ESTRUTURAL: nenhum número mágico existe fora deste arquivo.

v1.1.0 — premissas definidas pelo especialista. Não são "a fórmula correta"
de capital segurado: não existe consenso de mercado sobre isso. São premissas
assumidas, explicáveis e defensáveis, que o cliente vê e pode ajustar.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Dict

VERSAO_MOTOR = "1.3.1"


class BaseDeCalculo(str, Enum):
    """Sobre o que as contas incidem."""

    RENDA = "RENDA"                  # renda mensal do segurado
    PADRAO_DE_VIDA = "PADRAO_DE_VIDA"  # custo familiar mensal


class MetodoMorte(str, Enum):
    ANOS_DEPENDENCIA = "ANOS_DEPENDENCIA"  # anos até o filho mais novo x 12 x base
    RENDA_PERPETUA = "RENDA_PERPETUA"      # base / taxa mensal
    MAIOR_ENTRE = "MAIOR_ENTRE"            # o maior dos dois


@dataclass(frozen=True)
class Parametros:
    versao: str = VERSAO_MOTOR

    # --- Base de cálculo --------------------------------------------------
    # Decisão do especialista: usar sempre a RENDA, não a despesa. O seguro é
    # o guardião da renda, e a renda em tese é maior que o padrão de vida.
    base_calculo: BaseDeCalculo = BaseDeCalculo.RENDA
    # PENDENTE: o exemplo dado para doenças graves usou padrão de vida.
    # Trocar para PADRAO_DE_VIDA aqui se a DG deve seguir outra base.
    base_calculo_doenca_grave: BaseDeCalculo = BaseDeCalculo.RENDA

    # --- Renda passiva ----------------------------------------------------
    # Rentabilidade mensal ILUSTRATIVA usada para converter capital em renda.
    # 0,8% é a escolha conservadora: gera capital maior que 1% e é mais fácil
    # de defender. NÃO é garantia de rentabilidade.
    taxa_renda_mensal: float = 0.008

    # --- Morte ------------------------------------------------------------
    # v1.2: morte segue a MESMA lógica da invalidez — capital que, rendendo
    # a taxa ilustrativa, repõe a renda mensal do segurado. O método por anos
    # de dependência continua implementado e pode ser reativado aqui.
    metodo_morte: MetodoMorte = MetodoMorte.RENDA_PERPETUA
    # Usado para inferir fase de vida e para exibir o horizonte de
    # dependência ao cliente. NÃO afeta mais o capital de morte.
    idade_independencia_filho: int = 25
    # Custo de inventário no Brasil: 15% como média (ITCMD + honorários +
    # custas). Varia por estado e por complexidade do espólio.
    custo_inventario_pct: float = 0.15
    soma_dividas_na_morte: bool = True
    soma_projetos_na_morte: bool = True

    # --- Doenças graves ---------------------------------------------------
    meses_doenca_grave: int = 24

    # --- Diária (internação / incapacidade temporária) --------------------
    dias_mes: int = 30

    # --- Abatimentos ------------------------------------------------------
    # Seguro já contratado abate, para mostrar o GAP.
    abate_seguro_existente: bool = True
    # Patrimônio NÃO abate. A lógica do produto é preservar patrimônio, não
    # assumir que a família vai consumi-lo.
    abate_patrimonio: bool = False

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

# Variante conservadora alternativa, para comparação lado a lado.
PARAMETROS_1PCT = Parametros(taxa_renda_mensal=0.01)


PERFIS_PROFISSIONAIS: Dict[str, Dict[str, float]] = {
    "MANUAL_ESPECIALIZADO": {
        "NEC_INVALIDEZ": 1.40, "NEC_RENDA": 1.50, "NEC_DOENCA_GRAVE": 1.10,
    },
    "AUTONOMO": {"NEC_RENDA": 1.40, "NEC_INVALIDEZ": 1.20},
    "EMPRESARIO": {"NEC_MORTE": 1.20, "NEC_DOENCA_GRAVE": 1.20},
    "CLT": {"NEC_RENDA": 0.80},
    "OUTRO": {},
}

FASES_DE_VIDA: Dict[str, Dict[str, float]] = {
    "JOVEM_SEM_DEPENDENTES": {
        "NEC_MORTE": 0.30, "NEC_INVALIDEZ": 1.40,
        "NEC_DOENCA_GRAVE": 1.30, "NEC_RENDA": 1.30,
    },
    "CASAL_SEM_FILHOS": {"NEC_MORTE": 0.70, "NEC_INVALIDEZ": 1.20},
    "FILHOS_PEQUENOS": {"NEC_MORTE": 1.50, "NEC_INVALIDEZ": 1.30},
    "FILHOS_ADOLESCENTES": {"NEC_MORTE": 1.20},
    "NINHO_VAZIO": {"NEC_MORTE": 0.80, "NEC_DOENCA_GRAVE": 1.30},
}
