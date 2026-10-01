"""Conexão com o banco e flags de ambiente, compartilhados pelos routers."""

import os
from contextlib import contextmanager

import psycopg

from .preparo import preparar_se_demonstracao

URL_PADRAO = "postgresql://guardiao:guardiao_dev@localhost:54329/guardiao"


@contextmanager
def conexao():
    url = os.environ.get("DATABASE_URL", URL_PADRAO)
    preparar_se_demonstracao(url)  # 1x por processo; só no modo demonstração (api/preparo.py)
    with psycopg.connect(url) as conn:
        yield conn  # commit ao sair sem erro, rollback com erro


def permitir_ficticios() -> bool:
    return os.environ.get("PERMITIR_TARIFA_FICTICIA") == "1"
