"""Conector Azos: AGUARDANDO CREDENCIAL E CONTRATO.

Fatos (PDF "Integração via API", Azos 2026): API só de consulta; a cotação tem
3 consultas (profissões; coberturas por perfil; cálculo de prêmio); acesso por
API key, pedida em formulário, até 5 dias úteis; docs em developer.azos.com.br
(partner-api-v2). O PDF NÃO traz URL base, autenticação exata nem formato das
respostas, por isso `cotar` ainda não chama nada. Implementar aqui depois de
ler o contrato real, preenchendo o mapeamento código Azos -> código interno.

A cotação Azos é simulação: não vira proposta. A contratação é no portal Azos.
"""

from __future__ import annotations

import os
from typing import List

from .base import (
    CoberturaSolicitada, Conector, ErroConector, PerfilCotacao, RespostaCotacao,
)


class ConectorAzos(Conector):
    nome = "azos"

    def configurado(self) -> bool:
        return bool(os.environ.get("AZOS_API_KEY"))

    def cotar(self, perfil: PerfilCotacao, solicitadas: List[CoberturaSolicitada]) -> RespostaCotacao:
        raise ErroConector("contrato da API Azos ainda não implementado (falta ler developer.azos.com.br)")
