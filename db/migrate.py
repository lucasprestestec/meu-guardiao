"""Aplica db/migrations/*.sql em ordem, uma vez cada.

    python db/migrate.py            # usa DATABASE_URL
"""
import os
import pathlib
import sys

import psycopg

URL_PADRAO = "postgresql://guardiao:guardiao_dev@localhost:54329/guardiao"
PASTA = pathlib.Path(__file__).parent / "migrations"


def migrar(url: str) -> list[str]:
    aplicadas = []
    with psycopg.connect(url, autocommit=True) as conn:
        conn.execute(
            "CREATE TABLE IF NOT EXISTS schema_migrations "
            "(arquivo text PRIMARY KEY, aplicada_em timestamptz NOT NULL DEFAULT now())"
        )
        feitas = {r[0] for r in conn.execute("SELECT arquivo FROM schema_migrations")}
        for arq in sorted(PASTA.glob("*.sql")):
            if arq.name in feitas:
                continue
            conn.execute(arq.read_text(encoding="utf-8"))
            conn.execute("INSERT INTO schema_migrations (arquivo) VALUES (%s)", (arq.name,))
            aplicadas.append(arq.name)
    return aplicadas


if __name__ == "__main__":
    novas = migrar(os.environ.get("DATABASE_URL", URL_PADRAO))
    print("aplicadas:", ", ".join(novas) if novas else "nenhuma (já em dia)")
    sys.exit(0)
