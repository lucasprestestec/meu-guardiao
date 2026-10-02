"""API do Meu Guardião.

    POST /v1/diagnostico   respostas do questionário -> Mapa de Proteção
    POST /v1/comparar      capitais escolhidos -> produtos ranqueados por aderência
    GET  /v1/saude

Contratos: docs/contrato-motor.json e docs/contrato-comparador.json.

Segurança de negócio:
  * Só produtos PUBLICADOS com tarifa da seguradora chegam ao consumidor.
    PERMITIR_TARIFA_FICTICIA=1 (apenas desenvolvimento) inclui os demais, e cada
    opção então sai com `exibivel_ao_consumidor: false`.
  * Produto com reajuste por idade só sai com projeção de prêmio em 10/20/30
    anos; se a projeção não é calculável, ele vai para `excluidos`.
  * Nenhum capital é decidido aqui: o Motor calcula, a API só transporta.

AINDA NÃO HÁ AUTENTICAÇÃO. `necessidade_id` é um UUID não adivinhável, o que
serve à demonstração, mas precisa de login antes de dados reais de clientes.
"""

from __future__ import annotations

import os
from dataclasses import replace
import uuid
from typing import Dict, List, Optional

import psycopg
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, ConfigDict, Field

from motor_dor import (
    Dependente, Diagnostico, Dividas, FaseDeVida, MapaDeProtecao, Necessidade, Projetos,
    SeguroAtual, SituacaoProfissional, VERSAO_MOTOR, calcular,
)
from motor_dor.comparador import PARAMETROS_COMPARADOR, comparar, recomendados
from motor_dor.projecao import HORIZONTES_ANOS, precisa_projecao, projetar_premio

from . import repositorio as repo
from .infra import conexao as _conexao, permitir_ficticios as _permitir_ficticios

SCHEMA_VERSAO = "1.0"
CODIGOS_NECESSIDADE = {
    "NEC_MORTE": ("Morte", "CAPITAL"),
    "NEC_INVALIDEZ": ("Invalidez", "CAPITAL"),
    "NEC_DOENCA_GRAVE": ("Doenças graves", "CAPITAL"),
    "NEC_RENDA": ("Diária de internação", "DIARIA"),
    # Escolhidas direto pelo cliente: o Motor não calcula necessidade para elas.
    "NEC_CIRURGIA": ("Cirurgias", "CAPITAL"),
    "NEC_FRATURA": ("Fraturas", "CAPITAL"),
}
ESCOLHA_DIRETA = ("NEC_CIRURGIA", "NEC_FRATURA")

app = FastAPI(title="Meu Guardião", version="0.1.0")


# ---------------------------------------------------------------------------
# Schemas de entrada (extra="forbid": campo digitado errado é erro, não silêncio)
# ---------------------------------------------------------------------------


class _Estrito(BaseModel):
    model_config = ConfigDict(extra="forbid")


class DependenteIn(_Estrito):
    idade: int = Field(ge=0, lt=120)
    financeiramente_dependente: bool = True


class DividasIn(_Estrito):
    imobiliaria: float = Field(0.0, ge=0)
    imobiliaria_tem_prestamista: bool = False
    empresarial: float = Field(0.0, ge=0)
    veiculos: float = Field(0.0, ge=0)
    outras: float = Field(0.0, ge=0)


class ProjetosIn(_Estrito):
    educacao_filhos: float = Field(0.0, ge=0)
    quitacao_imovel: float = Field(0.0, ge=0)
    outros: float = Field(0.0, ge=0)


class SeguroAtualIn(_Estrito):
    morte: float = Field(0.0, ge=0)
    invalidez: float = Field(0.0, ge=0)
    doenca_grave: float = Field(0.0, ge=0)
    dit_diaria: float = Field(0.0, ge=0)


class DiagnosticoIn(_Estrito):
    idade: int
    renda_mensal_liquida: float = Field(ge=0)
    custo_familiar_mensal: float = Field(ge=0)
    situacao_profissional: SituacaoProfissional = SituacaoProfissional.OUTRO
    fase_de_vida: Optional[FaseDeVida] = None
    dependentes: List[DependenteIn] = []
    horizonte_protecao_anos: Optional[int] = None
    dividas: DividasIn = DividasIn()
    projetos: ProjetosIn = ProjetosIn()
    patrimonio_liquido: float = Field(0.0, ge=0)
    patrimonio_inventariavel: float = Field(0.0, ge=0)
    meses_de_reserva: float = Field(0.0, ge=0)
    seguro_atual: SeguroAtualIn = SeguroAtualIn()
    cliente_id: Optional[str] = None

    def para_motor(self) -> Diagnostico:
        return Diagnostico(
            idade=self.idade, renda_mensal_liquida=self.renda_mensal_liquida,
            custo_familiar_mensal=self.custo_familiar_mensal,
            situacao_profissional=self.situacao_profissional, fase_de_vida=self.fase_de_vida,
            dependentes=[Dependente(**d.model_dump()) for d in self.dependentes],
            horizonte_protecao_anos=self.horizonte_protecao_anos,
            dividas=Dividas(**self.dividas.model_dump()),
            projetos=Projetos(**self.projetos.model_dump()),
            patrimonio_liquido=self.patrimonio_liquido,
            patrimonio_inventariavel=self.patrimonio_inventariavel,
            meses_de_reserva=self.meses_de_reserva,
            seguro_atual=SeguroAtual(**self.seguro_atual.model_dump()),
        )


class CompararIn(_Estrito):
    necessidade_id: Optional[str] = None
    idade: int = Field(ge=18, lt=120)
    sexo: str = Field(pattern="^[MF]$")
    fumante: bool
    capitais_escolhidos: Optional[Dict[str, float]] = None
    # False = simulação (sliders): calcula sem gravar nada no banco.
    persistir: bool = True
    # Recado livre do cliente para o especialista (tela de personalização).
    recado: Optional[str] = Field(None, max_length=1000)


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@app.get("/v1/saude")
def saude():
    return {
        "ok": True, "versao_motor": VERSAO_MOTOR, "comparador": PARAMETROS_COMPARADOR.versao,
        # O front usa estes dois para não prometer o que o sistema ainda não faz.
        "modo_demonstracao": _permitir_ficticios(),
        "notificacoes_ativas": os.environ.get("NOTIFICACOES_ATIVAS") == "1",
    }


@app.post("/v1/diagnostico")
def diagnostico(req: DiagnosticoIn):
    entrada = req.para_motor()
    try:
        entrada.validar()
    except ValueError as e:
        raise HTTPException(422, str(e))
    mapa = calcular(entrada)
    dados = req.model_dump(mode="json", exclude={"cliente_id"})
    try:
        with _conexao() as conn:
            nid, cid = repo.gravar_necessidade(conn, req.cliente_id, dados, mapa)
    except LookupError as e:
        raise HTTPException(404, str(e))
    return {"necessidade_id": nid, "cliente_id": cid, **mapa.to_dict()}


@app.get("/v1/necessidades/{necessidade_id}")
def obter_necessidade(necessidade_id: str):
    try:
        uuid.UUID(necessidade_id)
    except ValueError:
        raise HTTPException(404, "necessidade não encontrada")
    with _conexao() as conn:
        achado = repo.carregar_necessidade(conn, necessidade_id)
    if achado is None:
        raise HTTPException(404, "necessidade não encontrada")
    mapa, cliente_id = achado
    return {"necessidade_id": necessidade_id, "cliente_id": cliente_id, **mapa.to_dict()}


def _mapa_sintetico(capitais: Dict[str, float]) -> MapaDeProtecao:
    """Jornada 'Montar minha proteção': sem diagnóstico, o escolhido É a necessidade.

    Pesos iguais (1,0): sem perfil não há base para priorizar uma cobertura.
    """
    necs = [
        Necessidade(
            codigo=cod, rotulo=CODIGOS_NECESSIDADE[cod][0], unidade=CODIGOS_NECESSIDADE[cod][1],
            valor_necessario=v, valor_existente=0.0, peso=1.0, memoria={},
            justificativa="Valor escolhido diretamente pelo cliente, sem diagnóstico.",
        )
        for cod, v in capitais.items() if v > 0
    ]
    return MapaDeProtecao(
        versao_motor=VERSAO_MOTOR, protection_score=0, necessidades=necs,
        vulnerabilidade_principal=None,
    )


def _com_escolha_direta(mapa: MapaDeProtecao, escolhidos: Optional[Dict[str, float]]) -> MapaDeProtecao:
    """Cirurgias e fraturas não vêm do diagnóstico: entram na cotação se o cliente escolheu um valor."""
    if not escolhidos:
        return mapa
    presentes = {n.codigo for n in mapa.necessidades}
    extras = [
        Necessidade(
            codigo=cod, rotulo=CODIGOS_NECESSIDADE[cod][0], unidade=CODIGOS_NECESSIDADE[cod][1],
            valor_necessario=escolhidos[cod], valor_existente=0.0, peso=1.0, memoria={},
            justificativa="Valor escolhido diretamente pelo cliente.",
        )
        for cod in ESCOLHA_DIRETA if escolhidos.get(cod, 0) > 0 and cod not in presentes
    ]
    return replace(mapa, necessidades=list(mapa.necessidades) + extras) if extras else mapa


@app.post("/v1/comparar")
def comparar_endpoint(req: CompararIn):
    escolhidos = req.capitais_escolhidos
    if escolhidos is not None:
        invalidos = [k for k in escolhidos if k not in CODIGOS_NECESSIDADE]
        if invalidos:
            raise HTTPException(422, f"necessidades desconhecidas: {invalidos}")
        if any(v < 0 for v in escolhidos.values()):
            raise HTTPException(422, "capital escolhido não pode ser negativo")

    alertas_gerais: List[str] = []
    with _conexao() as conn:
        if req.necessidade_id:
            try:
                uuid.UUID(req.necessidade_id)
            except ValueError:
                raise HTTPException(404, "necessidade_id não encontrada")
            achado = repo.carregar_necessidade(conn, req.necessidade_id)
            if achado is None:
                raise HTTPException(404, "necessidade_id não encontrada")
            mapa, cliente_id = achado
            motor_versao = mapa.versao_motor
            mapa = _com_escolha_direta(mapa, escolhidos)
        else:
            if not escolhidos or not any(v > 0 for v in escolhidos.values()):
                raise HTTPException(
                    422, "sem necessidade_id, informe capitais_escolhidos com ao menos um valor > 0")
            mapa, motor_versao = _mapa_sintetico(escolhidos), None
            cliente_id = (
                str(conn.execute("INSERT INTO cliente DEFAULT VALUES RETURNING id").fetchone()[0])
                if req.persistir else None
            )
            alertas_gerais.append(
                "Sem diagnóstico: a aderência mede a qualidade das coberturas em relação ao que "
                "você escolheu, não em relação à sua necessidade real."
            )

        dev = _permitir_ficticios()
        carregados = repo.carregar_produtos(conn, dev)
        por_produto = {id(c.produto): c for c in carregados}
        cotacoes = comparar(
            [c.produto for c in carregados], mapa, req.idade, req.sexo, req.fumante,
            capitais_escolhidos=escolhidos,
        )

        opcoes, excluidos, gravar = [], [], []
        for cot in cotacoes:
            pc = por_produto[id(cot.produto)]
            nome = f"{cot.produto.seguradora} — {cot.produto.nome}"
            if not cot.produto.idade_min <= req.idade <= cot.produto.idade_max:
                excluidos.append({"produto": nome, "motivo": "Idade fora da faixa de aceitação."})
                continue
            projecao = None
            if precisa_projecao(cot):
                projecao = {a: projetar_premio(cot, req.idade, req.sexo, req.fumante, a)
                            for a in HORIZONTES_ANOS}
                if any(v is None for v in projecao.values()):
                    excluidos.append({
                        "produto": nome,
                        "motivo": "Prêmio sobe com a idade e não há tarifa para projetá-lo em "
                                  "10, 20 e 30 anos; não pode ser exibido.",
                    })
                    continue
                projecao = {a: round(v, 2) for a, v in projecao.items()}
            opcao = {
                "produto_versao_id": pc.produto_versao_id,
                "produto": {"seguradora": cot.produto.seguradora, "nome": cot.produto.nome,
                            "fonte_tarifa": cot.produto.fonte_tarifa},
                "exibivel_ao_consumidor": pc.exibivel,
                "premio_mensal": round(cot.premio_mensal_total, 2),
                "aderencia_total": round(cot.aderencia_total, 4),
                "coberturas_ausentes": cot.coberturas_ausentes,
                "itens": [
                    {"necessidade": i.necessidade, "cobertura": i.codigo_cobertura,
                     "capital_contratado": round(i.capital_contratado, 2),
                     "premio_mensal": round(i.premio_mensal, 2),
                     "aderencia": round(i.aderencia, 4), "observacoes": i.observacoes}
                    for i in cot.itens
                ],
                "projecao_premio": None if projecao is None else {
                    "ano_10": projecao[10], "ano_20": projecao[20], "ano_30": projecao[30],
                    "premissa": "Capital constante e tabela de tarifa de hoje, lida na sua idade futura.",
                },
                "alertas": cot.alertas,
            }
            opcoes.append(opcao)
            gravar.append({"cotacao": cot, "carregado": pc, "projecao": projecao,
                           "detalhe": {"itens": opcao["itens"], "alertas": cot.alertas}})

        cotacao_id = None
        if req.persistir:
            cotacao_id = repo.gravar_cotacao(
                conn, cliente_id=cliente_id, necessidade_id=req.necessidade_id,
                motor_versao=motor_versao, comparador_versao=PARAMETROS_COMPARADOR.versao,
                idade=req.idade, sexo=req.sexo, fumante=req.fumante,
                capitais_escolhidos=escolhidos, modo_dev=dev, itens=gravar, recado=(req.recado or '').strip() or None,
            )

    kept = [g["cotacao"] for g in gravar]
    ids = {id(g["cotacao"]): g["carregado"].produto_versao_id for g in gravar}
    destaques = {
        k: (ids[id(v)] if v is not None else None) for k, v in recomendados(kept).items()
    }
    if not opcoes:
        alertas_gerais.append("Nenhum produto disponível para este perfil no momento.")
    return {
        "schema_versao": SCHEMA_VERSAO, "motor_versao": motor_versao,
        "comparador_versao": PARAMETROS_COMPARADOR.versao, "cotacao_id": cotacao_id,
        "modo_demonstracao": any(not o["exibivel_ao_consumidor"] for o in opcoes),
        "opcoes": opcoes, "destaques": destaques, "excluidos": excluidos,
        "alertas_gerais": alertas_gerais,
    }


from .solicitacoes import router as _router_solicitacoes  # noqa: E402

app.include_router(_router_solicitacoes)

from .contato import router as _router_contato  # noqa: E402

app.include_router(_router_contato)
