"""Campos da proposta por seguradora (rodada 3): lógica pura, sem banco."""
from datetime import date
from decimal import Decimal

import pytest
from pydantic import ValidationError

from api.proposta import (
    AZOS, COMUM, ICATU, PropostaIn, campos_da_seguradora, perfil_de, validar_proposta,
)

BASE = {
    "profissao": "Analista", "estado_civil": "Solteiro(a)", "cidade": "São Paulo", "uf": "SP",
    "sexo": "M", "renda_mensal": Decimal("15000"), "peso_kg": Decimal("91"), "altura_cm": 180,
    "cep": "01001000", "logradouro": "Rua A", "numero_endereco": "10", "bairro": "Centro",
}
ICATU_EXTRA = {"aposentado": "nao", "nacionalidade": "Brasileira", "pais_nascimento": "Brasil",
               "pais_residencia": "Brasil", "pais_residencia_fiscal": "Brasil", "us_person": False,
               "origem_recurso": "Salário/pró-labore"}
BEN = {"nome": "Maria Silva", "data_nascimento": date(1990, 1, 1), "percentual": Decimal("100")}


def ben(parentesco, pct="100", nome="Maria Silva"):
    return {**BEN, "parentesco": parentesco, "percentual": Decimal(pct), "nome": nome}


def erros(perfil, campos=None, bens=None, legais=False, sexo="M", fumante=False):
    c = {**BASE, **(campos or {})}
    return validar_proposta(perfil, c, bens if bens is not None else [], legais, sexo, fumante,
                            hoje=date(2026, 10, 15))


def test_perfil_pela_razao_social():
    assert perfil_de("Azos Seguros") == AZOS and perfil_de("ICATU Seguros S.A.") == ICATU
    assert perfil_de("Exemplo Seguros") == COMUM


def test_comum_completo_com_beneficiario_passa():
    assert erros(COMUM, bens=[ben("Filho(a)")]) == []


def test_campo_faltando_e_apontado_pelo_nome():
    e = erros(COMUM, {"cep": None, "peso_kg": None}, [ben("Filho(a)")])
    assert any("CEP" in m for m in e) and any("peso" in m for m in e)


def test_azos_exige_pep_e_fumo_e_confere_fumante_com_a_cotacao():
    assert len(erros(AZOS, bens=[ben("Cônjuge")])) == 2  # pep e fumante_24_meses
    ok = erros(AZOS, {"pep": False, "fumante_24_meses": False}, [ben("Cônjuge")], fumante=False)
    assert ok == []
    div = erros(AZOS, {"pep": False, "fumante_24_meses": True}, [ben("Cônjuge")], fumante=False)
    assert len(div) == 1 and "fumar" in div[0]


def test_icatu_exige_campos_proprios_e_origem_da_lista_fechada():
    assert len(erros(ICATU, bens=[ben("ESPOSA")])) == 7
    assert erros(ICATU, ICATU_EXTRA, [ben("ESPOSA")]) == []
    e = erros(ICATU, {**ICATU_EXTRA, "origem_recurso": "Loteria"}, [ben("ESPOSA")])
    assert any("Origem do recurso" in m for m in e)


def test_sexo_diferente_da_cotacao_e_recusado():
    e = erros(COMUM, {"sexo": "F"}, [ben("Filho(a)")], sexo="M")
    assert len(e) == 1 and "refaça a comparação" in e[0]


def test_beneficiarios_soma_100_e_grau_da_lista():
    e = erros(COMUM, bens=[ben("Filho(a)", "60"), ben("Cônjuge ou companheiro(a)", "30", "Joao Pedro")])
    assert any("100%" in m and "90" in m for m in e)
    assert erros(COMUM, bens=[ben("Filho(a)", "60.50"), ben("Cônjuge ou companheiro(a)", "39.50", "Joao Pedro")]) == []
    assert any("parentesco" in m for m in erros(COMUM, bens=[ben("Vizinho")]))


def test_beneficiarios_legais_so_onde_a_seguradora_aceita():
    assert erros(AZOS, {"pep": False, "fumante_24_meses": False}, [], legais=True) == []
    assert any("ao menos um" in m for m in erros(ICATU, ICATU_EXTRA, [], legais=True))
    assert any("não os dois" in m for m in erros(COMUM, bens=[ben("Filho(a)")], legais=True))
    assert any("ao menos um" in m for m in erros(COMUM, bens=[]))


def test_formato_dos_campos_e_barrado_na_entrada():
    with pytest.raises(ValidationError):
        PropostaIn(cep="123")
    with pytest.raises(ValidationError):
        PropostaIn(peso_kg=Decimal("5"))
    with pytest.raises(ValidationError):
        PropostaIn(aposentado="talvez")
    assert PropostaIn(cep="01001-000").cep == "01001000"
    with pytest.raises(ValidationError):
        PropostaIn(beneficiarios=[{"nome": "Ana Lima", "data_nascimento": "1990-01-01",
                                   "parentesco": "FILHA", "percentual": "0"}])


def test_endpoint_de_campos_diz_o_que_mostrar_por_seguradora():
    i = campos_da_seguradora("Icatu")
    assert i["perfil"] == ICATU and "us_person" in i["exigidos"] and i["origens_recurso"]
    assert not i["aceita_beneficiarios_legais"] and "PAI" in i["parentescos"]
    a = campos_da_seguradora("Azos")
    assert "pep" in a["exigidos"] and a["aceita_beneficiarios_legais"] and not a["lista_parentesco_completa"]
    assert campos_da_seguradora("Exemplo Seguros")["perfil"] == COMUM
