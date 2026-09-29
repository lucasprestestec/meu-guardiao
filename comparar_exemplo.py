"""Demonstração do comparador. TARIFAS FICTÍCIAS."""
from motor_dor import Dependente, Diagnostico, SituacaoProfissional, calcular
from motor_dor.catalogo_ficticio import CATALOGO
from motor_dor.comparador import comparar, recomendados

def brl(v): return f"R$ {v:,.0f}".replace(",", ".")

cliente = Diagnostico(
    idade=38, renda_mensal_liquida=25_000, custo_familiar_mensal=18_000,
    situacao_profissional=SituacaoProfissional.MANUAL_ESPECIALIZADO,
    dependentes=[Dependente(idade=6)])
IDADE, SEXO, FUMA = 38, "M", False

mapa = calcular(cliente)
print(f"Protection Score: {mapa.protection_score}/100 | "
      f"Vulnerabilidade: {mapa.vulnerabilidade_principal}\n")
print("NECESSIDADE CALCULADA")
for n in mapa.necessidades:
    u = "/dia" if n.unidade == "DIARIA" else ""
    print(f"  {n.rotulo:<38}{brl(n.valor_necessario)}{u}")

cot = comparar(CATALOGO, mapa, IDADE, SEXO, FUMA)
print(f"\n{'PRODUTO':<42}{'ADERÊNCIA':>11}{'PRÊMIO/MÊS':>14}")
print("=" * 67)
for c in cot:
    nome = f"{c.produto.seguradora.split(' (')[0]} — {c.produto.nome}"
    print(f"{nome:<42}{c.aderencia_total:>10.0%}{brl(c.premio_mensal_total):>14}")
    for i in c.itens:
        cap = "—" if not i.codigo_cobertura else (
            f"{brl(i.capital_contratado)}" if i.capital_contratado >= 1000
            else f"{brl(i.capital_contratado)}/dia")
        print(f"   {i.necessidade:<20}{(i.codigo_cobertura or 'AUSENTE'):<12}"
              f"{cap:>16}{i.aderencia:>9.0%}")
        for o in i.observacoes[:2]:
            print(f"      · {o}")
    print()

r = recomendados(cot)
print("DESTAQUES")
for k, v in r.items():
    print(f"  {k:<16}{v.produto.nome:<22}{brl(v.premio_mensal_total):>12}"
          f"{v.aderencia_total:>8.0%}")
print("\n" + cot[0].alertas[-1])
