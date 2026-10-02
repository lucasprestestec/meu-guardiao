"""Acesso ao banco: carrega produtos para o comparador e grava necessidade/cotação."""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import List, Optional

from psycopg.rows import dict_row

from motor_dor import MapaDeProtecao, Necessidade
from motor_dor.comparador import (
    CoberturaOfertada, Cotacao, Produto, Reajuste, TarifaLinha, Temporalidade,
    TipoCapital,
)

INF = float("inf")


@dataclass
class ProdutoCarregado:
    produto_versao_id: str
    tarifa_versao_id: str
    condicoes_gerais_versao_id: Optional[str]
    produto: Produto
    exibivel: bool  # PUBLICADO + tarifa da seguradora


def _f(v):
    return None if v is None else float(v)


def _cobertura(r) -> CoberturaOfertada:
    escopo = r["escopo_dg"] or {}
    qtd = escopo.get("quantidade_doencas")
    if qtd is None and escopo.get("rol"):
        qtd = len(escopo["rol"])
    pct = _f(r["limite_percentual_referencia"])
    # renovação: AUTOMATICA_GARANTIDA renova sem nova avaliação; a NAO_GARANTIDA
    # renova mas pode exigir nova subscrição; NAO_RENOVAVEL não renova.
    ren = r["renovacao"]
    return CoberturaOfertada(
        codigo=r["codigo_cobertura"],
        temporalidade=Temporalidade(r["temporalidade"]),
        reajuste=Reajuste(r["reajuste"]),
        tipo_capital=TipoCapital(r["tipo_capital"]),
        capital_minimo=_f(r["capital_minimo"]) or 0.0,
        capital_maximo=_f(r["capital_maximo"]) if r["capital_maximo"] is not None else INF,
        idade_limite_cobertura=r["idade_limite_cobertura"],
        carencia_dias=r["carencia_dias_geral"],
        franquia_dias=r["franquia_dias"],
        renovacao_automatica=ren != "NAO_RENOVAVEL",
        renovacao_exige_nova_subscricao=ren == "AUTOMATICA_NAO_GARANTIDA",
        escopo_dg_qtd_doencas=qtd,
        escopo_dg_estagio_inicial=bool(escopo.get("cobre_estagio_inicial", False)),
        limite_pct_de=r["referencia_capital"],
        limite_pct=None if pct is None else pct / 100.0,
    )


def carregar_produtos(conn, permitir_ficticios: bool) -> List[ProdutoCarregado]:
    """Produtos cotáveis.

    Padrão (consumidor): só produto_versao PUBLICADA com tarifa da seguradora.
    `permitir_ficticios` (apenas desenvolvimento) inclui também as demais.
    A tarifa usada é a vigente de início mais recente.
    """
    filtro = "" if permitir_ficticios else (
        "AND pv.status = 'PUBLICADO' AND tv.fonte_tarifa = 'SEGURADORA'"
    )
    cur = conn.cursor(row_factory=dict_row)
    cur.execute(f"""
        SELECT DISTINCT ON (pv.id)
               pv.id AS pv_id, pv.status, pv.condicoes_gerais_versao_id AS cg_id,
               tv.id AS tv_id, tv.fonte_tarifa,
               s.nome AS seguradora, p.nome_comercial
        FROM produto_versao pv
        JOIN produto p    ON p.id = pv.produto_id
        JOIN seguradora s ON s.id = p.seguradora_id AND s.ativa
        JOIN tarifa_versao tv ON tv.produto_versao_id = pv.id
             AND tv.vigencia_inicio <= CURRENT_DATE
             AND (tv.vigencia_fim IS NULL OR tv.vigencia_fim > CURRENT_DATE)
        WHERE EXISTS (SELECT 1 FROM produto_cobertura pc WHERE pc.produto_versao_id = pv.id)
        {filtro}
        ORDER BY pv.id, tv.vigencia_inicio DESC
    """)
    cabecalhos = cur.fetchall()
    out: List[ProdutoCarregado] = []
    for h in cabecalhos:
        cobs = conn.cursor(row_factory=dict_row)
        cobs.execute("SELECT * FROM produto_cobertura WHERE produto_versao_id = %s", (h["pv_id"],))
        coberturas = {r["codigo_cobertura"]: _cobertura(r) for r in cobs.fetchall()}
        # Linhas mais específicas (sexo/fumante definidos) antes das genéricas.
        lin = conn.cursor(row_factory=dict_row)
        lin.execute(
            "SELECT * FROM tarifa_linha WHERE tarifa_versao_id = %s AND classe_risco IS NULL "
            "ORDER BY (sexo IS NULL), (fumante IS NULL), codigo_cobertura, idade_min",
            (h["tv_id"],),
        )
        tarifas = [
            TarifaLinha(
                codigo_cobertura=r["codigo_cobertura"], idade_min=r["idade_min"],
                idade_max=r["idade_max"], taxa_por_mil=_f(r["taxa_por_mil"]),
                premio_por_unidade=_f(r["premio_por_unidade"]),
                sexo=r["sexo"], fumante=r["fumante"],
            )
            for r in lin.fetchall()
        ]
        # Aceitação do produto = interseção das faixas de contratação das coberturas.
        idades = conn.execute(
            "SELECT max(idade_min_contratacao), min(idade_max_contratacao) "
            "FROM produto_cobertura WHERE produto_versao_id = %s", (h["pv_id"],)
        ).fetchone()
        produto = Produto(
            seguradora=h["seguradora"], nome=h["nome_comercial"], coberturas=coberturas,
            tarifas=tarifas, idade_min=idades[0], idade_max=idades[1],
            fonte_tarifa=h["fonte_tarifa"],
        )
        out.append(ProdutoCarregado(
            produto_versao_id=str(h["pv_id"]), tarifa_versao_id=str(h["tv_id"]),
            condicoes_gerais_versao_id=str(h["cg_id"]) if h["cg_id"] else None,
            produto=produto,
            exibivel=h["status"] == "PUBLICADO" and h["fonte_tarifa"] == "SEGURADORA",
        ))
    return out


# ---------------------------------------------------------------------------
# Necessidade
# ---------------------------------------------------------------------------


def gravar_necessidade(conn, cliente_id: Optional[str], entradas: dict, mapa: MapaDeProtecao):
    if cliente_id is None:
        cliente_id = str(conn.execute("INSERT INTO cliente DEFAULT VALUES RETURNING id").fetchone()[0])
    elif not conn.execute("SELECT 1 FROM cliente WHERE id = %s", (cliente_id,)).fetchone():
        raise LookupError("cliente_id não encontrado")
    nid = conn.execute(
        "INSERT INTO necessidade (cliente_id, motor_versao, entradas, protection_score, "
        "vulnerabilidade_principal, alertas) VALUES (%s,%s,%s,%s,%s,%s) RETURNING id",
        (cliente_id, mapa.versao_motor, json.dumps(entradas), mapa.protection_score,
         mapa.vulnerabilidade_principal, json.dumps(mapa.alertas)),
    ).fetchone()[0]
    for n in mapa.necessidades:
        conn.execute(
            "INSERT INTO necessidade_item (necessidade_id, codigo_necessidade, rotulo, unidade, "
            "capital_necessario, valor_existente, peso, memoria, justificativa) "
            "VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)",
            (nid, n.codigo, n.rotulo, n.unidade, n.valor_necessario, n.valor_existente,
             n.peso, json.dumps(n.memoria), n.justificativa),
        )
    return str(nid), cliente_id


def carregar_necessidade(conn, necessidade_id: str):
    """Reconstrói o MapaDeProtecao gravado. Devolve (mapa, cliente_id) ou None."""
    cab = conn.execute(
        "SELECT cliente_id, motor_versao, protection_score, vulnerabilidade_principal, alertas "
        "FROM necessidade WHERE id = %s", (necessidade_id,)
    ).fetchone()
    if cab is None:
        return None
    itens = conn.execute(
        "SELECT codigo_necessidade, rotulo, unidade, capital_necessario, valor_existente, peso, "
        "memoria, justificativa FROM necessidade_item WHERE necessidade_id = %s "
        "ORDER BY codigo_necessidade", (necessidade_id,)
    ).fetchall()
    # mesma ordem que o motor emite
    ordem = ["NEC_MORTE", "NEC_INVALIDEZ", "NEC_DOENCA_GRAVE", "NEC_RENDA"]
    itens.sort(key=lambda r: ordem.index(r[0]) if r[0] in ordem else 99)
    necessidades = [
        Necessidade(codigo=r[0], rotulo=r[1], unidade=r[2], valor_necessario=float(r[3]),
                    valor_existente=float(r[4]), peso=float(r[5]), memoria=r[6], justificativa=r[7])
        for r in itens
    ]
    mapa = MapaDeProtecao(
        versao_motor=cab[1], protection_score=cab[2], necessidades=necessidades,
        vulnerabilidade_principal=cab[3], alertas=list(cab[4]),
    )
    return mapa, str(cab[0])


# ---------------------------------------------------------------------------
# Cotação
# ---------------------------------------------------------------------------


def gravar_cotacao(conn, *, cliente_id, necessidade_id, motor_versao, comparador_versao,
                   idade, sexo, fumante, capitais_escolhidos, modo_dev, itens, recado=None):
    """`itens`: lista de dicts com ProdutoCarregado, Cotacao e projeções."""
    cid = conn.execute(
        "INSERT INTO cotacao (cliente_id, necessidade_id, motor_versao, comparador_versao, idade, "
        "sexo, fumante, capitais_escolhidos, modo_dev_ficticio, recado) "
        "VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s) RETURNING id",
        (cliente_id, necessidade_id, motor_versao, comparador_versao, idade, sexo, fumante,
         json.dumps(capitais_escolhidos) if capitais_escolhidos is not None else None, modo_dev, recado),
    ).fetchone()[0]
    for i in itens:
        c: Cotacao = i["cotacao"]
        pc: ProdutoCarregado = i["carregado"]
        pr = i["projecao"] or {}
        conn.execute(
            "INSERT INTO cotacao_item (cotacao_id, produto_versao_id, tarifa_versao_id, "
            "condicoes_gerais_versao_id, premio_mensal, premio_ano_10, premio_ano_20, "
            "premio_ano_30, aderencia_total, motivo_ranking) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)",
            (cid, pc.produto_versao_id, pc.tarifa_versao_id, pc.condicoes_gerais_versao_id,
             round(c.premio_mensal_total, 2), pr.get(10), pr.get(20), pr.get(30),
             round(c.aderencia_total, 4), json.dumps(i["detalhe"])),
        )
    return str(cid)
