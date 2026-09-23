"""Estruturas de entrada e saída do Motor DOR$.

Entrada = respostas do diagnóstico. Saída = necessidade por cobertura,
gaps e Protection Score. Nada aqui calcula: só transporta dados.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional


class SituacaoProfissional(str, Enum):
    MANUAL_ESPECIALIZADO = "MANUAL_ESPECIALIZADO"
    AUTONOMO = "AUTONOMO"
    EMPRESARIO = "EMPRESARIO"
    CLT = "CLT"
    OUTRO = "OUTRO"


class FaseDeVida(str, Enum):
    JOVEM_SEM_DEPENDENTES = "JOVEM_SEM_DEPENDENTES"
    CASAL_SEM_FILHOS = "CASAL_SEM_FILHOS"
    FILHOS_PEQUENOS = "FILHOS_PEQUENOS"
    FILHOS_ADOLESCENTES = "FILHOS_ADOLESCENTES"
    NINHO_VAZIO = "NINHO_VAZIO"


@dataclass(frozen=True)
class Dependente:
    idade: int
    financeiramente_dependente: bool = True


@dataclass(frozen=True)
class Dividas:
    imobiliaria: float = 0.0
    # Dívida imobiliária costuma ter seguro prestamista embutido (MIP). Se
    # houver, ela NÃO entra na necessidade de morte.
    imobiliaria_tem_prestamista: bool = False
    empresarial: float = 0.0
    veiculos: float = 0.0
    outras: float = 0.0

    def total_para_morte(self) -> float:
        imob = 0.0 if self.imobiliaria_tem_prestamista else self.imobiliaria
        return imob + self.empresarial + self.veiculos + self.outras


@dataclass(frozen=True)
class Projetos:
    educacao_filhos: float = 0.0
    quitacao_imovel: float = 0.0
    outros: float = 0.0

    def total(self) -> float:
        return self.educacao_filhos + self.quitacao_imovel + self.outros


@dataclass(frozen=True)
class SeguroAtual:
    """Coberturas já existentes, somadas entre todas as apólices."""

    morte: float = 0.0
    invalidez: float = 0.0
    doenca_grave: float = 0.0
    dit_diaria: float = 0.0


@dataclass(frozen=True)
class Diagnostico:
    """Respostas do cliente. Toda entrada do Motor está aqui."""

    idade: int
    renda_mensal_liquida: float
    custo_familiar_mensal: float
    situacao_profissional: SituacaoProfissional = SituacaoProfissional.OUTRO
    fase_de_vida: Optional[FaseDeVida] = None
    dependentes: List[Dependente] = field(default_factory=list)
    horizonte_protecao_anos: Optional[int] = None
    dividas: Dividas = field(default_factory=Dividas)
    projetos: Projetos = field(default_factory=Projetos)
    patrimonio_liquido: float = 0.0
    patrimonio_inventariavel: float = 0.0
    meses_de_reserva: float = 0.0
    seguro_atual: SeguroAtual = field(default_factory=SeguroAtual)

    def validar(self) -> None:
        if not 0 < self.idade < 120:
            raise ValueError(f"idade fora de faixa plausível: {self.idade}")
        if self.renda_mensal_liquida < 0:
            raise ValueError("renda_mensal_liquida não pode ser negativa")
        if self.custo_familiar_mensal < 0:
            raise ValueError("custo_familiar_mensal não pode ser negativo")
        if self.custo_familiar_mensal > self.renda_mensal_liquida * 3:
            raise ValueError(
                "custo_familiar_mensal mais de 3x a renda: provável erro de "
                "digitação ou de unidade"
            )
        for d in self.dependentes:
            if not 0 <= d.idade < 120:
                raise ValueError(f"idade de dependente inválida: {d.idade}")
        if self.horizonte_protecao_anos is not None and (
            self.horizonte_protecao_anos <= 0
        ):
            raise ValueError("horizonte_protecao_anos deve ser positivo")


@dataclass(frozen=True)
class Necessidade:
    """Uma necessidade calculada, com a memória de cálculo que a gerou."""

    codigo: str
    rotulo: str
    valor_necessario: float
    valor_existente: float
    unidade: str  # CAPITAL | DIARIA
    peso: float
    memoria: Dict[str, float]
    justificativa: str

    @property
    def gap(self) -> float:
        return max(0.0, self.valor_necessario - self.valor_existente)

    @property
    def cobertura(self) -> float:
        """Fração da necessidade já coberta, entre 0 e 1."""
        if self.valor_necessario <= 0:
            return 1.0
        return min(1.0, self.valor_existente / self.valor_necessario)


@dataclass(frozen=True)
class MapaDeProtecao:
    versao_motor: str
    protection_score: int
    necessidades: List[Necessidade]
    vulnerabilidade_principal: Optional[str]
    alertas: List[str] = field(default_factory=list)

    def por_codigo(self, codigo: str) -> Necessidade:
        for n in self.necessidades:
            if n.codigo == codigo:
                return n
        raise KeyError(codigo)

    def to_dict(self) -> dict:
        return {
            "versao_motor": self.versao_motor,
            "protection_score": self.protection_score,
            "vulnerabilidade_principal": self.vulnerabilidade_principal,
            "alertas": list(self.alertas),
            "necessidades": [
                {
                    "codigo": n.codigo,
                    "rotulo": n.rotulo,
                    "unidade": n.unidade,
                    "valor_necessario": round(n.valor_necessario, 2),
                    "valor_existente": round(n.valor_existente, 2),
                    "gap": round(n.gap, 2),
                    "cobertura": round(n.cobertura, 4),
                    "peso": round(n.peso, 4),
                    "memoria": {k: round(v, 2) for k, v in n.memoria.items()},
                    "justificativa": n.justificativa,
                }
                for n in self.necessidades
            ],
        }
