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


# --- disparo pós-contratação ---------------------------------------------------


def test_primeira_mensagem_traz_confirmacao_regua_e_condicoes_gerais(dev, monkeypatch):
    monkeypatch.setenv("PRAZO_ESPERADO_TEXTO", "até 5 dias úteis")
    monkeypatch.setenv("CANAL_CONTATO_TEXTO", "WhatsApp (11) 99999-0000")
    sid = _solicitar(dev).json()["id"]
    msg = dev.get(f"/v1/solicitacoes/{sid}").json()["notificacoes"][0]["mensagem"]
    assert "Recebemos sua solicitação" in msg and "O que acontece agora" in msg
    assert "Solicitação recebida → Proposta em preparação" in msg and "Apólice emitida" in msg
    assert "Prazo esperado: até 5 dias úteis" in msg and "WhatsApp (11) 99999-0000" in msg
    assert "condições gerais" in msg.lower()
    f = dev.get(f"/v1/backoffice/solicitacoes/{sid}", headers=CHAVE).json()
    assert f["condicoes_gerais"]["url"] is None  # sem link: o backoffice alerta a equipe
    assert "serão enviadas a você hoje" in msg


def test_com_link_das_condicoes_gerais_a_mensagem_leva_o_link(dev, banco):
    with psycopg.connect(banco) as c:
        c.execute("INSERT INTO condicoes_gerais_versao (produto_id, versao, vigencia_inicio, url_documento) "
                  "SELECT produto_id, 'v1', current_date, 'https://exemplo.com/cg.pdf' FROM produto_versao")
        c.execute("UPDATE produto_versao pv SET condicoes_gerais_versao_id = "
                  "(SELECT id FROM condicoes_gerais_versao cg WHERE cg.produto_id = pv.produto_id)")
        c.commit()
    sid = _solicitar(dev).json()["id"]
    msg = dev.get(f"/v1/solicitacoes/{sid}").json()["notificacoes"][0]["mensagem"]
    assert "https://exemplo.com/cg.pdf" in msg
    f = dev.get(f"/v1/backoffice/solicitacoes/{sid}", headers=CHAVE).json()
    assert f["condicoes_gerais"]["url"] == "https://exemplo.com/cg.pdf"


def test_caixa_de_saida_para_o_crm_e_confirmacao_de_envio(dev):
    sid = _solicitar(dev).json()["id"]
    assert dev.get("/v1/backoffice/notificacoes/pendentes").status_code == 401
    r = dev.get("/v1/backoffice/notificacoes/pendentes?canal=WHATSAPP", headers=CHAVE).json()
    assert len(r["pendentes"]) == 1 and r["pendentes"][0]["solicitacao_id"] == sid
    assert r["pendentes"][0]["destino"] == "5511987654321"
    assert dev.post(f"/v1/backoffice/notificacoes/{r['pendentes'][0]['id']}/enviada", headers=CHAVE).status_code == 200
    assert dev.get("/v1/backoffice/notificacoes/pendentes?canal=WHATSAPP", headers=CHAVE).json()["pendentes"] == []
    assert len(dev.get("/v1/backoffice/notificacoes/pendentes?canal=EMAIL", headers=CHAVE).json()["pendentes"]) == 1
    assert dev.post("/v1/backoffice/notificacoes/999999/enviada", headers=CHAVE).status_code == 404


def test_email_so_sai_com_smtp_configurado_e_falha_nao_trava_a_fila(dev, monkeypatch):
    from api import envio
    _solicitar(dev)
    assert dev.post("/v1/backoffice/notificacoes/enviar-email", headers=CHAVE).status_code == 409
    monkeypatch.setenv("SMTP_HOST", "smtp.exemplo.com")
    monkeypatch.setenv("EMAIL_REMETENTE", "contato@exemplo.com")
    enviados = []
    monkeypatch.setattr(envio, "enviar_email", lambda d, a, c: enviados.append((d, a)))
    assert dev.post("/v1/backoffice/notificacoes/enviar-email", headers=CHAVE).json() == {"enviados": 1, "falhas": 0}
    assert enviados == [("ana@exemplo.com", envio.ASSUNTO_PADRAO)]
    assert dev.get("/v1/backoffice/notificacoes/pendentes?canal=EMAIL", headers=CHAVE).json()["pendentes"] == []

    _solicitar(dev)
    def quebra(d, a, c):
        raise OSError("smtp fora")
    monkeypatch.setattr(envio, "enviar_email", quebra)
    assert dev.post("/v1/backoffice/notificacoes/enviar-email", headers=CHAVE).json() == {"enviados": 0, "falhas": 1}
    assert len(dev.get("/v1/backoffice/notificacoes/pendentes?canal=EMAIL", headers=CHAVE).json()["pendentes"]) == 1


def _crm_falso(respostas):
    """Sobe um servidor HTTP que imita o DeskComm e grava o que recebeu."""
    import json
    import threading
    from http.server import BaseHTTPRequestHandler, HTTPServer

    recebidos = []

    class H(BaseHTTPRequestHandler):
        def do_POST(self):
            corpo = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
            recebidos.append((self.path, dict(self.headers), corpo))
            status, resp = respostas(self.path)
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps(resp).encode())

        def log_message(self, *a):
            pass

    srv = HTTPServer(("127.0.0.1", 0), H)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return srv, recebidos


def test_whatsapp_sai_pelo_crm_deskcomm_com_token_e_idempotencia(dev, monkeypatch):
    srv, recebidos = _crm_falso(lambda p: (200, {"data": {"conversation_id": "c-1", "contact_id": "k-1"}}))
    monkeypatch.setenv("DESKCOMM_URL", f"http://127.0.0.1:{srv.server_port}")
    monkeypatch.setenv("DESKCOMM_TOKEN", "dsk_teste")
    try:
        _solicitar(dev)
        assert dev.post("/v1/backoffice/notificacoes/enviar-whatsapp", headers=CHAVE).json() == \
            {"enviados": 1, "falhas": 0}
    finally:
        srv.shutdown()
    (p1, h1, c1), (p2, h2, c2) = recebidos
    assert p1 == "/api/v1/conversations/open-with-contact" and c1["phone_number"] == "+5511987654321"
    assert p2 == "/api/v1/messages" and c2["conversation_id"] == "c-1" and "Recebemos" in c2["body"]
    assert h1["Authorization"] == "Bearer dsk_teste" and len(h2["Idempotency-Key"]) == 36
    assert dev.get("/v1/backoffice/notificacoes/pendentes?canal=WHATSAPP", headers=CHAVE).json()["pendentes"] == []


def test_falha_do_crm_deixa_o_whatsapp_pendente(dev, monkeypatch):
    srv, recebidos = _crm_falso(lambda p: (429, {"error": {"code": "rate_limited"}}))
    monkeypatch.setenv("DESKCOMM_URL", f"http://127.0.0.1:{srv.server_port}")
    monkeypatch.setenv("DESKCOMM_TOKEN", "dsk_teste")
    try:
        _solicitar(dev)
        assert dev.post("/v1/backoffice/notificacoes/enviar-whatsapp", headers=CHAVE).json() == \
            {"enviados": 0, "falhas": 1}
    finally:
        srv.shutdown()
    assert len(dev.get("/v1/backoffice/notificacoes/pendentes?canal=WHATSAPP", headers=CHAVE).json()["pendentes"]) == 1


def test_sem_crm_configurado_o_envio_de_whatsapp_responde_409(dev, monkeypatch):
    monkeypatch.delenv("DESKCOMM_URL", raising=False)
    assert dev.post("/v1/backoffice/notificacoes/enviar-whatsapp", headers=CHAVE).status_code == 409
