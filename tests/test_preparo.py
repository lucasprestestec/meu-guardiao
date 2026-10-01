"""Atualização automática do banco da demonstração (api/preparo.py)."""
import psycopg

from api import preparo

from .test_api import _diagnosticar, banco, cli, dev  # noqa: F401

# Simula um banco carregado ANTES de o catálogo ganhar a cobertura IPA nos produtos Alfa e Beta.
_APAGAR_IPA = (
    "DELETE FROM {tabela} WHERE {chave} IN (SELECT pv.id FROM produto_versao pv JOIN produto p ON p.id=pv.produto_id "
    "WHERE p.nome_comercial IN ('Vida Integral','Vida Simples')) AND codigo_cobertura='IPA'"
)


def _ipa_por_produto(url):
    with psycopg.connect(url) as c:
        return dict(c.execute(
            "SELECT p.nome_comercial, count(*) FROM produto_cobertura pc JOIN produto_versao pv ON pv.id=pc.produto_versao_id "
            "JOIN produto p ON p.id=pv.produto_id WHERE pc.codigo_cobertura='IPA' GROUP BY 1").fetchall())


def _envelhecer(url):
    with psycopg.connect(url) as c:
        c.execute("DELETE FROM tarifa_linha WHERE codigo_cobertura='IPA' AND tarifa_versao_id IN (SELECT tv.id FROM "
                  "tarifa_versao tv JOIN produto_versao pv ON pv.id=tv.produto_versao_id JOIN produto p ON p.id=pv.produto_id "
                  "WHERE p.nome_comercial IN ('Vida Integral','Vida Simples'))")
        c.execute(_APAGAR_IPA.format(tabela="produto_cobertura", chave="produto_versao_id"))
        c.commit()
    assert _ipa_por_produto(url) == {"Proteção Acidentes": 1}


def test_banco_antigo_e_completado_sozinho_no_modo_demonstracao(dev, banco):
    _envelhecer(banco)
    preparo._feitos.clear()
    r = _diagnosticar(dev)  # qualquer rota que abra conexão dispara o preparo
    assert r["necessidade_id"]
    assert _ipa_por_produto(banco) == {"Vida Integral": 1, "Vida Simples": 1, "Proteção Acidentes": 1}
    with psycopg.connect(banco) as c:  # o que já existia não foi tocado
        assert c.execute("SELECT count(*) FROM produto_cobertura WHERE codigo_cobertura IN ('IFPD','IPT_LISTA')"
                         ).fetchone()[0] == 2


def test_fora_do_modo_demonstracao_nada_e_alterado(cli, banco, monkeypatch):
    monkeypatch.delenv("PERMITIR_TARIFA_FICTICIA", raising=False)
    _envelhecer(banco)
    preparo._feitos.clear()
    cli.get("/v1/saude")
    _diagnosticar(cli)
    assert _ipa_por_produto(banco) == {"Proteção Acidentes": 1}


def test_falha_no_preparo_nao_derruba_a_api(dev, banco, monkeypatch):
    import seed_ficticio
    monkeypatch.setattr(seed_ficticio, "carregar", lambda *a, **k: (_ for _ in ()).throw(RuntimeError("x")))
    preparo._feitos.clear()
    assert _diagnosticar(dev)["necessidade_id"]
