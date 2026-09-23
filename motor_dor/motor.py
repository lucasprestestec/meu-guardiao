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
            h = anos_ate_idade(d.idade, p.idade_aposentadoria)
            origem = f"até a aposentadoria aos {p.idade_aposentadoria} anos"

    h = clamp(h, p.horizonte_minimo_anos, p.horizonte_maximo_anos)
    return h, origem


# ---------------------------------------------------------------------------
# Recursos próprios
# ---------------------------------------------------------------------------


def recursos_utilizaveis(d: Diagnostico, p: Parametros) -> float:
    """Parte do patrimônio que a família consegue realmente usar."""
    return max(0.0, d.patrimonio_liquido * p.liquidez_patrimonio_pct)


# ---------------------------------------------------------------------------
# Necessidades
# ---------------------------------------------------------------------------


def necessidade_morte(d: Diagnostico, p: Parametros) -> Necessidade:
    horizonte, origem_horizonte = calcular_horizonte(d, p)

    custo_sem_segurado = d.custo_familiar_mensal * (1 - p.share_consumo_do_segurado)
    renda_anual = custo_sem_segurado * 12
    vp_renda = valor_presente_anuidade(renda_anual, horizonte, p.taxa_real_desconto_aa)

    dividas = d.dividas.total_para_morte()
    projetos = d.projetos.total()
    inventario = max(0.0, d.patrimonio_inventariavel * p.custo_inventario_pct)
    recursos = recursos_utilizaveis(d, p)

    bruto = vp_renda + dividas + projetos + inventario
    valor = max(0.0, bruto - recursos)

    memoria = {
        "horizonte_anos": horizonte,
        "custo_familiar_mensal": d.custo_familiar_mensal,
        "custo_mensal_sem_segurado": custo_sem_segurado,
        "renda_anual_a_sustentar": renda_anual,
        "taxa_real_desconto_aa": p.taxa_real_desconto_aa,
        "vp_renda_familiar": vp_renda,
        "dividas": dividas,
        "projetos": projetos,
        "custo_inventario": inventario,
        "recursos_proprios_utilizaveis": recursos,
        "necessidade_bruta": bruto,
    }

    justificativa = (
        f"Na sua ausência, a família precisaria de R$ {_brl(custo_sem_segurado)} "
        f"por mês durante {horizonte:.0f} anos ({origem_horizonte}). Trazido a "
        f"valor presente a {_pct(p.taxa_real_desconto_aa)} ao ano real, isso "
        f"equivale a R$ {_brl(vp_renda)}. Somam-se dívidas de "
        f"R$ {_brl(dividas)}, projetos de R$ {_brl(projetos)} e custo estimado "
        f"de inventário de R$ {_brl(inventario)}. Descontados "
        f"R$ {_brl(recursos)} de recursos próprios efetivamente líquidos."
    )

    return Necessidade(
        codigo="NEC_MORTE",
        rotulo="Morte",
        valor_necessario=valor,
        valor_existente=d.seguro_atual.morte,
        unidade="CAPITAL",
        peso=0.0,
        memoria=memoria,
        justificativa=justificativa,
    )


def necessidade_invalidez(d: Diagnostico, p: Parametros) -> Necessidade:
    """Invalidez custa MAIS que morte: o segurado continua consumindo e gera
    custo adicional, enquanto a renda dele desaparece."""
    horizonte = clamp(
        anos_ate_idade(d.idade, p.idade_aposentadoria),
        p.horizonte_minimo_anos,
        p.horizonte_maximo_anos,
    )

    custo_com_invalidez = d.custo_familiar_mensal * (1 + p.acrescimo_custo_invalidez)
    renda_anual = custo_com_invalidez * 12
    vp_renda = valor_presente_anuidade(renda_anual, horizonte, p.taxa_real_desconto_aa)

    dividas = d.dividas.total_para_morte()
    projetos = d.projetos.total()
    adaptacao = p.custo_adaptacao_invalidez
    recursos = recursos_utilizaveis(d, p)

    bruto = vp_renda + dividas + projetos + adaptacao
    valor = max(0.0, bruto - recursos)

    memoria = {
        "horizonte_anos": horizonte,
        "custo_familiar_mensal": d.custo_familiar_mensal,
        "custo_mensal_com_invalidez": custo_com_invalidez,
        "vp_renda_familiar": vp_renda,
        "custo_adaptacao": adaptacao,
        "dividas": dividas,
        "projetos": projetos,
        "recursos_proprios_utilizaveis": recursos,
        "necessidade_bruta": bruto,
    }

    justificativa = (
        f"Numa invalidez, a renda acaba mas o custo aumenta: estimamos "
        f"R$ {_brl(custo_com_invalidez)} por mês durante {horizonte:.0f} anos, "
        f"até a idade de aposentadoria. A valor presente, R$ {_brl(vp_renda)}. "
        f"Acrescentamos R$ {_brl(adaptacao)} de adaptação inicial, mais dívidas "
        f"e projetos, e descontamos os recursos próprios líquidos."
    )

    return Necessidade(
        codigo="NEC_INVALIDEZ",
        rotulo="Invalidez",
        valor_necessario=valor,
        valor_existente=d.seguro_atual.invalidez,
        unidade="CAPITAL",
        peso=0.0,
        memoria=memoria,
        justificativa=justificativa,
    )


def necessidade_doenca_grave(d: Diagnostico, p: Parametros) -> Necessidade:
    """Capital de travessia.

    DECISÃO METODOLÓGICA EXPLÍCITA: o patrimônio próprio NÃO é descontado
    desta necessidade. O capital de doença grave existe justamente para
    evitar que a pessoa consuma reservas e venda patrimônio durante o
    tratamento. Descontá-lo assumiria como aceitável exatamente o desfecho
    que a cobertura previne. [CONFIRMAR com o especialista]
    """
    meses = p.meses_travessia_doenca_grave
    perda_renda = d.renda_mensal_liquida * p.queda_renda_tratamento * meses
    tratamento = p.reserva_tratamento_nao_coberto
    valor = perda_renda + tratamento

    memoria = {
        "meses_travessia": float(meses),
        "renda_mensal_liquida": d.renda_mensal_liquida,
        "queda_renda_esperada": p.queda_renda_tratamento,
        "perda_de_renda_no_periodo": perda_renda,
        "reserva_tratamento_nao_coberto": tratamento,
        "patrimonio_descontado": 0.0,
    }

    justificativa = (
        f"Um diagnóstico grave costuma significar {meses} meses de renda "
        f"reduzida. Estimamos perda de R$ {_brl(perda_renda)} no período, mais "
        f"R$ {_brl(tratamento)} para o que o plano de saúde não cobre. O "
        f"patrimônio próprio não é descontado aqui de propósito: o objetivo "
        f"desta cobertura é não precisar consumir reservas nem vender bens "
        f"durante o tratamento."
    )

    return Necessidade(
        codigo="NEC_DOENCA_GRAVE",
        rotulo="Doenças graves",
        valor_necessario=valor,
        valor_existente=d.seguro_atual.doenca_grave,
        unidade="CAPITAL",
        peso=0.0,
        memoria=memoria,
        justificativa=justificativa,
    )


def necessidade_renda(d: Diagnostico, p: Parametros) -> Necessidade:
    """Diária de incapacidade temporária."""
    diaria = (d.renda_mensal_liquida / p.dit_dias_mes) * p.dit_teto_pct_renda
    meses_reserva = d.meses_de_reserva

    memoria = {
        "renda_mensal_liquida": d.renda_mensal_liquida,
        "dias_mes": float(p.dit_dias_mes),
        "teto_pct_renda": p.dit_teto_pct_renda,
        "meses_de_reserva_declarados": meses_reserva,
    }

    justificativa = (
        f"Se você ficasse temporariamente impedido de trabalhar, a diária "
        f"equivalente à sua renda seria de R$ {_brl(diaria, 2)}. Sua reserva "
        f"sustentaria o padrão financeiro por aproximadamente "
        f"{meses_reserva:.0f} meses."
    )

    return Necessidade(
        codigo="NEC_RENDA",
        rotulo="Proteção de renda (diária)",
        valor_necessario=diaria,
        valor_existente=d.seguro_atual.dit_diaria,
        unidade="DIARIA",
        peso=0.0,
        memoria=memoria,
        justificativa=justificativa,
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

    # Reserva robusta reduz a urgência da proteção de renda, não a necessidade.
    if p.dit_meses_reserva_confortavel > 0:
        fator = 1.0 - 0.5 * clamp(
            d.meses_de_reserva / p.dit_meses_reserva_confortavel, 0.0, 1.0
        )
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
    if d.seguro_atual.dit_diaria > (d.renda_mensal_liquida / p.dit_dias_mes) * 1.2:
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
