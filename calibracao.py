"""Confronta o Motor com os 5 casos reais do histórico do especialista.

Cada caso traz o que FOI EFETIVAMENTE PROPOSTO ao cliente. A distância entre
a necessidade calculada e o capital proposto é o dado mais importante aqui:
mostra o tamanho do ajuste comercial que hoje é feito de cabeça.
"""
from motor_dor import (Dependente, Diagnostico, Dividas, Projetos,
                       SeguroAtual, SituacaoProfissional, calcular)
from motor_dor.parametros import PARAMETROS_1PCT

def brl(v): return f"{v:,.0f}".replace(",", ".")

CASOS = [
    ("A — provedor 39a, filha 7a, patrimônio alto",
     Diagnostico(idade=39, renda_mensal_liquida=30_000, custo_familiar_mensal=30_000,
                 dependentes=[Dependente(idade=7)], patrimonio_inventariavel=5_000_000),
     {"NEC_MORTE": 2_200_000}),
    ("B — médica, filha 5a, alta renda",
     Diagnostico(idade=38, renda_mensal_liquida=45_000, custo_familiar_mensal=40_000,
                 dependentes=[Dependente(idade=5)]),
     {"NEC_MORTE": 2_500_000, "NEC_INVALIDEZ": 5_000_000,
      "NEC_DOENCA_GRAVE": 1_080_000, "NEC_RENDA": 1_500}),
    ("C — dentista 55a, sem reserva",
     Diagnostico(idade=55, renda_mensal_liquida=20_000, custo_familiar_mensal=20_000,
                 situacao_profissional=SituacaoProfissional.MANUAL_ESPECIALIZADO),
     {"NEC_MORTE": 300_000, "NEC_INVALIDEZ": 1_500_000,
      "NEC_DOENCA_GRAVE": 60_000, "NEC_RENDA": 600}),
    ("D — casal jovem, filho pequeno",
     Diagnostico(idade=33, renda_mensal_liquida=14_000, custo_familiar_mensal=11_000,
                 dependentes=[Dependente(idade=2)]),
     {"NEC_MORTE": 600_000, "NEC_DOENCA_GRAVE": 336_000, "NEC_RENDA": 500}),
    ("E — profissional 45a, aposentadoria aos 60",
     Diagnostico(idade=45, renda_mensal_liquida=20_000, custo_familiar_mensal=15_000,
                 patrimonio_liquido=750_000),
     {"NEC_INVALIDEZ": 1_875_000}),
]

print(f"{'Caso / cobertura':<44}{'Motor':>14}{'Proposto':>14}{'Razão':>9}")
print("=" * 81)
for nome, diag, proposto in CASOS:
    print(nome)
    m = calcular(diag)
    for n in m.necessidades:
        if n.codigo not in proposto:
            continue
        p = proposto[n.codigo]
        razao = n.valor_necessario / p if p else 0
        print(f"  {n.rotulo:<42}{brl(n.valor_necessario):>14}{brl(p):>14}{razao:>8.1f}x")
    print()

print("\nSensibilidade da taxa de renda passiva (0,8% vs 1,0% a.m.)")
print("-" * 81)
for nome, diag, _ in CASOS:
    a = calcular(diag).por_codigo("NEC_INVALIDEZ").valor_necessario
    b = calcular(diag, PARAMETROS_1PCT).por_codigo("NEC_INVALIDEZ").valor_necessario
    print(f"  {nome[:42]:<44}{brl(a):>14}{brl(b):>14}{a/b:>8.2f}x")
