"""Testes da camada de conectores, com seguradora simulada (sem rede)."""
import json
import time
import urllib.error

import pytest

from conectores import (
    CoberturaCotada, CoberturaSolicitada, Conector, ErroConector, PerfilCotacao,
    RespostaCotacao, cotar_em_conectores, montar_produto,
)
from conectores.azos import ConectorAzos
from conectores.icatu import ConectorIcatu
from conectores.mag import ConectorMag
from motor_dor import Dependente, Diagnostico, calcular
from motor_dor.comparador import CoberturaOfertada, Reajuste, Temporalidade, cotar

PERFIL = PerfilCotacao(idade=38, sexo="M", fumante=False)
MAPA = calcular(Diagnostico(idade=38, renda_mensal_liquida=25_000,
                            custo_familiar_mensal=18_000, dependentes=[Dependente(idade=6)]))
OFERTA = CoberturaOfertada("MORTE_QC", Temporalidade.VITALICIO, Reajuste.PREMIO_NIVELADO)
PEDIDO = [CoberturaSolicitada("MORTE_QC", 500_000)]


class Falso(Conector):
    def __init__(self, nome, resposta=None, erro=None, demora=0.0):
        self.nome, self._r, self._e, self._d = nome, resposta, erro, demora

    def configurado(self):
        return True

    def cotar(self, perfil, solicitadas):
        time.sleep(self._d)
        if self._e:
            raise self._e
        return self._r


def resposta(seg, premio=150.0, capital=500_000, inclui_iof=True):
    return RespostaCotacao(seg, "Vida", [CoberturaCotada("MORTE_QC", capital, premio, OFERTA)],
                           preco_inclui_iof=inclui_iof)


def test_produto_derivado_reproduz_o_preco_da_api():
    prod = montar_produto(resposta("X", premio=150.0), PERFIL)
    assert prod.fonte_tarifa == "API:X"
    cot = cotar(prod, MAPA, 38, "M", False, capitais_escolhidos={"NEC_MORTE": 500_000})
    assert round(cot.premio_mensal_total, 2) == 150.0


def test_preco_de_api_sem_iof_recebe_iof_e_com_iof_nao_recebe_de_novo():
    com = cotar(montar_produto(resposta("X", premio=150.0, inclui_iof=True), PERFIL), MAPA, 38, "M",
                False, capitais_escolhidos={"NEC_MORTE": 500_000})
    sem = cotar(montar_produto(resposta("X", premio=150.0, inclui_iof=False), PERFIL), MAPA, 38, "M",
                False, capitais_escolhidos={"NEC_MORTE": 500_000})
    assert round(com.premio_mensal_total, 2) == 150.0
    assert round(sem.premio_mensal_total, 2) == 150.57  # 150 x 1,0038


def test_preco_sem_informacao_de_iof_nao_vira_produto():
    r = resposta("X")
    r = RespostaCotacao(r.seguradora, r.produto, r.coberturas)  # preco_inclui_iof = None
    with pytest.raises(ErroConector, match="IOF"):
        montar_produto(r, PERFIL)


def test_capital_nao_extrapola_alem_do_que_a_api_cotou():
    prod = montar_produto(resposta("X", capital=300_000), PERFIL)
    cot = cotar(prod, MAPA, 38, "M", False, capitais_escolhidos={"NEC_MORTE": 500_000})
    morte = next(i for i in cot.itens if i.necessidade == "NEC_MORTE")
    assert morte.capital_contratado == 300_000


def test_falha_de_uma_seguradora_nao_derruba_as_outras():
    r = cotar_em_conectores(PERFIL, PEDIDO, [
        Falso("ok", resposta("Ok")), Falso("fora", erro=ErroConector("503")),
        Falso("bug", erro=KeyError("x")),
    ])
    assert [p.seguradora for p in r.produtos] == ["Ok"]
    assert len(r.avisos) == 2


def test_seguradora_lenta_vira_aviso():
    r = cotar_em_conectores(PERFIL, PEDIDO, [Falso("lenta", resposta("L"), demora=0.6)], prazo=0.1)
    assert r.produtos == [] and "sem resposta" in r.avisos[0]


def test_resposta_invalida_vira_aviso():
    r = cotar_em_conectores(PERFIL, PEDIDO, [Falso("z", resposta("Z", premio=-1))])
    assert r.produtos == [] and r.avisos


def test_azos_mag_e_icatu_ficam_desligados_sem_credencial(monkeypatch):
    for v in ("AZOS_API_KEY", "MAG_CLIENT_ID", "MAG_CLIENT_SECRET", "ICATU_SUBSCRIPTION_KEY"):
        monkeypatch.delenv(v, raising=False)
    assert not ConectorAzos().configurado() and not ConectorMag().configurado()
    assert not ConectorIcatu().configurado()
    assert cotar_em_conectores(PERFIL, PEDIDO).produtos == []


# --- Icatu: HTTP simulado, sem rede -----------------------------------------

MAPA_ICATU = {"MORTE_QC": {"numero": 1, "temporalidade": "TEMPORARIO", "reajuste": "ANUAL_INDICE"}}


class _Resp:
    def __init__(self, corpo):
        self._c = json.dumps(corpo).encode()

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False

    def read(self):
        return self._c


def _icatu(monkeypatch, corpo=None, erro=None):
    monkeypatch.setenv("ICATU_SUBSCRIPTION_KEY", "k")
    monkeypatch.setenv("ICATU_CODIGO_EMPRESA", "514")
    monkeypatch.setenv("ICATU_CODIGO_PRODUTO", "67612_0_2")
    monkeypatch.setenv("ICATU_MAPA_COBERTURAS", json.dumps(MAPA_ICATU))
    monkeypatch.setenv("ICATU_PRECO_INCLUI_IOF", "sim")
    visto = {}

    def abrir(req, timeout):
        visto["req"] = req
        if erro:
            raise erro
        return _Resp(corpo)

    return ConectorIcatu(abrir), visto


def test_icatu_monta_requisicao_e_le_o_preco_por_cobertura(monkeypatch):
    c, visto = _icatu(monkeypatch, {"idCotacao": "abc", "valorPremioTotal": 150.0,
                                    "coberturas": [{"numero": 1, "valorPremio": 150.0, "valorCapital": 400_000}]})
    r = c.cotar(PERFIL, PEDIDO)
    req = visto["req"]
    assert req.get_header("Codigoempresa") == "0514" and req.get_header("Ocp-apim-subscription-key") == "k"
    corpo = json.loads(req.data)
    assert corpo["proponente"]["pessoaFisica"]["sexo"] == "masculino"
    assert corpo["coberturas"] == [{"numero": 1, "valorCapital": 500_000}]
    assert r.referencia_externa == "abc" and r.coberturas[0].capital == 400_000
    assert round(montar_produto(r, PERFIL).tarifas[0].taxa_por_mil, 4) == 0.375


def test_icatu_aceita_formato_aninhado_da_doc(monkeypatch):
    c, _ = _icatu(monkeypatch, {"coberturas": [{"cobertura": {"numero": 1, "valorCapital": 500_000}, "premio": 90.0}]})
    assert c.cotar(PERFIL, PEDIDO).coberturas[0].premio_mensal == 90.0


def test_icatu_cobertura_fora_do_mapa_vira_aviso_ou_erro(monkeypatch):
    c, _ = _icatu(monkeypatch, {"coberturas": [{"numero": 1, "valorPremio": 10.0}]})
    r = c.cotar(PERFIL, PEDIDO + [CoberturaSolicitada("DIH", 300)])
    assert len(r.coberturas) == 1 and "DIH" in r.avisos[0]
    with pytest.raises(ErroConector):
        c.cotar(PERFIL, [CoberturaSolicitada("DIH", 300)])


def test_icatu_exige_declarar_se_o_preco_inclui_iof(monkeypatch):
    c, _ = _icatu(monkeypatch, {"coberturas": [{"numero": 1, "valorPremio": 10.0}]})
    monkeypatch.delenv("ICATU_PRECO_INCLUI_IOF")
    with pytest.raises(ErroConector, match="IOF"):
        c.cotar(PERFIL, PEDIDO)


def test_icatu_http_com_erro_vira_erro_do_conector(monkeypatch):
    c, _ = _icatu(monkeypatch, erro=urllib.error.HTTPError("u", 503, "x", {}, None))
    with pytest.raises(ErroConector, match="503"):
        c.cotar(PERFIL, PEDIDO)
