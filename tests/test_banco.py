"""Testes do banco: as regras do HANDOFF precisam ser constraint, não comentário.

Cria um banco descartável, aplica as migrações e roda. Sem PostgreSQL
acessível (docker compose up -d), os testes são pulados.
"""
import os
import pathlib
import sys
import uuid

import pytest

psycopg = pytest.importorskip("psycopg")
sys.path.insert(0, str(pathlib.Path(__file__).parent.parent / "db"))
import importar_tarifario as imp  # noqa: E402
import migrate  # noqa: E402

ADMIN = os.environ.get("DATABASE_URL", migrate.URL_PADRAO)
DOCS = pathlib.Path(__file__).parent.parent / "docs"


@pytest.fixture(scope="module")
def url():
    nome = "teste_" + uuid.uuid4().hex[:8]
    try:
        adm = psycopg.connect(ADMIN, autocommit=True)
    except psycopg.OperationalError:
        pytest.skip("PostgreSQL indisponível")
    adm.execute(f"CREATE DATABASE {nome}")
    u = ADMIN.rsplit("/", 1)[0] + "/" + nome
    migrate.migrar(u)
    yield u
    adm.execute(f"DROP DATABASE {nome} WITH (FORCE)")
    adm.close()


@pytest.fixture
def conn(url):
    with psycopg.connect(url) as c:
        yield c
        c.rollback()


def _produto_publicavel(conn, fonte):
    """Cria produto_versao RASCUNHO completo; devolve id."""
    seg = conn.execute("INSERT INTO seguradora (nome) VALUES (%s) RETURNING id",
                       ("S" + uuid.uuid4().hex[:6],)).fetchone()[0]
    prod = conn.execute("INSERT INTO produto (seguradora_id, nome_comercial, ramo_susep) "
                        "VALUES (%s,'P','x') RETURNING id", (seg,)).fetchone()[0]
    cg = conn.execute("INSERT INTO condicoes_gerais_versao (produto_id, versao, vigencia_inicio) "
                      "VALUES (%s,'1','2026-01-01') RETURNING id", (prod,)).fetchone()[0]
    pv = conn.execute("INSERT INTO produto_versao (produto_id, versao, vigencia_inicio, "
                      "condicoes_gerais_versao_id) VALUES (%s,'1','2026-01-01',%s) RETURNING id",
                      (prod, cg)).fetchone()[0]
    conn.execute("INSERT INTO produto_cobertura (produto_versao_id, codigo_cobertura, tipo_capital,"
                 " temporalidade, idade_min_contratacao, idade_max_contratacao, renovacao, reajuste)"
                 " VALUES (%s,'MORTE_QC','NIVELADO','VITALICIO',18,65,'AUTOMATICA_GARANTIDA',"
                 "'PREMIO_NIVELADO')", (pv,))
    conn.execute("INSERT INTO tarifa_versao (produto_versao_id, versao, vigencia_inicio, fonte_tarifa)"
                 " VALUES (%s,'t1','2026-01-01',%s)", (pv, fonte))
    return pv


def test_migracoes_e_catalogo(conn):
    assert conn.execute("SELECT count(*) FROM cobertura_canonica").fetchone()[0] == 24


def test_tarifa_ficticia_nao_publica(conn):
    pv = _produto_publicavel(conn, "FICTICIA")
    with pytest.raises(psycopg.errors.RaiseException, match="FICTICIA"):
        conn.execute("UPDATE produto_versao SET status='PUBLICADO' WHERE id=%s", (pv,))


def test_tarifa_real_publica_e_aparece_na_view(conn):
    pv = _produto_publicavel(conn, "SEGURADORA")
    conn.execute("UPDATE produto_versao SET status='PUBLICADO' WHERE id=%s", (pv,))
    assert conn.execute("SELECT count(*) FROM vw_produto_exibivel WHERE produto_versao_id=%s",
                        (pv,)).fetchone()[0] == 1


def test_nao_entra_tarifa_ficticia_em_produto_publicado(conn):
    pv = _produto_publicavel(conn, "SEGURADORA")
    conn.execute("UPDATE produto_versao SET status='PUBLICADO' WHERE id=%s", (pv,))
    with pytest.raises(psycopg.errors.RaiseException):
        conn.execute("INSERT INTO tarifa_versao (produto_versao_id, versao, vigencia_inicio,"
                     " fonte_tarifa) VALUES (%s,'t2','2026-06-01','FICTICIA')", (pv,))


def test_publicacao_exige_condicoes_gerais(conn):
    pv = _produto_publicavel(conn, "SEGURADORA")
    conn.execute("UPDATE produto_versao SET condicoes_gerais_versao_id=NULL WHERE id=%s", (pv,))
    with pytest.raises(psycopg.errors.RaiseException, match="condicoes gerais"):
        conn.execute("UPDATE produto_versao SET status='PUBLICADO' WHERE id=%s", (pv,))


def test_mapeamento_nao_verificado_bloqueia_publicacao(conn):
    pv = _produto_publicavel(conn, "SEGURADORA")
    conn.execute("INSERT INTO mapeamento_cobertura (produto_versao_id, rotulo_original,"
                 " codigo_cobertura) VALUES (%s,'Invalidez','IFPD')", (pv,))
    with pytest.raises(psycopg.errors.RaiseException, match="nao verificado"):
        conn.execute("UPDATE produto_versao SET status='PUBLICADO' WHERE id=%s", (pv,))


def test_dg_sem_escopo_e_rejeitada(conn):
    pv = _produto_publicavel(conn, "SEGURADORA")
    with pytest.raises(psycopg.errors.CheckViolation):
        conn.execute("INSERT INTO produto_cobertura (produto_versao_id, codigo_cobertura,"
                     " tipo_capital, temporalidade, idade_min_contratacao, idade_max_contratacao,"
                     " renovacao, reajuste) VALUES (%s,'DG','NIVELADO','VITALICIO',18,65,"
                     "'AUTOMATICA_GARANTIDA','PREMIO_NIVELADO')", (pv,))


def test_reajuste_etario_exige_projecao(conn):
    pv = _produto_publicavel(conn, "SEGURADORA")
    conn.execute("UPDATE produto_cobertura SET reajuste='FAIXA_ETARIA' WHERE produto_versao_id=%s", (pv,))
    tv = conn.execute("SELECT id FROM tarifa_versao WHERE produto_versao_id=%s", (pv,)).fetchone()[0]
    cli = conn.execute("INSERT INTO cliente DEFAULT VALUES RETURNING id").fetchone()[0]
    cot = conn.execute("INSERT INTO cotacao (cliente_id, comparador_versao, idade, sexo, fumante) "
                       "VALUES (%s,'t',38,'M',false) RETURNING id", (cli,)).fetchone()[0]
    with pytest.raises(psycopg.errors.RaiseException, match="projecao"):
        conn.execute("INSERT INTO cotacao_item (cotacao_id, produto_versao_id, tarifa_versao_id,"
                     " premio_mensal) VALUES (%s,%s,%s,100)", (cot, pv, tv))


def test_um_cliente_varias_apolices_varias_seguradoras(conn):
    cli = conn.execute("INSERT INTO cliente DEFAULT VALUES RETURNING id").fetchone()[0]
    for _ in range(2):
        s = conn.execute("INSERT INTO seguradora (nome) VALUES (%s) RETURNING id",
                         (f"X{uuid.uuid4().hex[:5]}",)).fetchone()[0]
        conn.execute("INSERT INTO apolice (cliente_id, seguradora_id) VALUES (%s,%s)", (cli, s))
    assert conn.execute("SELECT count(DISTINCT seguradora_id) FROM apolice WHERE cliente_id=%s",
                        (cli,)).fetchone()[0] == 2


def test_importador_grava_modelo_como_ficticia(url):
    r = imp.importar(url, DOCS / "tarifario-modelo.csv", "2026.1-t1", "FICTICIA",
                     DOCS / "agravos-modelo.csv", "A_DEFINIR")
    assert r == [("Exemplo Seguros", "Vida Individual", "2026.1", 7, 4)]
    with psycopg.connect(url) as c:
        assert c.execute("SELECT fonte_tarifa FROM tarifa_versao").fetchone()[0] == "FICTICIA"


def test_importador_rejeita_tarifa_repetida(url):
    with pytest.raises(imp.ErroImportacao, match="imutável"):
        imp.importar(url, DOCS / "tarifario-modelo.csv", "2026.1-t1", "FICTICIA", None, "A_DEFINIR")


def test_importador_tudo_ou_nada_e_lista_todos_os_erros(url, tmp_path):
    cab = (DOCS / "tarifario-modelo.csv").read_text(encoding="utf-8").splitlines()[0]
    ruim = tmp_path / "ruim.csv"
    ruim.write_text("\n".join([
        cab,
        "S,P,1,MORTE_QC,18,24,M,false,,0.4,,5,9,BRL,2026-01-01,x",         # ok
        "S,P,1,MORTE_QC,20,30,M,false,,0.4,,5,9,BRL,2026-01-01,x",         # sobrepõe
        "S,P,1,NAO_EXISTE,18,24,M,false,,0.4,,5,9,BRL,2026-01-01,x",       # cobertura inválida
        "S,P,1,DIT,18,24,M,false,,0.4,,5,9,BRL,2026-01-01,x",              # diária com taxa
        "S,P,1,MORTE_QC,30,40,M,false,,0.4,0.2,5,9,BRL,2026-01-01,x",      # as duas métricas
    ]) + "\n", encoding="utf-8")
    with pytest.raises(imp.ErroImportacao) as e:
        imp.importar(url, ruim, "t9", "FICTICIA", None, "A_DEFINIR")
    assert len(e.value.erros) == 4
    with psycopg.connect(url) as c:
        assert c.execute("SELECT count(*) FROM seguradora WHERE nome='S'").fetchone()[0] == 0
