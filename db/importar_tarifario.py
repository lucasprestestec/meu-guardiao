"""Importa tarifário e agravos no formato de docs/tarifario-modelo.csv.

Tudo ou nada: se qualquer linha for inválida, nada é gravado e todos os erros
são listados de uma vez.

    python db/importar_tarifario.py docs/tarifario-modelo.csv \\
        --agravos docs/agravos-modelo.csv --tarifa-versao 2026.1-t1 \\
        --fonte FICTICIA --ramo-susep A_DEFINIR

`--fonte` é obrigatório de propósito: FICTICIA ou SEGURADORA. Tarifa FICTICIA
nunca deixa o produto ser publicado (trigger no banco).
"""
import argparse
import csv
import os
import sys
from collections import defaultdict
from decimal import Decimal, InvalidOperation

import psycopg

URL_PADRAO = "postgresql://guardiao:guardiao_dev@localhost:54329/guardiao"
COLUNAS_TARIFA = {
    "seguradora", "produto", "produto_versao", "codigo_cobertura", "idade_min",
    "idade_max", "sexo", "fumante", "classe_risco", "taxa_por_mil",
    "premio_por_unidade", "capital_minimo", "capital_maximo", "moeda",
    "vigencia_inicio", "fonte",
}
UNIDADES_POR_DIARIA = {"DIARIA", "RENDA_MENSAL"}


class ErroImportacao(Exception):
    def __init__(self, erros):
        self.erros = erros
        super().__init__("\n".join(erros))


def _dec(v):
    if v in (None, ""):
        return None
    try:
        return Decimal(v)
    except InvalidOperation:
        raise ValueError(f"número inválido: {v!r}")


def _bool(v):
    if v == "":
        return None
    if v.lower() in ("true", "false"):
        return v.lower() == "true"
    raise ValueError(f"booleano inválido: {v!r}")


def _ler_tarifa(caminho, unidades, erros):
    """Valida e devolve as linhas prontas para gravar."""
    with open(caminho, newline="", encoding="utf-8") as f:
        leitor = csv.DictReader(f)
        faltando = COLUNAS_TARIFA - set(leitor.fieldnames or [])
        if faltando:
            raise ErroImportacao([f"{caminho}: colunas ausentes: {sorted(faltando)}"])
        linhas, faixas = [], defaultdict(list)
        for n, r in enumerate(leitor, start=2):
            loc = f"{caminho} linha {n}"
            try:
                cod = r["codigo_cobertura"]
                if cod not in unidades:
                    raise ValueError(f"cobertura {cod!r} não existe no dicionário canônico")
                taxa, prem = _dec(r["taxa_por_mil"]), _dec(r["premio_por_unidade"])
                if (taxa is None) == (prem is None):
                    raise ValueError("exatamente uma entre taxa_por_mil e premio_por_unidade")
                por_diaria = unidades[cod] in UNIDADES_POR_DIARIA
                if por_diaria and prem is None:
                    raise ValueError(f"{cod} é diária/renda: usar premio_por_unidade")
                if not por_diaria and taxa is None:
                    raise ValueError(f"{cod} é capital: usar taxa_por_mil")
                if (taxa or prem) <= 0:
                    raise ValueError("taxa/prêmio deve ser > 0")
                imin, imax = int(r["idade_min"]), int(r["idade_max"])
                if imax < imin:
                    raise ValueError("idade_max < idade_min")
                sexo = r["sexo"] or None
                if sexo not in (None, "M", "F"):
                    raise ValueError(f"sexo inválido: {sexo!r}")
                if r["moeda"] != "BRL":
                    raise ValueError(f"moeda {r['moeda']!r}: só BRL")
                cmin, cmax = _dec(r["capital_minimo"]), _dec(r["capital_maximo"])
                if cmin is not None and cmax is not None and cmax < cmin:
                    raise ValueError("capital_maximo < capital_minimo")
                fum = _bool(r["fumante"])
                chave = (r["seguradora"], r["produto"], r["produto_versao"], cod,
                         sexo, fum, r["classe_risco"] or None)
                for (a, b, nl) in faixas[chave]:
                    if imin <= b and a <= imax:
                        raise ValueError(f"faixa {imin}-{imax} sobrepõe a da linha {nl}")
                faixas[chave].append((imin, imax, n))
                linhas.append({**r, "cod": cod, "imin": imin, "imax": imax, "sexo": sexo,
                               "fumante": fum, "classe": r["classe_risco"] or None,
                               "taxa": taxa, "prem": prem, "cmin": cmin, "cmax": cmax})
            except (ValueError, KeyError) as e:
                erros.append(f"{loc}: {e}")
    return linhas


def _ler_agravos(caminho, erros):
    out, vistos = [], set()
    with open(caminho, newline="", encoding="utf-8") as f:
        for n, r in enumerate(csv.DictReader(f), start=2):
            try:
                m = _dec(r["multiplicador"])
                if m is None or m <= 0:
                    raise ValueError("multiplicador deve ser > 0")
                k = (r["seguradora"], r["produto_versao"], r["tipo"], r["chave"])
                if k in vistos:
                    raise ValueError(f"agravo duplicado: {k[2]}/{k[3]}")
                vistos.add(k)
                out.append({**r, "mult": m})
            except (ValueError, KeyError) as e:
                erros.append(f"{caminho} linha {n}: {e}")
    return out


def importar(url, csv_tarifa, tarifa_versao, fonte, csv_agravos=None, ramo_susep=None):
    if fonte not in ("FICTICIA", "SEGURADORA"):
        raise ErroImportacao(["--fonte deve ser FICTICIA ou SEGURADORA"])
    with psycopg.connect(url) as conn:
        unidades = dict(conn.execute("SELECT codigo, unidade_capital::text FROM cobertura_canonica"))
        erros = []
        linhas = _ler_tarifa(csv_tarifa, unidades, erros)
        agravos = _ler_agravos(csv_agravos, erros) if csv_agravos else []
        if erros:
            raise ErroImportacao(erros)

        grupos = defaultdict(list)
        for l in linhas:
            grupos[(l["seguradora"], l["produto"], l["produto_versao"], l["vigencia_inicio"])].append(l)
        resumo = []
        for (seg, prod, pv, vig), ls in grupos.items():
            seg_id = conn.execute(
                "INSERT INTO seguradora (nome) VALUES (%s) "
                "ON CONFLICT (nome) DO UPDATE SET nome = EXCLUDED.nome RETURNING id", (seg,)
            ).fetchone()[0]
            achou = conn.execute(
                "SELECT id FROM produto WHERE seguradora_id=%s AND nome_comercial=%s", (seg_id, prod)
            ).fetchone()
            if achou:
                prod_id = achou[0]
            else:
                if not ramo_susep:
                    raise ErroImportacao([f"produto novo {seg}/{prod}: informe --ramo-susep"])
                prod_id = conn.execute(
                    "INSERT INTO produto (seguradora_id, nome_comercial, ramo_susep) "
                    "VALUES (%s,%s,%s) RETURNING id", (seg_id, prod, ramo_susep)
                ).fetchone()[0]
            pv_id = conn.execute(
                "INSERT INTO produto_versao (produto_id, versao, vigencia_inicio) VALUES (%s,%s,%s) "
                "ON CONFLICT (produto_id, versao) DO UPDATE SET versao = EXCLUDED.versao RETURNING id",
                (prod_id, pv, vig),
            ).fetchone()[0]
            try:
                tv_id = conn.execute(
                    "INSERT INTO tarifa_versao (produto_versao_id, versao, vigencia_inicio, "
                    "fonte_tarifa, fonte_arquivo) VALUES (%s,%s,%s,%s,%s) RETURNING id",
                    (pv_id, tarifa_versao, vig, fonte, os.path.basename(csv_tarifa)),
                ).fetchone()[0]
            except psycopg.errors.UniqueViolation:
                raise ErroImportacao([f"tarifa_versao {tarifa_versao!r} já existe para {seg}/{prod}/{pv}: "
                                      "tarifa é imutável, use outro nome de versão"])
            with conn.cursor() as cur:
                cur.executemany(
                    "INSERT INTO tarifa_linha (tarifa_versao_id, codigo_cobertura, idade_min, idade_max, "
                    "sexo, fumante, classe_risco, taxa_por_mil, premio_por_unidade, capital_minimo, "
                    "capital_maximo, fonte_ref) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)",
                    [(tv_id, l["cod"], l["imin"], l["imax"], l["sexo"], l["fumante"], l["classe"],
                      l["taxa"], l["prem"], l["cmin"], l["cmax"], l["fonte"]) for l in ls],
                )
            n_ag = 0
            for a in agravos:
                if (a["seguradora"], a["produto_versao"]) == (seg, pv):
                    conn.execute(
                        "INSERT INTO agravo (tarifa_versao_id, tipo, chave, multiplicador) "
                        "VALUES (%s,%s,%s,%s)", (tv_id, a["tipo"], a["chave"], a["mult"]))
                    n_ag += 1
            resumo.append((seg, prod, pv, len(ls), n_ag))
    return resumo


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("tarifario")
    ap.add_argument("--agravos")
    ap.add_argument("--tarifa-versao", required=True)
    ap.add_argument("--fonte", required=True, choices=["FICTICIA", "SEGURADORA"])
    ap.add_argument("--ramo-susep")
    a = ap.parse_args()
    try:
        for seg, prod, pv, nl, na in importar(os.environ.get("DATABASE_URL", URL_PADRAO), a.tarifario,
                                              a.tarifa_versao, a.fonte, a.agravos, a.ramo_susep):
            print(f"OK {seg} / {prod} / {pv}: {nl} linhas de tarifa, {na} agravos")
    except ErroImportacao as e:
        print("IMPORTAÇÃO REJEITADA, nada foi gravado:\n  " + "\n  ".join(e.erros))
        sys.exit(1)
