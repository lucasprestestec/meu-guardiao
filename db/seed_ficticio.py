"""Carrega o catálogo FICTÍCIO (motor_dor/catalogo_ficticio.py) no banco.

Só para desenvolvimento e demonstração. Tudo entra como RASCUNHO com tarifa
FICTICIA, portanto nunca chega ao consumidor (trigger no banco); a API só o
enxerga com PERMITIR_TARIFA_FICTICIA=1.

    python db/seed_ficticio.py
"""
import json
import os
import sys
import pathlib

import psycopg

sys.path.insert(0, str(pathlib.Path(__file__).parent.parent))
from motor_dor.catalogo_ficticio import CATALOGO  # noqa: E402
from motor_dor.comparador import TipoCapital  # noqa: E402

URL_PADRAO = "postgresql://guardiao:guardiao_dev@localhost:54329/guardiao"
VIGENCIA = "2026-01-01"
INF = float("inf")
# As tarifas do catálogo fictício são altas demais para um cliente achar plausível
# (~R$ 15 mil/mês). Na demonstração elas entram multiplicadas por este fator,
# o que preserva as proporções entre os produtos e leva os preços à casa de R$ 150 a R$ 600 por mês.
ESCALA_DEMO = 0.2


def _esc(valor, escala):
    return None if valor is None else round(valor * escala, 6)


def _renovacao(c):
    if not c.renovacao_automatica:
        return "NAO_RENOVAVEL"
    return "AUTOMATICA_NAO_GARANTIDA" if c.renovacao_exige_nova_subscricao else "AUTOMATICA_GARANTIDA"


def carregar(url=None, escala=ESCALA_DEMO):
    """`escala` multiplica todas as tarifas. Os testes usam 1.0 (números do contrato)."""
    criados = []
    with psycopg.connect(url or os.environ.get("DATABASE_URL", URL_PADRAO)) as conn:
        for p in CATALOGO:
            seg = conn.execute(
                "INSERT INTO seguradora (nome) VALUES (%s) ON CONFLICT (nome) DO UPDATE "
                "SET nome = EXCLUDED.nome RETURNING id", (p.seguradora,)).fetchone()[0]
            prod = conn.execute(
                "INSERT INTO produto (seguradora_id, nome_comercial, ramo_susep) VALUES (%s,%s,'A_DEFINIR') "
                "ON CONFLICT (seguradora_id, nome_comercial) DO UPDATE SET nome_comercial = EXCLUDED.nome_comercial "
                "RETURNING id", (seg, p.nome)).fetchone()[0]
            if conn.execute("SELECT 1 FROM produto_versao WHERE produto_id=%s AND versao='ficticio-1'",
                            (prod,)).fetchone():
                continue
            pv = conn.execute(
                "INSERT INTO produto_versao (produto_id, versao, vigencia_inicio) "
                "VALUES (%s,'ficticio-1',%s) RETURNING id", (prod, VIGENCIA)).fetchone()[0]
            for c in p.coberturas.values():
                escopo = None
                if c.escopo_dg_qtd_doencas is not None:
                    escopo = json.dumps({
                        "quantidade_doencas": c.escopo_dg_qtd_doencas, "rol": [],
                        "cobre_estagio_inicial": c.escopo_dg_estagio_inicial,
                        "periodo_sobrevivencia_dias": 30})
                diaria = c.codigo in ("DIT", "DIT_A", "DIH", "DIH_UTI")
                conn.execute(
                    "INSERT INTO produto_cobertura (produto_versao_id, codigo_cobertura, tipo_capital, indice_atualizacao, "
                    "capital_minimo, capital_maximo, referencia_capital, limite_percentual_referencia, "
                    "temporalidade, idade_limite_cobertura, idade_min_contratacao, idade_max_contratacao, "
                    "renovacao, reajuste, carencia_dias_geral, franquia_dias, "
                    "periodo_maximo_indenizacao_dias, escopo_dg) "
                    "VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)",
                    (pv, c.codigo, c.tipo_capital.value,
                     "IPCA" if c.tipo_capital == TipoCapital.ATUALIZADO_INDICE else None,
                     c.capital_minimo or None,
                     None if c.capital_maximo == INF else c.capital_maximo,
                     c.limite_pct_de, None if c.limite_pct is None else c.limite_pct * 100,
                     c.temporalidade.value, c.idade_limite_cobertura, p.idade_min, p.idade_max,
                     _renovacao(c), c.reajuste.value, c.carencia_dias, c.franquia_dias,
                     120 if diaria else None, escopo))
            tv = conn.execute(
                "INSERT INTO tarifa_versao (produto_versao_id, versao, vigencia_inicio, fonte_tarifa, "
                "fonte_arquivo) VALUES (%s,'ficticia-1',%s,'FICTICIA','catalogo_ficticio.py') RETURNING id",
                (pv, VIGENCIA)).fetchone()[0]
            with conn.cursor() as cur:
                cur.executemany(
                    "INSERT INTO tarifa_linha (tarifa_versao_id, codigo_cobertura, idade_min, idade_max, "
                    "sexo, fumante, taxa_por_mil, premio_por_unidade) VALUES (%s,%s,%s,%s,%s,%s,%s,%s)",
                    [(tv, t.codigo_cobertura, t.idade_min, t.idade_max, t.sexo, t.fumante,
                      _esc(t.taxa_por_mil, escala), _esc(t.premio_por_unidade, escala))
                     for t in p.tarifas])
            criados.append(f"{p.seguradora} / {p.nome}")
    return criados


if __name__ == "__main__":
    novos = carregar()
    print("carregados:", ", ".join(novos) if novos else "nenhum (já existiam)")
