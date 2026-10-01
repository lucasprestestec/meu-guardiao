"""Testes da camada de conectores, com seguradora simulada (sem rede)."""
import time

from conectores import (
    CoberturaCotada, CoberturaSolicitada, Conector, ErroConector, PerfilCotacao,
    RespostaCotacao, cotar_em_conectores, montar_produto,
)
from conectores.azos import ConectorAzos
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


def resposta(seg, premio=150.0, capital=500_000):
    return RespostaCotacao(seg, "Vida", [CoberturaCotada("MORTE_QC", capital, premio, OFERTA)])


def test_produto_derivado_reproduz_o_preco_da_api():
    prod = montar_produto(resposta("X", premio=150.0), PERFIL)
    assert prod.fonte_tarifa == "API:X"
    cot = cotar(prod, MAPA, 38, "M", False, capitais_escolhidos={"NEC_MORTE": 500_000})
    assert round(cot.premio_mensal_total, 2) == 150.0


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


def test_azos_e_mag_ficam_desligados_sem_credencial(monkeypatch):
    for v in ("AZOS_API_KEY", "MAG_CLIENT_ID", "MAG_CLIENT_SECRET"):
        monkeypatch.delenv(v, raising=False)
    assert not ConectorAzos().configurado() and not ConectorMag().configurado()
    assert cotar_em_conectores(PERFIL, PEDIDO).produtos == []
