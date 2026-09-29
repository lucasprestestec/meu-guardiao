"""Conexão com o banco e flags de ambiente, compartilhados pelos routers."""

import os
from contextlib import contextmanager

import psycopg

URL_PADRAO = "postgresql://guardiao:guardiao_dev@localhost:54329/guardiao"


@contextmanager
def conexao():
    with psycopg.connect(os.environ.get("DATABASE_URL", URL_PADRAO)) as conn:
        yield conn  # commit ao sair sem erro, rollback com erro


def permitir_ficticios() -> bool:
    return os.environ.get("PERMITIR_TARIFA_FICTICIA") == "1"
