# Correção v1.3.1 — texto da justificativa de morte

## O bug
Com `metodo_morte = RENDA_PERPETUA` (padrão), a justificativa afirmava que o
valor adotado "superou o método alternativo" mesmo quando o alternativo era
maior — com os dois números na mesma frase, visível ao cliente.

Exemplo real no site, renda de R$ 25.000 e filho de 6 anos:

> "...seriam necessários R$ 3.125.000 rendendo 0,8% ao mês. Esse valor superou
> o método alternativo, de sustentar os anos de dependência (R$ 5.700.000)."

3.125.000 não superou 5.700.000. O texto se contradiz sozinho.

## A correção
Substituir o bloco que monta `explica` em `necessidade_morte`, em
`motor_dor/motor.py`, por este:

```python
    # O texto precisa dizer a verdade sobre POR QUE o método foi adotado.
    # Com MAIOR_ENTRE, o adotado de fato superou o outro. Com um método
    # fixado em parâmetro, ele pode ser o MENOR dos dois — e afirmar que
    # "superou" seria falso com os dois números na mesma frase.
    escolhido_por_ser_maior = p.metodo_morte == MetodoMorte.MAIOR_ENTRE

    if metodo == "anos de dependência":
        base_txt = (
            f"Assumimos que o dependente mais novo precisa de apoio financeiro "
            f"até os {p.idade_independencia_filho} anos, o que dá "
            f"{anos:.0f} anos. Multiplicado pela renda mensal de "
            f"R$ {_brl(base)}, chega-se a R$ {_brl(metodo_a)}."
        )
        outro, outro_txt = metodo_b, "gerar a renda equivalente"
    else:
        base_txt = (
            f"Para que a família mantenha a renda de R$ {_brl(base)} por mês "
            f"sem consumir o capital, seriam necessários R$ {_brl(metodo_b)} "
            f"rendendo {_pct(p.taxa_renda_mensal)} ao mês. Essa premissa de "
            f"rentabilidade é ilustrativa, não garantida."
        )
        outro, outro_txt = metodo_a, "sustentar os anos de dependência"

    if escolhido_por_ser_maior:
        comparacao = (
            f" Esse valor superou o método alternativo, de {outro_txt} "
            f"(R$ {_brl(outro)}), por isso foi o adotado."
        )
    elif outro > capital_base:
        comparacao = (
            f" Existe um método alternativo, de {outro_txt}, que resultaria em "
            f"R$ {_brl(outro)}. Adotamos o critério de reposição de renda por "
            f"ser o mais conservador de defender."
        )
    else:
        comparacao = ""

    explica = base_txt + comparacao
```

Requer `from .parametros import MetodoMorte` no escopo da função (já existe).

## Resultado

> "...seriam necessários R$ 2.750.000 rendendo 0,8% ao mês. Essa premissa de
> rentabilidade é ilustrativa, não garantida. Existe um método alternativo, de
> sustentar os anos de dependência, que resultaria em R$ 6.336.000. Adotamos o
> critério de reposição de renda por ser o mais conservador de defender."

Nenhum número de saída muda. Só o texto. Travado pelo teste
`test_justificativa_nao_afirma_falsidade_sobre_o_metodo_alternativo`.
