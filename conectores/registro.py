"""Registro e execução dos conectores: paralelo, com prazo, falha isolada."""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, TimeoutError as PrazoEsgotado
from dataclasses import dataclass, field
from typing import List, Optional

from motor_dor.comparador import Produto

from .azos import ConectorAzos
from .base import (
    CoberturaSolicitada, Conector, ErroConector, PerfilCotacao, montar_produto,
)
from .mag import ConectorMag

PRAZO_SEGUNDOS = 8.0


def conectores_disponiveis() -> List[Conector]:
    """Só os que têm credenciais no ambiente. Nenhuma credencial = lista vazia."""
    return [c for c in (ConectorAzos(), ConectorMag()) if c.configurado()]


@dataclass
class ResultadoConectores:
    produtos: List[Produto] = field(default_factory=list)
    avisos: List[str] = field(default_factory=list)  # falhas por seguradora


def cotar_em_conectores(
    perfil: PerfilCotacao,
    solicitadas: List[CoberturaSolicitada],
    conectores: Optional[List[Conector]] = None,
    prazo: float = PRAZO_SEGUNDOS,
) -> ResultadoConectores:
    """Consulta todos os conectores em paralelo.

    Uma seguradora fora do ar ou lenta NÃO derruba a comparação: vira aviso e
    as demais seguem.
    """
    ativos = conectores_disponiveis() if conectores is None else conectores
    out = ResultadoConectores()
    if not ativos or not solicitadas:
        return out
    pool = ThreadPoolExecutor(max_workers=len(ativos))
    try:
        futuros = [(c, pool.submit(c.cotar, perfil, solicitadas)) for c in ativos]
        for c, f in futuros:
            try:
                out.produtos.append(montar_produto(f.result(timeout=prazo), perfil))
            except PrazoEsgotado:
                out.avisos.append(f"{c.nome}: sem resposta em {prazo:.0f}s.")
            except ErroConector as e:
                out.avisos.append(f"{c.nome}: {e}")
            except Exception as e:  # resposta inesperada de terceiro
                out.avisos.append(f"{c.nome}: falha inesperada ({type(e).__name__}).")
    finally:
        pool.shutdown(wait=False, cancel_futures=True)
    return out
