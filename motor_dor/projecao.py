"""Projeção do prêmio mensal daqui a N anos (regra 5 do HANDOFF).

Premissa: capital constante e a MESMA tabela de tarifa de hoje, lida na idade
futura do cliente. Não projeta reajuste de tabela nem correção por índice.
Se o produto não tem tarifa para a idade futura, não há projeção honesta: o
resultado é None e o produto com reajuste por idade não pode ser exibido.
"""

from __future__ import annotations

from typing import Optional

from .comparador import Cotacao, Reajuste

HORIZONTES_ANOS = (10, 20, 30)


def precisa_projecao(cotacao: Cotacao) -> bool:
    """True se alguma cobertura do produto tem prêmio que muda com a idade."""
    return any(
        c.reajuste != Reajuste.PREMIO_NIVELADO
        for c in cotacao.produto.coberturas.values()
    )


def projetar_premio(
    cotacao: Cotacao, idade: int, sexo: str, fumante: bool, anos: int
) -> Optional[float]:
    """Prêmio mensal total aos `idade + anos`. None se não for calculável.

    Cobertura que já terminou (idade acima do limite de cobertura) não gera
    prêmio; a que ainda vigora mas está sem tarifa torna a projeção impossível.
    """
    futura = idade + anos
    total = 0.0
    for item in cotacao.itens:
        if item.codigo_cobertura is None or item.capital_contratado <= 0:
            continue
        cob = cotacao.produto.coberturas[item.codigo_cobertura]
        if cob.idade_limite_cobertura is not None and futura > cob.idade_limite_cobertura:
            continue
        tarifa = cotacao.produto.tarifa(item.codigo_cobertura, futura, sexo, fumante)
        if tarifa is None:
            return None
        if tarifa.premio_por_unidade is not None:
            total += item.capital_contratado * tarifa.premio_por_unidade
        else:
            total += (item.capital_contratado / 1000.0) * (tarifa.taxa_por_mil or 0.0)
    return total
