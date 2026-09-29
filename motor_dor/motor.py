"""
Motor DOR$ v1.0 — cálculo determinístico de necessidade de proteção.

PRINCÍPIO: nenhuma linha deste arquivo chama IA, rede, banco ou relógio.
Mesma entrada, mesma saída, para sempre. A IA entra DEPOIS, apenas para
traduzir a memória de cálculo em linguagem humana.

Toda necessidade devolvida carrega a memória de cálculo que a gerou, para
que qualquer número possa ser explicado linha a linha a um cliente, a um
auditor ou a um juiz.
"""

from __future__ import annotations

from typing import Dict, List, Optional, Tuple

from .financeiro import anos_ate_idade, clamp, valor_presente_anuidade
from .modelos import (
    Diagnostico,
    FaseDeVida,
    MapaDeProtecao,
    Necessidade,
)
from .parametros import (
    FASES_DE_VIDA,
    PARAMETROS_V1,
    PERFIS_PROFISSIONAIS,
    Parametros,
)

# ---------------------------------------------------------------------------
# Formatação
# ---------------------------------------------------------------------------


def _brl(valor: float, casas: int = 0) -> str:
    """Formata em padrão brasileiro SEM tocar na pontuação do texto ao redor.

    O bug clássico aqui é aplicar .replace(",", ".") na frase inteira, o que
    destrói as vírgulas gramaticais. Por isso a troca acontece apenas dentro
    desta função, sobre o número isolado.
    """
    bruto = f"{valor:,.{casas}f}"
    return bruto.replace(",", "\x00").replace(".", ",").replace("\x00", ".")


def _pct(fracao: float) -> str:
    """Percentual em padrão brasileiro: 0.03 -> '3,0%'."""
    return f"{fracao * 100:.1f}".replace(".", ",") + "%"


def _anos(n: int) -> str:
    return "1 ano" if n == 1 else f"{n} anos"


# ---------------------------------------------------------------------------
# Horizonte
# ---------------------------------------------------------------------------


def calcular_horizonte(d: Diagnostico, p: Parametros) -> Tuple[float, str]:
    """Por quantos anos a renda da família precisa ser sustentada.

    Ordem de precedência:
      1. O horizonte que o próprio cliente escolheu.
      2. Se há dependentes: até o mais novo atingir independência.
      3. Caso contrário: até a aposentadoria do segurado.
    """
    if d.horizonte_protecao_anos is not None:
        h = float(d.horizonte_protecao_anos)
        origem = "escolhido pelo cliente"
    else:
        dependentes = [x for x in d.dependentes if x.financeiramente_dependente]
        if dependentes:
            mais_novo = min(x.idade for x in dependentes)
            h = anos_ate_idade(mais_novo, p.idade_independencia_filho)
            origem = (
                f"até o dependente mais novo ({_anos(mais_novo)}) atingir "
                f"{p.idade_independencia_filho} anos"
            )
        else:
            h = 0.0
            origem = "sem dependentes financeiros"

    return clamp(h, 0.0, 60.0), origem


# ---------------------------------------------------------------------------
# Recursos próprios
# ---------------------------------------------------------------------------


def recursos_utilizaveis(d: Diagnostico, p: Parametros) -> float:
    """Patrimônio considerado disponível. Só é usado se abate_patrimonio=True."""
    return max(0.0, d.patrimonio_liquido)


# ---------------------------------------------------------------------------
# Necessidades
# ---------------------------------------------------------------------------


def _base(d, p) -> float:
    from .parametros import BaseDeCalculo
    if p.base_calculo == BaseDeCalculo.RENDA:
        return d.renda_mensal_liquida
    return d.custo_familiar_mensal


def _capital_renda_perpetua(mensal: float, p) -> float:
    """Capital que, aplicado à taxa ilustrativa, gera a renda mensal."""
    if p.taxa_renda_mensal <= 0:
        raise ValueError("taxa_renda_mensal deve ser positiva")
    return mensal / p.taxa_renda_mensal


def _anos_de_dependencia(d, p) -> float:
    dependentes = [x for x in d.dependentes if x.financeiramente_dependente]
    if not dependentes:
        return 0.0
    mais_novo = min(x.idade for x in dependentes)
    return max(0.0, float(p.idade_independencia_filho - mais_novo))


def necessidade_morte(d: Diagnostico, p: Parametros) -> Necessidade:
    from .parametros import MetodoMorte

    base = _base(d, p)
    anos = _anos_de_dependencia(d, p)

    metodo_a = anos * 12 * base                      # sustentar até a independência
    metodo_b = _capital_renda_perpetua(base, p)      # gerar renda equivalente

    if p.metodo_morte == MetodoMorte.ANOS_DEPENDENCIA:
        capital_base, metodo = metodo_a, "anos de dependência"
    elif p.metodo_morte == MetodoMorte.RENDA_PERPETUA:
        capital_base, metodo = metodo_b, "renda perpétua"
    else:
        if metodo_a >= metodo_b:
            capital_base, metodo = metodo_a, "anos de dependência"
        else:
            capital_base, metodo = metodo_b, "renda perpétua"

    dividas = d.dividas.total_para_morte() if p.soma_dividas_na_morte else 0.0
    projetos = d.projetos.total() if p.soma_projetos_na_morte else 0.0
    inventario = max(0.0, d.patrimonio_inventariavel * p.custo_inventario_pct)
    patrimonio = recursos_utilizaveis(d, p) if p.abate_patrimonio else 0.0

    bruto = capital_base + dividas + projetos + inventario
    valor = max(0.0, bruto - patrimonio)

    memoria = {
        "base_mensal": base,
        "anos_de_dependencia": anos,
        "metodo_a_anos_dependencia": metodo_a,
        "metodo_b_renda_perpetua": metodo_b,
        "taxa_renda_mensal": p.taxa_renda_mensal,
        "capital_base_adotado": capital_base,
        "dividas": dividas,
        "projetos": projetos,
        "custo_inventario": inventario,
        "pct_inventario": p.custo_inventario_pct,
        "patrimonio_abatido": patrimonio,
        "necessidade_bruta": bruto,
    }

    if metodo == "anos de dependência":
        explica = (
            f"Assumimos que o dependente mais novo precisa de apoio financeiro "
            f"até os {p.idade_independencia_filho} anos, o que dá "
            f"{anos:.0f} anos. Multiplicado pela renda mensal de "
            f"R$ {_brl(base)}, chega-se a R$ {_brl(metodo_a)}. Esse valor "
            f"superou o método alternativo, de gerar renda equivalente "
            f"(R$ {_brl(metodo_b)}), por isso foi o adotado."
        )
    else:
        explica = (
            f"Para que a família mantenha a renda de R$ {_brl(base)} por mês "
            f"sem consumir o capital, seriam necessários R$ {_brl(metodo_b)} "
            f"rendendo {_pct(p.taxa_renda_mensal)} ao mês. Essa premissa de "
            f"rentabilidade é ilustrativa, não garantida. Esse valor superou o "
            f"método alternativo, de sustentar os anos de dependência "
            f"(R$ {_brl(metodo_a)})."
        )

    justificativa = (
        explica
        + f" Somam-se dívidas de R$ {_brl(dividas)}, projetos de "
        f"R$ {_brl(projetos)} e custo de inventário de R$ {_brl(inventario)}, "
        f"estimado em {_pct(p.custo_inventario_pct)} do patrimônio "
        f"inventariável — média brasileira de ITCMD, honorários e custas, que "
        f"varia conforme o estado e a complexidade do espólio."
    )

    return Necessidade(
        codigo="NEC_MORTE", rotulo="Morte", valor_necessario=valor,
        valor_existente=d.seguro_atual.morte if p.abate_seguro_existente else 0.0,
        unidade="CAPITAL", peso=0.0, memoria=memoria, justificativa=justificativa,
    )


def necessidade_invalidez(d: Diagnostico, p: Parametros) -> Necessidade:
    base = _base(d, p)
    valor = _capital_renda_perpetua(base, p)

    memoria = {
        "base_mensal": base,
        "taxa_renda_mensal": p.taxa_renda_mensal,
        "capital_gerador_de_renda": valor,
    }
    justificativa = (
        f"Numa invalidez a renda desaparece, mas a pessoa continua viva e as "
        f"despesas tendem a aumentar. Para repor R$ {_brl(base)} por mês sem "
        f"consumir o capital, seriam necessários R$ {_brl(valor)} rendendo "
        f"{_pct(p.taxa_renda_mensal)} ao mês. Premissa de rentabilidade "
        f"ilustrativa, não garantida."
    )

    return Necessidade(
        codigo="NEC_INVALIDEZ", rotulo="Invalidez", valor_necessario=valor,
        valor_existente=d.seguro_atual.invalidez if p.abate_seguro_existente else 0.0,
        unidade="CAPITAL", peso=0.0, memoria=memoria, justificativa=justificativa,
    )


def necessidade_doenca_grave(d: Diagnostico, p: Parametros) -> Necessidade:
    """Patrimônio NÃO é descontado: a cobertura existe para não consumi-lo."""
    from .parametros import BaseDeCalculo

    base = (
        d.renda_mensal_liquida
        if p.base_calculo_doenca_grave == BaseDeCalculo.RENDA
        else d.custo_familiar_mensal
    )
    meses = p.meses_doenca_grave
    valor = base * meses

    memoria = {
        "base_mensal": base,
        "meses": float(meses),
        "patrimonio_descontado": 0.0,
    }
    justificativa = (
        f"Assumimos {meses} meses como horizonte de um tratamento grave e da "
        f"reorganização financeira que ele exige. Sobre a base mensal de "
        f"R$ {_brl(base)}, isso dá R$ {_brl(valor)}. O plano de saúde paga "
        f"hospital e médico; este capital compra liberdade de escolha e evita "
        f"que a reserva vire a primeira fonte de recursos. Por isso o "
        f"patrimônio próprio não é descontado aqui."
    )

    return Necessidade(
        codigo="NEC_DOENCA_GRAVE", rotulo="Doenças graves", valor_necessario=valor,
        valor_existente=d.seguro_atual.doenca_grave if p.abate_seguro_existente else 0.0,
        unidade="CAPITAL", peso=0.0, memoria=memoria, justificativa=justificativa,
    )


def necessidade_renda(d: Diagnostico, p: Parametros) -> Necessidade:
    """Diária de internação / incapacidade temporária: renda mensal / 30."""
    diaria = d.renda_mensal_liquida / p.dias_mes

    memoria = {
        "renda_mensal_liquida": d.renda_mensal_liquida,
        "dias_mes": float(p.dias_mes),
        "meses_de_reserva_declarados": d.meses_de_reserva,
    }
    justificativa = (
        f"A diária é dimensionada para repor a renda: R$ {_brl(d.renda_mensal_liquida)} "
        f"por mês dividido por {p.dias_mes} dias dá R$ {_brl(diaria, 2)} por dia. "
        f"Sua reserva sustentaria o padrão financeiro por aproximadamente "
        f"{d.meses_de_reserva:.0f} meses."
    )

    return Necessidade(
        codigo="NEC_RENDA", rotulo="Diária (internação / afastamento)",
        valor_necessario=diaria,
        valor_existente=d.seguro_atual.dit_diaria if p.abate_seguro_existente else 0.0,
        unidade="DIARIA", peso=0.0, memoria=memoria, justificativa=justificativa,
    )


# ---------------------------------------------------------------------------
# Pesos
# ---------------------------------------------------------------------------


def _inferir_fase_de_vida(d: Diagnostico) -> Optional[FaseDeVida]:
    if d.fase_de_vida is not None:
        return d.fase_de_vida
    dependentes = [x for x in d.dependentes if x.financeiramente_dependente]
    if not dependentes:
        return None  # sem informação suficiente: não inventa
    mais_novo = min(x.idade for x in dependentes)
    if mais_novo < 12:
        return FaseDeVida.FILHOS_PEQUENOS
    if mais_novo < 18:
        return FaseDeVida.FILHOS_ADOLESCENTES
    return FaseDeVida.NINHO_VAZIO


def calcular_pesos(d: Diagnostico, p: Parametros) -> Dict[str, float]:
    """Pesos determinam PRIORIDADE, nunca CAPITAL.

    Um dentista não precisa de mais capital de invalidez que um advogado
    com a mesma renda; ele precisa que a invalidez seja tratada como
    prioridade maior, porque a probabilidade e o impacto são outros.
    """
    pesos = dict(p.peso_base)

    perfil = PERFIS_PROFISSIONAIS.get(d.situacao_profissional.value, {})
    for codigo, mult in perfil.items():
        pesos[codigo] = pesos.get(codigo, 1.0) * mult

    fase = _inferir_fase_de_vida(d)
    if fase is not None:
        for codigo, mult in FASES_DE_VIDA.get(fase.value, {}).items():
            pesos[codigo] = pesos.get(codigo, 1.0) * mult

    # Reserva robusta reduz a URGÊNCIA da proteção de renda, não a necessidade.
    fator = 1.0 - 0.5 * clamp(d.meses_de_reserva / 6.0, 0.0, 1.0)
    pesos["NEC_RENDA"] = pesos.get("NEC_RENDA", 1.0) * fator

    return {k: round(v, 6) for k, v in pesos.items()}


# ---------------------------------------------------------------------------
# Alertas
# ---------------------------------------------------------------------------


def gerar_alertas(d: Diagnostico, p: Parametros) -> List[str]:
    alertas: List[str] = []

    if d.custo_familiar_mensal > d.renda_mensal_liquida:
        alertas.append(
            "O custo familiar declarado supera a renda líquida. Confirme os "
            "valores antes de usar o resultado."
        )
    if d.dividas.imobiliaria > 0 and not d.dividas.imobiliaria_tem_prestamista:
        alertas.append(
            "Financiamento imobiliário informado sem seguro prestamista. "
            "Confirme, porque o MIP costuma ser obrigatório e quitaria o "
            "saldo, reduzindo a necessidade de capital de morte."
        )
    if d.patrimonio_inventariavel > 0 and d.patrimonio_liquido == 0:
        alertas.append(
            "Há patrimônio inventariável mas nenhum recurso líquido "
            "declarado. A família pode ficar sem caixa até o fim do inventário."
        )
    if d.seguro_atual.dit_diaria > (d.renda_mensal_liquida / p.dias_mes) * 1.2:
        alertas.append(
            "A diária já contratada supera a renda diária declarada. "
            "Seguradoras costumam recusar sinistro nessa situação."
        )
    if not d.dependentes and d.fase_de_vida in (
        FaseDeVida.FILHOS_PEQUENOS,
        FaseDeVida.FILHOS_ADOLESCENTES,
    ):
        alertas.append(
            "Fase de vida indica filhos, mas nenhum dependente foi informado."
        )
    return alertas


# ---------------------------------------------------------------------------
# Motor
# ---------------------------------------------------------------------------


def calcular(
    diagnostico: Diagnostico, parametros: Parametros = PARAMETROS_V1
) -> MapaDeProtecao:
    """Ponto de entrada único do Motor DOR$."""
    diagnostico.validar()
    p = parametros

    pesos = calcular_pesos(diagnostico, p)

    brutas = [
        necessidade_morte(diagnostico, p),
        necessidade_invalidez(diagnostico, p),
        necessidade_doenca_grave(diagnostico, p),
        necessidade_renda(diagnostico, p),
    ]

    necessidades = [
        Necessidade(
            codigo=n.codigo,
            rotulo=n.rotulo,
            valor_necessario=n.valor_necessario,
            valor_existente=n.valor_existente,
            unidade=n.unidade,
            peso=pesos.get(n.codigo, 1.0),
            memoria=n.memoria,
            justificativa=n.justificativa,
        )
        for n in brutas
    ]

    soma_pesos = sum(n.peso for n in necessidades)
    if soma_pesos <= 0:
        score = 0
    else:
        score = round(
            sum(n.peso * n.cobertura for n in necessidades) / soma_pesos * 100
        )
    score = int(clamp(score, 0, 100))

    descobertas = [n for n in necessidades if n.gap > 0]
    if descobertas:
        pior = max(descobertas, key=lambda n: n.peso * (1 - n.cobertura))
        vulnerabilidade = pior.codigo
    else:
        vulnerabilidade = None

    return MapaDeProtecao(
        versao_motor=p.versao,
        protection_score=score,
        necessidades=necessidades,
        vulnerabilidade_principal=vulnerabilidade,
        alertas=gerar_alertas(diagnostico, p),
    )
