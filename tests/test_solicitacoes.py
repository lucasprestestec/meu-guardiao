"""Contratação, régua de status e backoffice."""
import uuid
from datetime import date

import psycopg
import pytest

from api.solicitacoes import TEXTO_CONSENTIMENTOS, cpf_valido

from .test_api import _diagnosticar, _req_comparar, banco, cli, dev  # noqa: F401

CHAVE = {"X-Backoffice-Key": "chave-de-teste"}
NASC_38 = date(date.today().year - 38, date.today().month, 1).isoformat()


@pytest.fixture(autouse=True)
def _chave(monkeypatch):
    monkeypatch.setenv("BACKOFFICE_KEY", "chave-de-teste")


def _dados(**extra):
    d = {"nome": "Ana Carolina Silva", "cpf": "529.982.247-25", "data_nascimento": NASC_38,
         "email": "Ana@Exemplo.com", "celular": "(11) 98765-4321", "profissao": "Analista",
         "faixa_renda": "8-12k", "estado_civil": "Casada", "cidade": "São Paulo", "uf": "SP"}
    d.update(extra)
    return d


def _cotar(c):
    nid = _diagnosticar(c)["necessidade_id"]
    r = c.post("/v1/comparar", json=_req_comparar(nid)).json()
    return r["cotacao_id"], r["opcoes"][0]["produto_versao_id"]


def _solicitar(c, **extra):
    cot, pv = _cotar(c)
    corpo = {"cotacao_id": cot, "produto_versao_id": pv, "dados": _dados(),
             "consentimentos": list(TEXTO_CONSENTIMENTOS)}
    corpo.update(extra)
    return c.post("/v1/solicitacoes", json=corpo)


def _mudar(c, sid, status, **kw):
    return c.post(f"/v1/backoffice/solicitacoes/{sid}/status", headers=CHAVE,
                  json={"status": status, **kw})


def test_cpf():
    assert cpf_valido("52998224725")
    assert not cpf_valido("52998224726") and not cpf_valido("11111111111")


def test_fluxo_completo_ate_apolice_emitida(dev, banco):
    r = _solicitar(dev)
    assert r.status_code == 201, r.text
    sid = r.json()["id"]

    a = dev.get(f"/v1/solicitacoes/{sid}").json()
    assert a["status"] == "RECEBIDA" and a["primeiro_nome"] == "Ana" and a["demonstracao"] is True
    assert [p["estado"] for p in a["regua"]] == ["CONCLUIDO", "EM_ANDAMENTO"] + ["AGUARDANDO"] * 4
    assert {n["canal"] for n in a["notificacoes"]} == {"WHATSAPP", "EMAIL"}
    assert "Recebemos sua solicitação" in a["notificacoes"][0]["mensagem"]
    assert a["plano"]["itens"] and a["plano"]["premio_mensal"] > 0

    for st in ["EM_PREPARACAO", "ENVIADA", "EM_ANALISE"]:
        assert _mudar(dev, sid, st).status_code == 200
    assert _mudar(dev, sid, "PENDENCIA", pendencia="Exame complementar").status_code == 200
    a = dev.get(f"/v1/solicitacoes/{sid}").json()
    assert a["status"] == "PENDENCIA" and a["pendencia"] == "Exame complementar"
    assert a["regua"][3]["estado"] == "EM_ANDAMENTO"  # pendência acontece dentro da análise
    assert _mudar(dev, sid, "EM_ANALISE").status_code == 200
    assert _mudar(dev, sid, "APROVADA").status_code == 200
    assert _mudar(dev, sid, "EMITIDA", numero_apolice="123456").status_code == 200

    a = dev.get(f"/v1/solicitacoes/{sid}").json()
    assert all(p["estado"] == "CONCLUIDO" for p in a["regua"]) and a["numero_apolice"] == "123456"
    with psycopg.connect(banco) as c:
        assert c.execute("SELECT count(*) FROM apolice WHERE origem='EMITIDA'").fetchone()[0] == 1
        assert c.execute("SELECT count(*) FROM apolice_cobertura").fetchone()[0] == 4
        assert c.execute("SELECT count(*) FROM consentimento").fetchone()[0] == 4
        assert c.execute("SELECT count(*) FROM notificacao").fetchone()[0] == 2 * 8
        assert c.execute("SELECT count(*) FROM solicitacao_historico").fetchone()[0] == 8
        assert c.execute("SELECT nome, email FROM cliente WHERE nome IS NOT NULL").fetchone() == \
            ("Ana Carolina Silva", "ana@exemplo.com")


def test_exige_todos_os_consentimentos(dev):
    parcial = [c for c in TEXTO_CONSENTIMENTOS if c != "TERMOS"]
    assert _solicitar(dev, consentimentos=parcial).status_code == 422


def test_validacoes_de_dados(dev):
    assert _solicitar(dev, dados=_dados(cpf="111.111.111-11")).status_code == 422
    assert _solicitar(dev, dados=_dados(nome="Ana")).status_code == 422
    assert _solicitar(dev, dados=_dados(email="sem-arroba")).status_code == 422
    assert _solicitar(dev, dados=_dados(celular="123")).status_code == 422
    r = _solicitar(dev, dados=_dados(data_nascimento="1960-01-01"))
    assert r.status_code == 422 and "cotação foi feita para 38" in r.json()["detail"]


def test_produto_ficticio_nao_e_contratavel_fora_do_modo_dev(dev, monkeypatch):
    cot, pv = _cotar(dev)
    monkeypatch.delenv("PERMITIR_TARIFA_FICTICIA")
    r = dev.post("/v1/solicitacoes", json={"cotacao_id": cot, "produto_versao_id": pv,
                                            "dados": _dados(), "consentimentos": list(TEXTO_CONSENTIMENTOS)})
    assert r.status_code == 409
    assert dev.post("/v1/solicitacoes", json={"cotacao_id": str(uuid.uuid4()), "produto_versao_id": pv,
                                               "dados": _dados(), "consentimentos": list(TEXTO_CONSENTIMENTOS)}
                    ).status_code == 404


def test_transicoes_invalidas_e_pendencia_descrita(dev):
    sid = _solicitar(dev).json()["id"]
    r = _mudar(dev, sid, "EMITIDA")
    assert r.status_code == 409 and "RECEBIDA" in r.json()["detail"]
    _mudar(dev, sid, "EM_PREPARACAO")
    assert _mudar(dev, sid, "PENDENCIA").status_code == 422
    assert _mudar(dev, sid, "CANCELADA").status_code == 200
    assert _mudar(dev, sid, "EM_PREPARACAO").status_code == 409  # cancelada é final
    a = dev.get(f"/v1/solicitacoes/{sid}").json()
    assert a["status"] == "CANCELADA" and a["regua"][0]["estado"] == "CONCLUIDO"


def test_backoffice_exige_chave(dev, monkeypatch):
    assert dev.get("/v1/backoffice/resumo").status_code == 401
    assert dev.get("/v1/backoffice/resumo", headers={"X-Backoffice-Key": "errada"}).status_code == 401
    monkeypatch.delenv("BACKOFFICE_KEY")
    assert dev.get("/v1/backoffice/resumo", headers=CHAVE).status_code == 503


def test_fila_resumo_e_ficha(dev):
    a = _solicitar(dev).json()["id"]
    b = _solicitar(dev).json()["id"]
    _mudar(dev, b, "EM_PREPARACAO"); _mudar(dev, b, "ENVIADA")  # b agora é vez da seguradora
    fila = dev.get("/v1/backoffice/solicitacoes", headers=CHAVE).json()
    assert [s["id"] for s in fila["solicitacoes"]] == [a, b]  # vez da nossa equipe primeiro
    assert [s["com_quem"] for s in fila["solicitacoes"]] == ["NOS", "SEGURADORA"]
    assert dev.get("/v1/backoffice/solicitacoes?status=ENVIADA", headers=CHAVE).json()["solicitacoes"][0]["id"] == b
    assert dev.get("/v1/backoffice/solicitacoes?q=carol", headers=CHAVE).json()["solicitacoes"].__len__() == 2
    assert dev.get("/v1/backoffice/solicitacoes?q=zzz", headers=CHAVE).json()["solicitacoes"] == []
    r = dev.get("/v1/backoffice/resumo", headers=CHAVE).json()
    assert r == {"hoje": 2, "em_analise": 1, "pendencias": 0, "emitidas_30d": 0, "para_nos": 1}
    f = dev.get(f"/v1/backoffice/solicitacoes/{a}", headers=CHAVE).json()
    assert f["proximos_status"] == ["CANCELADA", "EM_PREPARACAO"]
    assert f["cliente"]["cpf_final"] == "25" and "cpf" not in f["cliente"]


def test_simulacao_nao_grava_nada(dev, banco):
    nid = _diagnosticar(dev)["necessidade_id"]
    r = dev.post("/v1/comparar", json=_req_comparar(nid, persistir=False)).json()
    assert r["cotacao_id"] is None and len(r["opcoes"]) == 3 and r["modo_demonstracao"] is True
    r2 = dev.post("/v1/comparar", json={"idade": 30, "sexo": "F", "fumante": False, "persistir": False,
                                        "capitais_escolhidos": {"NEC_MORTE": 500000}}).json()
    assert r2["cotacao_id"] is None
    with psycopg.connect(banco) as c:
        assert c.execute("SELECT count(*) FROM cotacao").fetchone()[0] == 0
        assert c.execute("SELECT count(*) FROM cliente").fetchone()[0] == 1  # só o do diagnóstico


def test_obter_necessidade(dev):
    d = _diagnosticar(dev)
    r = dev.get(f"/v1/necessidades/{d['necessidade_id']}").json()
    assert r["protection_score"] == d["protection_score"]
    assert [n["codigo"] for n in r["necessidades"]] == [n["codigo"] for n in d["necessidades"]]
    assert dev.get("/v1/necessidades/xyz").status_code == 404
