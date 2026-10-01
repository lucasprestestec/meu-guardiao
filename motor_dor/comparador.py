"""
Comparador — liga o Motor DOR$ ao catálogo de produtos.

Recebe um MapaDeProtecao (o que o cliente precisa) e um catálogo de produtos
(o que o mercado oferece) e devolve opções ranqueadas por ADERÊNCIA e PREÇO.

REGRA ESTRUTURAL: um produto que não cobre uma necessidade não é "mais
barato" — é incompleto. A aderência existe justamente para impedir que o
comparador compare banana com maçã.

A estrutura de tarifa aqui é REAL. Os NÚMEROS de `catalogo_ficticio.py` são
inventados e estão marcados como tal. Quando chegar o primeiro tarifário de
seguradora, troca-se o catálogo e nada mais.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional

from .modelos import MapaDeProtecao, Necessidade

# ---------------------------------------------------------------------------
# Ligação entre necessidade (Motor) e cobertura (Schema)
# ---------------------------------------------------------------------------

# Cada necessidade pode ser atendida por coberturas de qualidade diferente.
# O peso indica o quanto aquela cobertura atende de fato a necessidade.
# Ex.: uma invalidez só por acidente (IPA) atende parcialmente a necessidade
# de invalidez, porque a maior parte das invalidezes vem de doença.
COBERTURAS_QUE_ATENDEM: Dict[str, Dict[str, float]] = {
    "NEC_MORTE": {"MORTE_QC": 1.00, "MORTE_ACID": 0.20},
    "NEC_INVALIDEZ": {
        "IFPD": 1.00,      # invalidez funcional por doença — o padrão-ouro
        "ILP": 1.00,       # invalidez laborativa por doença
        "IPT_LISTA": 0.65, # lista fechada de perdas: cobre bem menos situações
        "IPA": 0.35,       # só acidente
        "IPTA": 0.30,      # só acidente e só total
    },
    "NEC_DOENCA_GRAVE": {"DG": 1.00, "DG_ONCO": 0.45, "DG_CARDIO": 0.35},
    "NEC_RENDA": {"DIT": 1.00, "DIT_A": 0.40, "DIH": 0.55, "DIH_UTI": 0.25},
}


class TipoCapital(str, Enum):
    NIVELADO = "NIVELADO"
    DECRESCENTE = "DECRESCENTE"
    ATUALIZADO_INDICE = "ATUALIZADO_INDICE"


class Reajuste(str, Enum):
    PREMIO_NIVELADO = "PREMIO_NIVELADO"
    FAIXA_ETARIA = "FAIXA_ETARIA"
    ANUAL_INDICE = "ANUAL_INDICE"
    MISTO = "MISTO"


class Temporalidade(str, Enum):
    VITALICIO = "VITALICIO"
    TEMPORARIO = "TEMPORARIO"
    ATE_IDADE = "ATE_IDADE"


@dataclass(frozen=True)
class TarifaLinha:
    """Uma linha do tarifário. Chave: cobertura + faixa etária + sexo + fumo."""

    codigo_cobertura: str
    idade_min: int
    idade_max: int
    taxa_por_mil: Optional[float] = None       # capital: prêmio mensal por mil
    premio_por_unidade: Optional[float] = None  # diária: prêmio mensal por R$1/dia
    sexo: Optional[str] = None                  # None = unissex
    fumante: Optional[bool] = None              # None = indiferente

    def casa(self, idade: int, sexo: str, fumante: bool) -> bool:
        return (
            self.idade_min <= idade <= self.idade_max
            and (self.sexo is None or self.sexo == sexo)
            and (self.fumante is None or self.fumante == fumante)
        )


@dataclass(frozen=True)
class CoberturaOfertada:
    """Uma cobertura dentro de um produto, com seus atributos normalizados."""

    codigo: str
    temporalidade: Temporalidade
    reajuste: Reajuste
    tipo_capital: TipoCapital = TipoCapital.ATUALIZADO_INDICE
    capital_minimo: float = 0.0
    capital_maximo: float = float("inf")
    idade_limite_cobertura: Optional[int] = None
    carencia_dias: int = 0
    franquia_dias: Optional[int] = None
    renovacao_automatica: bool = True
    renovacao_exige_nova_subscricao: bool = False
    # Só para DG: quantidade de doenças do rol e se cobre estágio inicial.
    escopo_dg_qtd_doencas: Optional[int] = None
    escopo_dg_estagio_inicial: bool = False
    # Teto como percentual de outra cobertura (ex.: DG limitada a 50% da morte)
    limite_pct_de: Optional[str] = None
    limite_pct: Optional[float] = None


@dataclass(frozen=True)
class Produto:
    seguradora: str
    nome: str
    coberturas: Dict[str, CoberturaOfertada]
    tarifas: List[TarifaLinha]
    idade_min: int = 18
    idade_max: int = 65
    fonte_tarifa: str = "FICTICIA"  # nunca publicar com FICTICIA

    def tarifa(
        self, codigo: str, idade: int, sexo: str, fumante: bool
    ) -> Optional[TarifaLinha]:
        for t in self.tarifas:
            if t.codigo_cobertura == codigo and t.casa(idade, sexo, fumante):
                return t
        return None


# ---------------------------------------------------------------------------
# Parâmetros de aderência
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ParametrosComparador:
    versao: str = "1.2.0"
    # CHAVE de decisão comercial (v1.2.0): invalidez só por acidente. As coberturas
    # abaixo continuam cadastradas no schema e no catálogo, mas o comparador as
    # ignora. Para reativá-las, esvazie este conjunto — não é preciso refazer nada.
    coberturas_inativas: frozenset = frozenset({"IFPD", "ILP", "IPT_LISTA"})
    # Penalidades estruturais multiplicativas.
    pen_temporario: float = 0.90
    pen_renovacao_nao_automatica: float = 0.90
    pen_renovacao_com_nova_subscricao: float = 0.70  # o risco real do temporário
    pen_capital_decrescente: float = 0.80
    pen_reajuste_etario: float = 0.92
    pen_carencia_longa: float = 0.95
    carencia_longa_dias: int = 180
    # DG: rol pequeno cobre menos situações.
    dg_doencas_referencia: int = 30
    dg_bonus_estagio_inicial: float = 1.05


PARAMETROS_COMPARADOR = ParametrosComparador()


# ---------------------------------------------------------------------------
# Cálculo
# ---------------------------------------------------------------------------


@dataclass
class ItemCotado:
    necessidade: str
    codigo_cobertura: Optional[str]
    capital_contratado: float
    capital_necessario: float
    premio_mensal: float
    qualidade_cobertura: float   # o quanto aquela cobertura atende a necessidade
    qualidade_estrutural: float  # temporalidade, renovação, reajuste, carência
    aderencia: float
    observacoes: List[str] = field(default_factory=list)


@dataclass
class Cotacao:
    produto: Produto
    itens: List[ItemCotado]
    premio_mensal_total: float
    aderencia_total: float
    alertas: List[str] = field(default_factory=list)

    @property
    def coberturas_ausentes(self) -> List[str]:
        return [i.necessidade for i in self.itens if i.codigo_cobertura is None]


def _qualidade_estrutural(
    c: CoberturaOfertada, p: ParametrosComparador
) -> tuple[float, List[str]]:
    q = 1.0
    obs: List[str] = []

    if c.temporalidade != Temporalidade.VITALICIO:
        q *= p.pen_temporario
        obs.append("Cobertura temporária, não vitalícia.")
    if not c.renovacao_automatica:
        q *= p.pen_renovacao_nao_automatica
        obs.append("Renovação não é automática: exige manifestação das partes.")
    if c.renovacao_exige_nova_subscricao:
        q *= p.pen_renovacao_com_nova_subscricao
        obs.append(
            "Renovação exige nova avaliação de saúde — se você adoecer, pode "
            "não conseguir renovar."
        )
    if c.tipo_capital == TipoCapital.DECRESCENTE:
        q *= p.pen_capital_decrescente
        obs.append("Capital decrescente: a proteção diminui com o tempo.")
    if c.reajuste in (Reajuste.FAIXA_ETARIA, Reajuste.MISTO):
        q *= p.pen_reajuste_etario
        obs.append("Prêmio sobe por faixa etária ao longo da vida.")
    if c.carencia_dias >= p.carencia_longa_dias:
        q *= p.pen_carencia_longa
        obs.append(f"Carência de {c.carencia_dias} dias.")

    if c.escopo_dg_qtd_doencas is not None:
        razao = min(1.0, c.escopo_dg_qtd_doencas / p.dg_doencas_referencia)
        q *= razao
        obs.append(f"Rol de {c.escopo_dg_qtd_doencas} doenças.")
        if c.escopo_dg_estagio_inicial:
            q *= p.dg_bonus_estagio_inicial
            obs.append("Paga estágio inicial de câncer.")

    return q, obs


def _melhor_cobertura(
    produto: Produto, necessidade: str, p: ParametrosComparador = PARAMETROS_COMPARADOR
) -> Optional[tuple[str, float]]:
    """Entre as coberturas ATIVAS do produto, a que melhor atende esta necessidade."""
    candidatas = COBERTURAS_QUE_ATENDEM.get(necessidade, {})
    melhor = None
    for codigo, qualidade in candidatas.items():
        if codigo in p.coberturas_inativas:
            continue
        if codigo in produto.coberturas:
            if melhor is None or qualidade > melhor[1]:
                melhor = (codigo, qualidade)
    return melhor


def cotar(
    produto: Produto,
    mapa: MapaDeProtecao,
    idade: int,
    sexo: str,
    fumante: bool,
    p: ParametrosComparador = PARAMETROS_COMPARADOR,
    capitais_escolhidos: Optional[Dict[str, float]] = None,
) -> Cotacao:
    """Cota um produto contra o mapa de proteção do cliente.

    `capitais_escolhidos` (código de necessidade -> valor) é o que o cliente
    ajustou nos sliders. Sem ele, cota-se o gap calculado pelo Motor. A
    aderência sempre mede contra a NECESSIDADE (gap), não contra o escolhido:
    escolher menos do que precisa reduz a aderência.
    """
    itens: List[ItemCotado] = []
    alertas: List[str] = []

    if not produto.idade_min <= idade <= produto.idade_max:
        alertas.append(
            f"Idade fora da faixa de aceitação do produto "
            f"({produto.idade_min}–{produto.idade_max} anos)."
        )

    capitais: Dict[str, float] = {}

    for nec in mapa.necessidades:
        escolha = _melhor_cobertura(produto, nec.codigo, p)
        if escolha is None:
            itens.append(
                ItemCotado(
                    necessidade=nec.codigo, codigo_cobertura=None,
                    capital_contratado=0.0, capital_necessario=nec.gap,
                    premio_mensal=0.0, qualidade_cobertura=0.0,
                    qualidade_estrutural=0.0, aderencia=0.0,
                    observacoes=["Este produto não oferece esta cobertura."],
                )
            )
            continue

        codigo, qualidade_cob = escolha
        cob = produto.coberturas[codigo]

        desejado = nec.gap
        solicitado = (
            capitais_escolhidos.get(nec.codigo, desejado)
            if capitais_escolhidos is not None else desejado
        )
        teto = cob.capital_maximo
        if cob.limite_pct_de and cob.limite_pct:
            base = capitais.get(cob.limite_pct_de)
            if base is not None:
                teto = min(teto, base * cob.limite_pct)
        contratado = max(0.0, min(solicitado, teto))
        if contratado and contratado < cob.capital_minimo:
            contratado = cob.capital_minimo
        capitais[codigo] = contratado

        tarifa = produto.tarifa(codigo, idade, sexo, fumante)
        if tarifa is None:
            premio = 0.0
            obs_tarifa = ["Sem tarifa para esta idade/perfil."]
            contratado = 0.0
        elif nec.unidade == "DIARIA":
            premio = contratado * (tarifa.premio_por_unidade or 0.0)
            obs_tarifa = []
        else:
            premio = (contratado / 1000.0) * (tarifa.taxa_por_mil or 0.0)
            obs_tarifa = []

        q_est, obs_est = _qualidade_estrutural(cob, p)
        cobertura_capital = (contratado / desejado) if desejado > 0 else 1.0
        aderencia = min(1.0, cobertura_capital) * qualidade_cob * q_est

        obs = obs_tarifa + obs_est
        if solicitado > 0 and contratado < solicitado:
            alvo = "necessidade" if capitais_escolhidos is None else "valor escolhido"
            obs.insert(
                0,
                f"Capital limitado a R$ {contratado:,.0f} — abaixo da "
                f"{alvo} de R$ {solicitado:,.0f}.".replace(",", "."),
            )
        if qualidade_cob < 1.0:
            obs.insert(0, f"Atende parcialmente: a cobertura oferecida é {codigo}.")

        itens.append(
            ItemCotado(
                necessidade=nec.codigo, codigo_cobertura=codigo,
                capital_contratado=contratado, capital_necessario=desejado,
                premio_mensal=premio, qualidade_cobertura=qualidade_cob,
                qualidade_estrutural=q_est, aderencia=aderencia, observacoes=obs,
            )
        )

    pesos = {n.codigo: n.peso for n in mapa.necessidades}
    soma = sum(pesos.values())
    aderencia_total = (
        sum(i.aderencia * pesos.get(i.necessidade, 0.0) for i in itens) / soma
        if soma > 0 else 0.0
    )

    if produto.fonte_tarifa == "FICTICIA":
        alertas.append(
            "TARIFA FICTÍCIA — este produto não pode ser exibido ao consumidor."
        )

    return Cotacao(
        produto=produto, itens=itens,
        premio_mensal_total=sum(i.premio_mensal for i in itens),
        aderencia_total=aderencia_total, alertas=alertas,
    )


def comparar(
    produtos: List[Produto], mapa: MapaDeProtecao, idade: int, sexo: str,
    fumante: bool, p: ParametrosComparador = PARAMETROS_COMPARADOR,
    capitais_escolhidos: Optional[Dict[str, float]] = None,
) -> List[Cotacao]:
    """Cota todos os produtos e ordena por aderência; empate desempata no preço."""
    cotacoes = [
        cotar(pr, mapa, idade, sexo, fumante, p, capitais_escolhidos)
        for pr in produtos
    ]
    return sorted(
        cotacoes, key=lambda c: (-round(c.aderencia_total, 4), c.premio_mensal_total)
    )


def recomendados(cotacoes: List[Cotacao]) -> Dict[str, Optional[Cotacao]]:
    """Os três destaques da tela de comparação."""
    if not cotacoes:
        return {"recomendado": None, "menor_preco": None, "maior_protecao": None}
    completas = [c for c in cotacoes if not c.coberturas_ausentes] or cotacoes
    return {
        "recomendado": completas[0],
        "menor_preco": min(cotacoes, key=lambda c: c.premio_mensal_total),
        "maior_protecao": max(cotacoes, key=lambda c: c.aderencia_total),
    }
