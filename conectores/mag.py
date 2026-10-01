"""Conector MAG: AGUARDANDO CADASTRO NO SANDBOX E CONTRATO.

Fatos (developers.mag.com.br, Guia Prático MAG Seguros): API Seguradora com
GET /modeloproposta (ofertas que o CNPJ pode vender), GET /modeloproposta/{id},
POST /simulacao (preço de um perfil) e POST /proposta. O Swagger e o formato
das respostas ficam atrás de cadastro no portal e não foram lidos. Autenticação:
ver "Autenticando sua Requisição" no portal. Implementar `cotar` com
POST /simulacao depois de ler o contrato no sandbox.
"""

from __future__ import annotations

import os
from typing import List

from .base import (
    CoberturaSolicitada, Conector, ErroConector, PerfilCotacao, RespostaCotacao,
)


class ConectorMag(Conector):
    nome = "mag"

    def configurado(self) -> bool:
        return bool(os.environ.get("MAG_CLIENT_ID") and os.environ.get("MAG_CLIENT_SECRET"))

    def cotar(self, perfil: PerfilCotacao, solicitadas: List[CoberturaSolicitada]) -> RespostaCotacao:
        raise ErroConector("contrato da API MAG ainda não implementado (falta ler o sandbox)")
