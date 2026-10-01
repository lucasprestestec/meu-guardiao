"""Contrato comum dos conectores de seguradora (API de cotação).

O comparador trabalha com `Produto` + tarifário. As APIs das seguradoras não
expõem tarifário: devolvem o preço de UM perfil. O conector faz a ponte:
pergunta o preço à API e entrega um `Produto` de um perfil só, com a tarifa
derivada do preço devolvido. O motor de aderência não muda.

Preço vindo de API é preço REAL: `fonte_tarifa` = "API:<seguradora>", nunca
"FICTICIA".
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field, replace
from typing import Dict, List, Optional

from motor_dor.comparador import CoberturaOfertada, Produto, TarifaLinha

# Coberturas cujo capital é diária (R$/dia) e não capital segurado (R$).
COBERTURAS_DIARIA = frozenset({"DIT", "DIT_A", "DIH", "DIH_UTI"})


class ErroConector(Exception):
    """Falha ao consultar a seguradora (rede, contrato, resposta inválida)."""


class ConectorNaoConfigurado(ErroConector):
    """Sem credenciais: o conector fica desligado, não é erro de produção."""


@dataclass(frozen=True)
class PerfilCotacao:
    idade: int
    sexo: str            # "M" | "F"
    fumante: bool
    profissao: Optional[str] = None  # a Azos pede profissão na cotação


@dataclass(frozen=True)
class CoberturaSolicitada:
    codigo: str          # código INTERNO (MORTE_QC, IFPD, DG, DIT...)
    capital: float


@dataclass(frozen=True)
class CoberturaCotada:
    codigo: str          # código INTERNO, já traduzido
    capital: float       # capital que a seguradora aceitou (pode ser < pedido)
    premio_mensal: float
    oferta: CoberturaOfertada  # atributos estruturais (temporalidade, carência...)


@dataclass(frozen=True)
class RespostaCotacao:
    seguradora: str
    produto: str
    coberturas: List[CoberturaCotada]
    referencia_externa: Optional[str] = None  # id/link da simulação, se houver
    avisos: List[str] = field(default_factory=list)


class Conector(ABC):
    nome: str  # "azos", "mag"...

    @abstractmethod
    def configurado(self) -> bool:
        """True se há credenciais no ambiente. Falso = conector desligado."""

    @abstractmethod
    def cotar(
        self, perfil: PerfilCotacao, solicitadas: List[CoberturaSolicitada]
    ) -> RespostaCotacao:
        """Consulta a API. Levanta ErroConector em qualquer falha."""


def montar_produto(resp: RespostaCotacao, perfil: PerfilCotacao) -> Produto:
    """Converte a resposta da API num Produto válido só para este perfil.

    A taxa é derivada do preço no capital confirmado pela seguradora, e o
    capital máximo fica travado nele: o comparador nunca extrapola preço
    para um capital que a API não cotou.
    """
    coberturas: Dict[str, CoberturaOfertada] = {}
    tarifas: List[TarifaLinha] = []
    for c in resp.coberturas:
        if c.capital <= 0 or c.premio_mensal < 0:
            raise ErroConector(f"{resp.seguradora}: cobertura {c.codigo} com valores inválidos")
        coberturas[c.codigo] = replace(c.oferta, capital_minimo=0.0, capital_maximo=c.capital)
        if c.codigo in COBERTURAS_DIARIA:
            tarifas.append(TarifaLinha(
                c.codigo, perfil.idade, perfil.idade, premio_por_unidade=c.premio_mensal / c.capital))
        else:
            tarifas.append(TarifaLinha(
                c.codigo, perfil.idade, perfil.idade, taxa_por_mil=c.premio_mensal / c.capital * 1000.0))
    return Produto(
        seguradora=resp.seguradora, nome=resp.produto, coberturas=coberturas, tarifas=tarifas,
        idade_min=perfil.idade, idade_max=perfil.idade, fonte_tarifa=f"API:{resp.seguradora}",
    )
