"""Conector Icatu: API Vida - Parceiro - Pré-Venda v3 (portal-api.icatuseguros.com.br).

Fatos (documentação pública lida em 2026-10-11): POST /cotacoes recebe produto,
proponente (nascimento, sexo, fumante) e a lista de coberturas por NÚMERO com o
capital; devolve prêmio total, id da cotação e o prêmio de cada cobertura. Headers:
`Ocp-Apim-Subscription-Key` e `CodigoEmpresa` (4 dígitos). A cotação é simulação.

NÃO validado (precisa de chave real/sandbox):
- o prêmio devolvido é tratado como MENSAL (a doc não diz a periodicidade);
- os exemplos da doc e o esquema divergem no formato de `coberturas`; o parser
  aceita os dois;
- os números de cobertura de cada produto saem de GET /produtos/{id} (ver
  `detalhes_produto`). O mapa interno -> número fica em ICATU_MAPA_COBERTURAS:
  nada é presumido sobre temporalidade/reajuste, por isso são obrigatórios.

Ambiente: ICATU_SUBSCRIPTION_KEY, ICATU_CODIGO_EMPRESA, ICATU_CODIGO_PRODUTO
(ex.: "67612_0_2"), ICATU_MAPA_COBERTURAS (JSON), opcionais ICATU_PROFISSAO (int)
e ICATU_BASE_URL (sandbox/mock).
"""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from datetime import date
from typing import Any, Dict, List

from motor_dor.comparador import CoberturaOfertada, Reajuste, Temporalidade

from .base import (
    CoberturaCotada, CoberturaSolicitada, Conector, ErroConector, PerfilCotacao,
    RespostaCotacao,
)

BASE_PADRAO = "https://api.icatuseguros.com.br/relacionamento-parceiro/vida/pre-venda/v3"
TIMEOUT = 6.0  # menor que o prazo do registro (8s)


def _preco_inclui_iof() -> bool:
    """A documentação da Icatu não diz se o prêmio inclui IOF: o valor vem da configuração,
    confirmado com a Icatu. Ausente = erro (chutar cobra em dobro ou deixa de cobrar)."""
    v = os.environ.get("ICATU_PRECO_INCLUI_IOF", "").strip().lower()
    if v not in ("sim", "nao"):
        raise ErroConector("icatu: defina ICATU_PRECO_INCLUI_IOF=sim ou nao (confirmar com a Icatu)")
    return v == "sim"


def _nascimento(idade: int) -> str:
    hoje = date.today()
    try:
        return hoje.replace(year=hoje.year - idade).isoformat()
    except ValueError:  # 29/02
        return hoje.replace(year=hoje.year - idade, day=28).isoformat()


class ConectorIcatu(Conector):
    nome = "icatu"

    def __init__(self, abrir=urllib.request.urlopen):
        self._abrir = abrir  # injetável nos testes

    def configurado(self) -> bool:
        e = os.environ
        return all(e.get(v) for v in (
            "ICATU_SUBSCRIPTION_KEY", "ICATU_CODIGO_EMPRESA", "ICATU_CODIGO_PRODUTO"))

    def _chamar(self, metodo: str, caminho: str, corpo: Any = None) -> Dict[str, Any]:
        base = os.environ.get("ICATU_BASE_URL", BASE_PADRAO).rstrip("/")
        req = urllib.request.Request(
            base + caminho, method=metodo,
            data=None if corpo is None else json.dumps(corpo).encode(),
            headers={
                "Content-Type": "application/json",
                "Ocp-Apim-Subscription-Key": os.environ["ICATU_SUBSCRIPTION_KEY"],
                "CodigoEmpresa": os.environ["ICATU_CODIGO_EMPRESA"].zfill(4),
            })
        try:
            with self._abrir(req, timeout=TIMEOUT) as r:
                return json.loads(r.read().decode())
        except urllib.error.HTTPError as e:
            raise ErroConector(f"icatu: HTTP {e.code}") from e
        except (urllib.error.URLError, TimeoutError, ValueError) as e:
            raise ErroConector(f"icatu: {type(e).__name__}") from e

    def detalhes_produto(self, id_produto: int) -> Dict[str, Any]:
        """Coberturas, limites e idades do produto: base para preencher o mapa."""
        return self._chamar("GET", f"/produtos/{id_produto}")

    @staticmethod
    def _mapa() -> Dict[str, Dict[str, Any]]:
        try:
            mapa = json.loads(os.environ.get("ICATU_MAPA_COBERTURAS", ""))
        except ValueError:
            raise ErroConector("icatu: ICATU_MAPA_COBERTURAS ausente ou inválido") from None
        for cod, m in mapa.items():
            if not {"numero", "temporalidade", "reajuste"} <= set(m):
                raise ErroConector(f"icatu: mapa de {cod} sem numero/temporalidade/reajuste")
        return mapa

    def cotar(self, perfil: PerfilCotacao, solicitadas: List[CoberturaSolicitada]) -> RespostaCotacao:
        mapa = self._mapa()
        avisos: List[str] = []
        pedido: Dict[int, CoberturaSolicitada] = {}
        for s in solicitadas:
            if s.codigo in mapa:
                pedido[int(mapa[s.codigo]["numero"])] = s
            else:
                avisos.append(f"icatu: sem {s.codigo} no mapa de coberturas")
        if not pedido:
            raise ErroConector("icatu: nenhuma cobertura pedida existe no mapa")

        pf: Dict[str, Any] = {
            "dataNascimento": _nascimento(perfil.idade),
            "sexo": "masculino" if perfil.sexo == "M" else "feminino",
            "aposentado": "nao",
            "saudeEntrada": {"fumante": perfil.fumante},
        }
        if os.environ.get("ICATU_PROFISSAO"):
            pf["profissao"] = int(os.environ["ICATU_PROFISSAO"])
        dados = self._chamar("POST", "/cotacoes", {
            "codigoProduto": os.environ["ICATU_CODIGO_PRODUTO"],
            "proponente": {"pessoaFisica": pf},
            "coberturas": [{"numero": n, "valorCapital": s.capital} for n, s in pedido.items()],
        })

        cotadas: List[CoberturaCotada] = []
        for c in dados.get("coberturas") or []:
            aninhada = c.get("cobertura") or {}
            numero = c.get("numero", aninhada.get("numero"))
            premio = c.get("valorPremio", c.get("premio"))
            if numero not in pedido or premio is None:
                continue
            s = pedido[numero]
            m = mapa[s.codigo]
            capital = c.get("valorCapital") or aninhada.get("valorCapital") or s.capital
            try:
                oferta = CoberturaOfertada(
                    s.codigo, Temporalidade(m["temporalidade"]), Reajuste(m["reajuste"]))
            except ValueError as e:
                raise ErroConector(f"icatu: mapa de {s.codigo} inválido ({e})") from None
            cotadas.append(CoberturaCotada(s.codigo, float(capital), float(premio), oferta))
        if not cotadas:
            raise ErroConector("icatu: resposta sem coberturas cotadas")
        return RespostaCotacao(
            "Icatu", "Icatu Vida", cotadas,
            referencia_externa=dados.get("idCotacao"), avisos=avisos,
            preco_inclui_iof=_preco_inclui_iof())
