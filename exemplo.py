"""Demonstração: três personas, um motor."""
import json
from motor_dor import (Dependente, Diagnostico, Dividas, FaseDeVida, Projetos,
                       SeguroAtual, SituacaoProfissional, calcular)

PERSONAS = {
    "Recém-pai, 34 anos, CLT": Diagnostico(
        idade=34, renda_mensal_liquida=22_000, custo_familiar_mensal=15_000,
        situacao_profissional=SituacaoProfissional.CLT,
        dependentes=[Dependente(idade=1), Dependente(idade=34)],
        dividas=Dividas(imobiliaria=450_000, imobiliaria_tem_prestamista=True),
        projetos=Projetos(educacao_filhos=400_000),
        patrimonio_liquido=180_000, patrimonio_inventariavel=700_000,
        meses_de_reserva=4, seguro_atual=SeguroAtual(morte=500_000)),
    "Dentista, 41 anos": Diagnostico(
        idade=41, renda_mensal_liquida=35_000, custo_familiar_mensal=20_000,
        situacao_profissional=SituacaoProfissional.MANUAL_ESPECIALIZADO,
        dependentes=[Dependente(idade=9)], dividas=Dividas(empresarial=300_000),
        patrimonio_liquido=400_000, meses_de_reserva=2,
        seguro_atual=SeguroAtual(morte=1_000_000, invalidez=300_000)),
    "Jovem solteiro, 27 anos, autônomo": Diagnostico(
        idade=27, renda_mensal_liquida=12_000, custo_familiar_mensal=6_000,
        situacao_profissional=SituacaoProfissional.AUTONOMO,
        fase_de_vida=FaseDeVida.JOVEM_SEM_DEPENDENTES,
        patrimonio_liquido=60_000, meses_de_reserva=5),
}

def brl(v): return f"R$ {v:,.0f}".replace(",", ".")

for nome, d in PERSONAS.items():
    m = calcular(d)
    print("=" * 74); print(nome)
    print(f"Protection Score: {m.protection_score}/100   "
          f"| Vulnerabilidade principal: {m.vulnerabilidade_principal}")
    print("-" * 74)
    print(f"{'Cobertura':<28}{'Necessário':>14}{'Já tem':>14}{'Gap':>14}{'Peso':>6}")
    for n in m.necessidades:
        f = (lambda v: f"R$ {v:,.0f}/dia".replace(",", ".")) if n.unidade == "DIARIA" else brl
        print(f"{n.rotulo:<28}{f(n.valor_necessario):>14}"
              f"{f(n.valor_existente):>14}{f(n.gap):>14}{n.peso:>6.2f}")
    pior = m.por_codigo(m.vulnerabilidade_principal)
    print(f"\n→ {pior.justificativa}")
    for a in m.alertas: print(f"  [alerta] {a}")
    print()
