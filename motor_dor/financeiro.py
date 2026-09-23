"""Funções financeiras puras. Sem estado, sem I/O, sem dependência externa.

Cada função aqui é testável isoladamente e determinística.
"""

from __future__ import annotations


def valor_presente_anuidade(
    pagamento_anual: float, anos: float, taxa_real_aa: float
) -> float:
    """Valor presente de uma série de pagamentos anuais constantes.

    Usa taxa REAL (acima da inflação), então o pagamento é expresso em poder
    de compra de hoje e não precisa ser corrigido ano a ano.

        PV = A * (1 - (1 + r)^-n) / r

    Com r = 0, degenera para A * n (caso-limite tratado explicitamente).
    """
    if pagamento_anual <= 0 or anos <= 0:
        return 0.0
    if abs(taxa_real_aa) < 1e-12:
        return pagamento_anual * anos
    if taxa_real_aa <= -1.0:
        raise ValueError("taxa real <= -100% não tem significado financeiro")
    fator = (1.0 - (1.0 + taxa_real_aa) ** (-anos)) / taxa_real_aa
    return pagamento_anual * fator


def anos_ate_idade(idade_atual: int, idade_alvo: int) -> float:
    """Anos restantes até uma idade-alvo. Nunca negativo."""
    return max(0.0, float(idade_alvo - idade_atual))


def clamp(valor: float, minimo: float, maximo: float) -> float:
    return max(minimo, min(maximo, valor))
