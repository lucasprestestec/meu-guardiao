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

## Banco (PostgreSQL)

```bash
docker compose up -d                 # sobe o Postgres em localhost:54329
python db/migrate.py                 # aplica db/migrations/*.sql
python db/importar_tarifario.py docs/tarifario-modelo.csv --agravos docs/agravos-modelo.csv \n    --tarifa-versao 2026.1-t1 --fonte FICTICIA --ramo-susep A_DEFINIR
pip install "psycopg[binary]"        # necessário para os scripts e testes de banco
```

Tarifa `FICTICIA` nunca deixa a produto_versao ir para `PUBLICADO` (trigger). A API do
consumidor deve ler só de `vw_produto_exibivel`.

## API

```bash
pip install -e ".[api,dev]"
python db/seed_ficticio.py                                   # só desenvolvimento
PERMITIR_TARIFA_FICTICIA=1 uvicorn api.main:app --reload     # docs em /docs
```

Sem `PERMITIR_TARIFA_FICTICIA=1` a API só compara produtos PUBLICADOS com tarifa da
seguradora, ou seja, hoje devolve lista vazia. Não há autenticação ainda.
