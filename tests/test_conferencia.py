"""Conferência do cliente, acesso registrado ao CPF e lembretes de prazo, com banco (rodada 3)."""
from datetime import timedelta

import psycopg
import pytest

from api.dps import questionario_de
from api.lembretes import hoje_no_brasil
from api.solicitacoes import TEXTO_CONSENTIMENTOS

from .test_api import banco, cli, dev  # noqa: F401
from .test_solicitacoes import CHAVE, _mudar, _solicitar


@pytest.fixture(autouse=True)
def _chaves(monkeypatch):
    monkeypatch.setenv("BACKOFFICE_KEY", "chave-de-teste")
    monkeypatch.setenv("DPS_PERFIL_DEMONSTRACAO", "AZOS")
    monkeypatch.delenv("CRON_SECRET", raising=False)


def _respostas():
    q = questionario_de("AZOS")
    return {p["id"]: (p["opcoes"][-1] if p["tipo"] == "unica" else [p["exclusiva"]] if p["tipo"] == "multipla"
                      else False) for p in q["perguntas"]}


def _nova(dev, com_dps=True):
    extra = {"dps": _respostas(), "consentimentos": [*TEXTO_CONSENTIMENTOS, "DPS_CONFERENCIA"]} if com_dps else {}
    r = _solicitar(dev, **extra)
    assert r.status_code == 201, r.text
    return r.json()["id"]


def _pedir(dev, sid):
    return dev.post(f"/v1/backoffice/solicitacoes/{sid}/conferencia", headers=CHAVE, json={})


# --- conferência ------------------------------------------------------------------------------


def test_conferencia_do_pedido_a_confirmacao(dev, banco):
    sid = _nova(dev)
    assert dev.get(f"/v1/solicitacoes/{sid}/conferencia").json()["estado"] == "NENHUMA"

    assert _pedir(dev, sid).status_code == 201
    assert _pedir(dev, sid).status_code == 409  # já há uma aguardando

    ver = dev.get(f"/v1/solicitacoes/{sid}/conferencia").json()
    assert ver["estado"] == "AGUARDANDO" and len(ver["dps"]) == 13 and ver["proposta"]["perfil"] == "COMUM"

    # erro sem explicação é recusado; com explicação fica registrado
    assert dev.post(f"/v1/solicitacoes/{sid}/conferencia", json={"acao": "corrigir"}).status_code == 422
    r = dev.post(f"/v1/solicitacoes/{sid}/conferencia", json={"acao": "corrigir", "nota": "Faltou o remédio"})
    assert r.json()["estado"] == "CONTESTADA"
    assert dev.post(f"/v1/solicitacoes/{sid}/conferencia", json={"acao": "confirmar"}).status_code == 409

    h = dev.get(f"/v1/backoffice/solicitacoes/{sid}/conferencia", headers=CHAVE).json()
    assert h["estado"] == "CONTESTADA" and h["conferencias"][0]["nota"] == "Faltou o remédio"

    # a equipe corrige e pede de novo; desta vez o cliente confirma
    assert _pedir(dev, sid).status_code == 201
    assert dev.post(f"/v1/solicitacoes/{sid}/conferencia", json={"acao": "confirmar"}).json()["estado"] == "CONFIRMADA"
    assert dev.get(f"/v1/solicitacoes/{sid}/conferencia").json()["estado"] == "CONFIRMADA"

    with psycopg.connect(banco) as c:
        assert c.execute("SELECT count(*) FROM solicitacao_conferencia WHERE dps_hash = "
                         "(SELECT hash_sha256 FROM dps_resposta)").fetchone()[0] == 2
        assert c.execute("SELECT count(*) FROM notificacao WHERE tipo LIKE 'CONFERENCIA:%'").fetchone()[0] == 4
        assert c.execute("SELECT count(*) FROM solicitacao_historico WHERE nota LIKE 'Cliente %'").fetchone()[0] == 2
        # resposta dada não muda mais, nem pelo banco
        with pytest.raises(psycopg.errors.RaiseException):
            c.execute("UPDATE solicitacao_conferencia SET resposta = 'CONTESTADA', nota = 'x' WHERE resposta = 'CONFIRMADA'")


def test_conferencia_exige_dps_e_chave_e_solicitacao_existente(dev):
    sem_dps = _nova(dev, com_dps=False)
    assert _pedir(dev, sem_dps).status_code == 409
    assert dev.post(f"/v1/backoffice/solicitacoes/{sem_dps}/conferencia", json={}).status_code == 401
    assert dev.post("/v1/solicitacoes/00000000-0000-0000-0000-000000000000/conferencia",
                    json={"acao": "confirmar"}).status_code == 404
    assert dev.post(f"/v1/solicitacoes/{sem_dps}/conferencia", json={"acao": "confirmar"}).status_code == 409


# --- CPF inteiro com registro --------------------------------------------------------------------


def test_cpf_inteiro_so_com_chave_e_cada_abertura_fica_registrada(dev, banco):
    sid = _nova(dev, com_dps=False)
    assert dev.post(f"/v1/backoffice/solicitacoes/{sid}/cpf", json={}).status_code == 401
    r1 = dev.post(f"/v1/backoffice/solicitacoes/{sid}/cpf", headers=CHAVE, json={"por": "maria"}).json()
    r2 = dev.post(f"/v1/backoffice/solicitacoes/{sid}/cpf", headers=CHAVE, json={"por": "joao"}).json()
    assert r1 == {"cpf": "529.982.247-25", "acessos": 1} and r2["acessos"] == 2
    h = dev.get(f"/v1/backoffice/solicitacoes/{sid}/conferencia", headers=CHAVE).json()
    assert [a["por"] for a in h["acessos_cpf"]] == ["joao", "maria"]
    # a ficha continua mostrando só o final; o CPF inteiro nunca vai na ficha
    f = dev.get(f"/v1/backoffice/solicitacoes/{sid}", headers=CHAVE).json()
    assert f["cliente"]["cpf_final"] == "25" and "529" not in str(f)
    with psycopg.connect(banco) as c:
        assert c.execute("SELECT count(*) FROM acesso_dado_pessoal").fetchone()[0] == 2


# --- lembretes ---------------------------------------------------------------------------------


def _aguardando(dev, dias, status="AGUARDANDO_ASSINATURA"):
    sid = _nova(dev, com_dps=False)
    caminho = ["EM_PREPARACAO"] if status == "AGUARDANDO_ASSINATURA" else ["EM_PREPARACAO", "ENVIADA", "EM_ANALISE"]
    for etapa in caminho:
        assert _mudar(dev, sid, etapa).status_code == 200
    prazo = (hoje_no_brasil() + timedelta(days=dias)).isoformat()
    assert _mudar(dev, sid, status, prazo_acao=prazo).status_code == 200
    return sid


def test_gera_lembrete_na_janela_e_nao_repete(dev, banco):
    _aguardando(dev, 2)
    r = dev.post("/v1/backoffice/lembretes/gerar", headers=CHAVE).json()
    assert r["candidatos"] == 1 and r["geradas"] == 2  # WhatsApp e e-mail
    assert dev.get("/v1/backoffice/lembretes/gerar", headers=CHAVE).json()["geradas"] == 0  # idempotente
    with psycopg.connect(banco) as c:
        msgs = [m[0] for m in c.execute("SELECT mensagem FROM notificacao WHERE tipo LIKE 'LEMBRETE:%'")]
    assert len(msgs) == 2 and "lembrete" in msgs[0] and "assinatura" in msgs[0]


def test_fora_da_janela_nao_gera_e_pagamento_tambem_gera(dev):
    _aguardando(dev, 10)
    assert dev.post("/v1/backoffice/lembretes/gerar", headers=CHAVE).json()["candidatos"] == 0
    _aguardando(dev, 0, status="AGUARDANDO_PAGAMENTO")
    assert dev.post("/v1/backoffice/lembretes/gerar", headers=CHAVE).json()["geradas"] == 2


def test_agendador_da_vercel_entra_com_cron_secret(dev, monkeypatch):
    _aguardando(dev, 1)
    assert dev.get("/v1/backoffice/lembretes/gerar").status_code == 401
    monkeypatch.setenv("CRON_SECRET", "segredo-do-cron")
    assert dev.get("/v1/backoffice/lembretes/gerar", headers={"authorization": "Bearer errado"}).status_code == 401
    r = dev.get("/v1/backoffice/lembretes/gerar", headers={"authorization": "Bearer segredo-do-cron"})
    assert r.status_code == 200 and r.json()["geradas"] == 2
