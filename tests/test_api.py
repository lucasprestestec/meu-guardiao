"""Testes da API contra um PostgreSQL descartável (pulados sem banco)."""
import json
import os
import pathlib
import sys
import uuid

import pytest

psycopg = pytest.importorskip("psycopg")
pytest.importorskip("fastapi")
from fastapi.testclient import TestClient  # noqa: E402

RAIZ = pathlib.Path(__file__).parent.parent
sys.path.insert(0, str(RAIZ / "db"))
import migrate  # noqa: E402
import seed_ficticio  # noqa: E402

from api.main import app  # noqa: E402

ADMIN = os.environ.get("DATABASE_URL", migrate.URL_PADRAO)
CONTRATO_MOTOR = json.loads((RAIZ / "docs/contrato-motor.json").read_text(encoding="utf-8"))["POST /v1/diagnostico"]
CONTRATO_COMP = json.loads((RAIZ / "docs/contrato-comparador.json").read_text(encoding="utf-8"))["POST /v1/comparar"]


@pytest.fixture
def banco(monkeypatch):
    nome = "teste_" + uuid.uuid4().hex[:8]
    try:
        adm = psycopg.connect(ADMIN, autocommit=True)
    except psycopg.OperationalError:
        pytest.skip("PostgreSQL indisponível")
    adm.execute(f"CREATE DATABASE {nome}")
    url = ADMIN.rsplit("/", 1)[0] + "/" + nome
    migrate.migrar(url)
    seed_ficticio.carregar(url, escala=1.0)
    monkeypatch.setenv("DATABASE_URL", url)
    monkeypatch.delenv("PERMITIR_TARIFA_FICTICIA", raising=False)
    yield url
    adm.execute(f"DROP DATABASE {nome} WITH (FORCE)")
    adm.close()


@pytest.fixture
def cli(banco):
    return TestClient(app)


@pytest.fixture
def dev(cli, monkeypatch):
    monkeypatch.setenv("PERMITIR_TARIFA_FICTICIA", "1")
    return cli


def _diagnosticar(c):
    r = c.post("/v1/diagnostico", json=CONTRATO_MOTOR["request"])
    assert r.status_code == 200, r.text
    return r.json()


def _req_comparar(nid, **extra):
    base = {"necessidade_id": nid, "idade": 38, "sexo": "M", "fumante": False}
    base.update(extra)
    return base


# --- /v1/diagnostico ---------------------------------------------------------


def test_diagnostico_reproduz_contrato_do_motor(cli):
    r = _diagnosticar(cli)
    esperado = CONTRATO_MOTOR["response"]
    for k, v in esperado.items():
        assert r[k] == v, k
    assert uuid.UUID(r["necessidade_id"])


def test_diagnostico_grava_memoria_de_calculo(cli, banco):
    r = _diagnosticar(cli)
    with psycopg.connect(banco) as c:
        n, motor = c.execute("SELECT count(*), max(motor_versao) FROM necessidade_item ni JOIN necessidade n "
                             "ON n.id = ni.necessidade_id WHERE n.id = %s", (r["necessidade_id"],)).fetchone()
        mem = c.execute("SELECT memoria FROM necessidade_item WHERE necessidade_id=%s AND "
                        "codigo_necessidade='NEC_MORTE'", (r["necessidade_id"],)).fetchone()[0]
    assert n == 4 and motor == r["versao_motor"]
    assert mem["capital_base_adotado"] == 3125000.0


def test_diagnostico_rejeita_campo_desconhecido_e_valor_absurdo(cli):
    ruim = dict(CONTRATO_MOTOR["request"], renda_mensal_liquida_typo=1)
    assert cli.post("/v1/diagnostico", json=ruim).status_code == 422
    absurdo = dict(CONTRATO_MOTOR["request"], custo_familiar_mensal=999_999)
    assert cli.post("/v1/diagnostico", json=absurdo).status_code == 422
    assert cli.post("/v1/diagnostico", json=dict(CONTRATO_MOTOR["request"], cliente_id=str(uuid.uuid4()))
                    ).status_code == 404


# --- /v1/comparar: travas de negócio -----------------------------------------


def test_sem_produto_publicado_nada_e_exibido(cli):
    nid = _diagnosticar(cli)["necessidade_id"]
    r = cli.post("/v1/comparar", json=_req_comparar(nid)).json()
    assert r["opcoes"] == []
    assert any("Nenhum produto" in a for a in r["alertas_gerais"])


def test_modo_dev_marca_ficticio_como_nao_exibivel(dev):
    nid = _diagnosticar(dev)["necessidade_id"]
    r = dev.post("/v1/comparar", json=_req_comparar(nid)).json()
    assert len(r["opcoes"]) == 3
    assert all(o["exibivel_ao_consumidor"] is False for o in r["opcoes"])
    assert all(o["produto"]["fonte_tarifa"] == "FICTICIA" for o in r["opcoes"])
    assert all(any("FICT" in a for a in o["alertas"]) for o in r["opcoes"])


def test_produto_publicado_com_tarifa_real_e_o_unico_visivel_ao_consumidor(cli, banco):
    with psycopg.connect(banco) as c:
        pv = c.execute("SELECT pv.id FROM produto_versao pv JOIN produto p ON p.id=pv.produto_id "
                       "WHERE p.nome_comercial='Vida Integral'").fetchone()[0]
        prod = c.execute("SELECT produto_id FROM produto_versao WHERE id=%s", (pv,)).fetchone()[0]
        cg = c.execute("INSERT INTO condicoes_gerais_versao (produto_id, versao, vigencia_inicio) "
                       "VALUES (%s,'1','2026-01-01') RETURNING id", (prod,)).fetchone()[0]
        c.execute("UPDATE produto_versao SET condicoes_gerais_versao_id=%s WHERE id=%s", (cg, pv))
        c.execute("UPDATE tarifa_versao SET fonte_tarifa='SEGURADORA' WHERE produto_versao_id=%s", (pv,))
        c.execute("UPDATE produto_versao SET status='PUBLICADO' WHERE id=%s", (pv,))
        c.commit()
    nid = _diagnosticar(cli)["necessidade_id"]
    r = cli.post("/v1/comparar", json=_req_comparar(nid)).json()
    assert [o["produto"]["nome"] for o in r["opcoes"]] == ["Vida Integral"]
    assert r["opcoes"][0]["exibivel_ao_consumidor"] is True
    assert r["destaques"]["recomendado"] == str(pv)


def test_reajuste_por_idade_sai_com_projecao_e_e_gravado(dev, banco):
    nid = _diagnosticar(dev)["necessidade_id"]
    r = dev.post("/v1/comparar", json=_req_comparar(nid)).json()
    por_nome = {o["produto"]["nome"]: o for o in r["opcoes"]}
    assert por_nome["Vida Integral"]["projecao_premio"] is None  # prêmio nivelado
    proj = por_nome["Proteção Acidentes"]["projecao_premio"]
    assert proj["ano_10"] > 0 and proj["ano_30"] != proj["ano_10"]
    with psycopg.connect(banco) as c:
        p10 = c.execute("SELECT premio_ano_10 FROM cotacao_item ci JOIN produto_versao pv ON pv.id=ci.produto_versao_id "
                        "JOIN produto p ON p.id=pv.produto_id WHERE p.nome_comercial='Proteção Acidentes'"
                        ).fetchone()[0]
        v = c.execute("SELECT motor_versao, comparador_versao FROM cotacao").fetchone()
    assert float(p10) == proj["ano_10"] and v == ("1.3.1", "1.3.0")


def test_produto_sem_tarifa_para_projetar_e_excluido_nao_exibido(dev, banco):
    with psycopg.connect(banco) as c:  # apaga a faixa 48-52 (idade 38+10) do produto Beta
        c.execute("DELETE FROM tarifa_linha WHERE idade_min = 48 AND tarifa_versao_id IN ("
                  "SELECT tv.id FROM tarifa_versao tv JOIN produto_versao pv ON pv.id=tv.produto_versao_id "
                  "JOIN produto p ON p.id=pv.produto_id WHERE p.nome_comercial='Vida Simples')")
        c.commit()
    nid = _diagnosticar(dev)["necessidade_id"]
    r = dev.post("/v1/comparar", json=_req_comparar(nid)).json()
    assert "Vida Simples" not in [o["produto"]["nome"] for o in r["opcoes"]]
    assert any("Vida Simples" in e["produto"] and "projet" in e["motivo"] for e in r["excluidos"])


# --- /v1/comparar: números ----------------------------------------------------


def test_sem_capitais_escolhidos_reproduz_o_contrato_do_comparador(dev):
    nid = _diagnosticar(dev)["necessidade_id"]
    r = dev.post("/v1/comparar", json=_req_comparar(nid)).json()
    esperado = CONTRATO_COMP["response"]["opcoes"]
    obtido = {o["produto"]["nome"]: o for o in r["opcoes"]}
    for e in esperado:
        o = obtido[e["produto"]["nome"]]
        assert o["premio_mensal"] == pytest.approx(e["premio_mensal"], abs=0.01)
        assert o["aderencia_total"] == pytest.approx(e["aderencia_total"], abs=1e-4)
        assert o["coberturas_ausentes"] == e["coberturas_ausentes"]
        assert [i["cobertura"] for i in o["itens"]] == [i["cobertura"] for i in e["itens"]]
    assert r["motor_versao"] == "1.3.1" and r["schema_versao"] == "1.0"


def test_escolher_menos_que_a_necessidade_reduz_aderencia_e_premio(dev):
    nid = _diagnosticar(dev)["necessidade_id"]
    opcoes = dev.post("/v1/comparar", json=_req_comparar(nid)).json()["opcoes"]
    base = next(o for o in opcoes if o["produto"]["nome"] == "Vida Integral")  # a lista vem por preço
    menos = dev.post("/v1/comparar", json=_req_comparar(
        nid, capitais_escolhidos={"NEC_MORTE": 1_000_000})).json()
    o = next(x for x in menos["opcoes"] if x["produto_versao_id"] == base["produto_versao_id"])
    assert o["aderencia_total"] < base["aderencia_total"]
    assert o["premio_mensal"] < base["premio_mensal"]
    morte = next(i for i in o["itens"] if i["necessidade"] == "NEC_MORTE")
    assert morte["capital_contratado"] == 1_000_000


def test_jornada_sem_diagnostico_usa_so_os_capitais_escolhidos(dev, banco):
    r = dev.post("/v1/comparar", json={
        "idade": 30, "sexo": "F", "fumante": False,
        "capitais_escolhidos": {"NEC_MORTE": 500_000, "NEC_DOENCA_GRAVE": 100_000}}).json()
    assert r["motor_versao"] is None
    assert any("Sem diagnóstico" in a for a in r["alertas_gerais"])
    assert {i["necessidade"] for o in r["opcoes"] for i in o["itens"]} == {"NEC_MORTE", "NEC_DOENCA_GRAVE"}
    with psycopg.connect(banco) as c:
        assert c.execute("SELECT necessidade_id, capitais_escolhidos FROM cotacao").fetchone()[0] is None


def test_entradas_invalidas_no_comparar(dev):
    nid = _diagnosticar(dev)["necessidade_id"]
    assert dev.post("/v1/comparar", json=_req_comparar(nid, capitais_escolhidos={"NEC_XYZ": 1})).status_code == 422
    assert dev.post("/v1/comparar", json=_req_comparar(nid, capitais_escolhidos={"NEC_MORTE": -1})).status_code == 422
    assert dev.post("/v1/comparar", json=_req_comparar(str(uuid.uuid4()))).status_code == 404
    assert dev.post("/v1/comparar", json=_req_comparar("nao-e-uuid")).status_code == 404
    assert dev.post("/v1/comparar", json={"idade": 30, "sexo": "M", "fumante": False}).status_code == 422
    assert dev.post("/v1/comparar", json=_req_comparar(nid, sexo="X")).status_code == 422


def test_saude_informa_o_que_o_ambiente_faz(cli, monkeypatch):
    s = cli.get("/v1/saude").json()
    assert s["modo_demonstracao"] is False and s["notificacoes_ativas"] is False
    monkeypatch.setenv("PERMITIR_TARIFA_FICTICIA", "1")
    monkeypatch.setenv("NOTIFICACOES_ATIVAS", "1")
    s = cli.get("/v1/saude").json()
    assert s["modo_demonstracao"] is True and s["notificacoes_ativas"] is True
