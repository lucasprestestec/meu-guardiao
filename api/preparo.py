"""Atualização automática do banco da DEMONSTRAÇÃO.

Na primeira conexão de cada processo da API, com PERMITIR_TARIFA_FICTICIA=1 (modo
demonstração, o que a Vercel já tem ligado), aplica as migrações que faltam e completa o
catálogo fictício com o que ele ganhou (ex.: cobertura nova). Assim um deploy novo não
deixa o banco desatualizado e ninguém precisa rodar `preparar-online` à mão.

Segurança:
- Fora do modo demonstração nada disto roda: banco de produção só muda de forma deliberada.
- Só ADICIONA dados de catálogo (ver `seed_ficticio._completar`); não cria clientes de exemplo.
- Um lock do Postgres impede duas instâncias de preparar ao mesmo tempo.
- Qualquer falha é registrada e NÃO derruba a API: ela segue com o banco como está.
"""

from __future__ import annotations

import logging
import os
import pathlib
import sys
import threading

import psycopg

_RAIZ = pathlib.Path(__file__).resolve().parent.parent
_LOCK_ID = 7342001  # id arbitrário do advisory lock
_feitos: set = set()
_trava = threading.Lock()
log = logging.getLogger("preparo")


def preparar_uma_vez(url: str) -> None:
    """Idempotente por processo e por banco. Nunca levanta exceção."""
    with _trava:
        if url in _feitos:
            return
        _feitos.add(url)  # marca antes: se falhar, não tenta de novo a cada requisição
    try:
        db = str(_RAIZ / "db")
        if db not in sys.path:
            sys.path.insert(0, db)
        import migrate
        import seed_ficticio

        with psycopg.connect(url, autocommit=True) as lock:
            lock.execute("SELECT pg_advisory_lock(%s)", (_LOCK_ID,))
            try:
                novas = migrate.migrar(url)
                if novas:
                    log.warning("migrações aplicadas: %s", ", ".join(novas))
                carregados = seed_ficticio.carregar(url)
                if carregados:
                    log.warning("catálogo fictício atualizado: %s", "; ".join(carregados))
            finally:
                lock.execute("SELECT pg_advisory_unlock(%s)", (_LOCK_ID,))
    except Exception as e:  # noqa: BLE001 — a API não pode cair por causa do preparo
        log.error("preparo automático do banco falhou: %s", type(e).__name__)


def preparar_se_demonstracao(url: str) -> None:
    if os.environ.get("PERMITIR_TARIFA_FICTICIA") == "1":
        preparar_uma_vez(url)
