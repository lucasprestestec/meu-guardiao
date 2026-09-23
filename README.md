# Motor DOR$

Cálculo determinístico de necessidade de proteção financeira.

```bash
python3 -m pytest tests/ -q     # 36 testes
python3 exemplo.py              # três personas, um motor
```

## Contrato

Entrada: `Diagnostico`. Saída: `MapaDeProtecao`.

```python
from motor_dor import Diagnostico, calcular
mapa = calcular(Diagnostico(idade=34, renda_mensal_liquida=22_000,
                            custo_familiar_mensal=15_000))
mapa.protection_score            # 0 a 100
mapa.vulnerabilidade_principal   # código da necessidade mais descoberta
mapa.to_dict()                   # serializável, com memória de cálculo
```

## Regras estruturais

1. **Zero IA no cálculo.** Nenhuma chamada de rede, banco, relógio ou modelo.
   Mesma entrada, mesma saída, para sempre. A IA entra depois, só para
   traduzir a memória de cálculo em linguagem humana.
2. **Nenhum número mágico fora de `parametros.py`.**
3. **Toda necessidade carrega sua memória de cálculo.** O teste
   `test_memoria_de_calculo_completa` prova que o valor final é reconstruível
   a partir dela.
4. **Pesos mudam prioridade, não capital.** Um dentista não precisa de mais
   capital de invalidez que um advogado de mesma renda; precisa que a
   invalidez seja tratada como prioridade maior.
5. **Mudou número de saída, mudou versão.** Ver `CHANGELOG.md`.

## Estrutura

```
motor_dor/parametros.py   constantes versionadas  [único lugar com números]
motor_dor/modelos.py      entrada e saída          [não calcula nada]
motor_dor/financeiro.py   VP de anuidade etc.      [funções puras]
motor_dor/motor.py        as quatro necessidades   [núcleo]
tests/test_motor.py       36 testes
exemplo.py                demonstração
```

## Próximos passos

- Calibrar os parâmetros `[CALIBRAR]` contra casos reais do especialista.
- Confirmar a decisão metodológica de doenças graves (ver CHANGELOG).
- Ligar ao DOR$ Insurance Schema: as saídas `NEC_*` são as chaves
  `necessidade_atendida` do dicionário canônico de coberturas.
