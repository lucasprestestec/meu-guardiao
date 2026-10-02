"""Captura de contato (LGPD), pedido ao especialista, recados e funil."""
import psycopg

from api.solicitacoes import TEXTO_CONSENTIMENTOS

from .test_api import _diagnosticar, _req_comparar, banco, cli, dev  # noqa: F401
from .test_solicitacoes import CHAVE, _chave, _dados  # noqa: F401

LEAD = {"nome": "Ana Silva", "email": "Ana@Exemplo.com", "celular": "(11) 98765-4321",
        "consentimento_atendimento": True, "consentimento_marketing": False}


def test_textos_de_consentimento_trazem_versao_e_politica(cli):
    t = cli.get("/v1/lead/textos").json()
    assert t["versao"].startswith("rascunho") and t["politica_url"] == "/privacidade"
    assert "Política de Privacidade" in t["atendimento"] and "ofertas" in t["marketing"]


def test_lead_exige_o_primeiro_consentimento_e_o_segundo_e_opcional(cli, banco):
    assert cli.post("/v1/leads", json={**LEAD, "consentimento_atendimento": False}).status_code == 422
    r = cli.post("/v1/leads", json=LEAD, headers={"X-Forwarded-For": "200.1.2.3, 10.0.0.1",
                                                  "User-Agent": "teste"})
    assert r.status_code == 201
    with psycopg.connect(banco) as c:
        assert c.execute("SELECT nome, email, celular FROM lead_contato").fetchone() == \
            ("Ana Silva", "ana@exemplo.com", "11987654321")
        linhas = c.execute("SELECT tipo, aceito, texto_versao, ip, user_agent, aceito_em IS NOT NULL "
                           "FROM consentimento_lead ORDER BY tipo").fetchall()
    versao = linhas[0][2]
    assert versao.startswith("rascunho")
    assert linhas == [("ATENDIMENTO", True, versao, "200.1.2.3", "teste", True),
                      ("MARKETING", False, versao, "200.1.2.3", "teste", True)]


def test_lead_vinculado_ao_diagnostico_atualiza_o_cliente(cli, banco):
    nid = _diagnosticar(cli)["necessidade_id"]
    assert cli.post("/v1/leads", json={**LEAD, "necessidade_id": nid}).status_code == 201
    assert cli.post("/v1/leads", json={**LEAD, "necessidade_id": "00000000-0000-4000-8000-000000000000"}
                    ).status_code == 404
    with psycopg.connect(banco) as c:
        assert c.execute("SELECT c.nome FROM cliente c JOIN necessidade n ON n.cliente_id=c.id").fetchone()[0] \
            == "Ana Silva"


def test_funil_registra_eventos_e_recusa_etapa_desconhecida(cli):
    s = "sessao-12345678"
    assert cli.post("/v1/eventos", json={"etapa": "contato_visto", "sessao": s}).status_code == 204
    assert cli.post("/v1/eventos", json={"etapa": "qualquer", "sessao": s}).status_code == 422


def test_pedido_ao_especialista_chega_ao_backoffice_com_o_diagnostico_completo(dev):
    nid = _diagnosticar(dev)["necessidade_id"]
    lead = dev.post("/v1/leads", json={**LEAD, "necessidade_id": nid}).json()["id"]
    cot = dev.post("/v1/comparar", json=_req_comparar(nid, recado="Queria 8 milhões")).json()["cotacao_id"]
    corpo = {"nome": "Ana Silva", "email": "ana@exemplo.com", "celular": "11987654321",
             "motivos": ["CAPITAL_MAIOR", "DUVIDAS_COBERTURAS"], "mensagem": "Prefiro à tarde.",
             "lead_id": lead, "necessidade_id": nid, "cotacao_id": cot}
    r = dev.post("/v1/pedidos-especialista", json=corpo)
    assert r.status_code == 201
    pid = r.json()["id"]

    assert dev.get("/v1/backoffice/pedidos-especialista").status_code == 401
    fila = dev.get("/v1/backoffice/pedidos-especialista", headers=CHAVE).json()
    assert fila["pedidos"][0]["id"] == pid and fila["pedidos"][0]["tem_diagnostico"] is True
    assert "Quero capital maior do que o site permite" in fila["pedidos"][0]["motivos"]

    f = dev.get(f"/v1/backoffice/pedidos-especialista/{pid}", headers=CHAVE).json()
    assert f["contato"]["celular"] == "11987654321" and f["mensagem"] == "Prefiro à tarde."
    assert {n["codigo"] for n in f["diagnostico"]["mapa"]["necessidades"]} >= {"NEC_MORTE", "NEC_RENDA"}
    assert f["diagnostico"]["entradas"]["renda_mensal_liquida"] == 25000
    assert f["cotacao"]["recado"] == "Queria 8 milhões"
    assert {c["tipo"] for c in f["consentimentos"]} == {"ATENDIMENTO", "MARKETING"}

    assert dev.post(f"/v1/backoffice/pedidos-especialista/{pid}/status", headers=CHAVE,
                    json={"status": "EM_CONTATO"}).status_code == 200
    assert dev.get("/v1/backoffice/pedidos-especialista?status=NOVO", headers=CHAVE).json()["pedidos"] == []


def test_pedido_valida_motivos_e_exige_motivo_ou_mensagem(cli):
    base = {"nome": "Ana Silva", "email": "ana@exemplo.com", "celular": "11987654321"}
    assert cli.post("/v1/pedidos-especialista", json={**base, "motivos": ["INVENTADO"]}).status_code == 422
    assert cli.post("/v1/pedidos-especialista", json=base).status_code == 422
    assert cli.post("/v1/pedidos-especialista", json={**base, "mensagem": "Oi"}).status_code == 201


def test_recado_do_checkout_e_da_personalizacao_chegam_na_ficha_da_solicitacao(dev):
    nid = _diagnosticar(dev)["necessidade_id"]
    r = dev.post("/v1/comparar", json=_req_comparar(nid, recado="Quero 8 milhões de morte")).json()
    corpo = {"cotacao_id": r["cotacao_id"], "produto_versao_id": r["opcoes"][0]["produto_versao_id"],
             "dados": _dados(), "consentimentos": list(TEXTO_CONSENTIMENTOS), "recado": "Ligar depois das 18h"}
    sid = dev.post("/v1/solicitacoes", json=corpo).json()["id"]
    f = dev.get(f"/v1/backoffice/solicitacoes/{sid}", headers=CHAVE).json()
    assert f["recados"] == {"checkout": "Ligar depois das 18h", "personalizacao": "Quero 8 milhões de morte"}


def test_cirurgia_e_fratura_entram_na_cotacao_pelo_valor_escolhido(dev):
    nid = _diagnosticar(dev)["necessidade_id"]
    r = dev.post("/v1/comparar", json=_req_comparar(
        nid, capitais_escolhidos={"NEC_MORTE": 1_000_000, "NEC_CIRURGIA": 20_000, "NEC_FRATURA": 100_000})).json()
    por = {o["produto"]["nome"]: {i["necessidade"]: i for i in o["itens"]} for o in r["opcoes"]}
    assert por["Vida Integral"]["NEC_CIRURGIA"]["capital_contratado"] == 20_000
    assert por["Vida Integral"]["NEC_FRATURA"]["capital_contratado"] == 100_000
    assert por["Vida Simples"]["NEC_FRATURA"]["cobertura"] is None
    assert "não oferece" in " ".join(por["Vida Simples"]["NEC_FRATURA"]["observacoes"]).lower()
    precos = [o["premio_mensal"] for o in r["opcoes"]]  # do mais barato ao mais caro
    assert precos == sorted(precos)


def test_cobertura_desligada_sai_do_preco_mas_a_necessidade_continua_no_mapa(dev):
    nid = _diagnosticar(dev)["necessidade_id"]
    ligado = dev.post("/v1/comparar", json=_req_comparar(nid)).json()
    desligado = dev.post("/v1/comparar", json=_req_comparar(
        nid, capitais_escolhidos={"NEC_MORTE": 1_000_000, "NEC_INVALIDEZ": 0, "NEC_DOENCA_GRAVE": 0,
                                  "NEC_RENDA": 0})).json()
    achar = lambda r: next(x for x in r["opcoes"] if x["produto"]["nome"] == "Vida Integral")
    assert {i["necessidade"]: i["premio_mensal"] for i in achar(desligado)["itens"]}["NEC_DOENCA_GRAVE"] == 0
    assert achar(desligado)["premio_mensal"] < achar(ligado)["premio_mensal"]
    mapa = dev.get(f"/v1/necessidades/{nid}").json()  # o Mapa não finge que o risco sumiu
    assert all(n["valor_necessario"] > 0 for n in mapa["necessidades"])
