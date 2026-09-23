# Changelog — Motor DOR$

Versionamento semântico. **Regra imutável:** qualquer alteração que mude um
número de saída exige nova versão em `parametros.VERSAO_MOTOR` e uma entrada
aqui. Cotação gravada sob a versão X precisa ser recalculável com a versão X
para sempre.

## [1.0.0] — 2026-09-22

Primeira versão executável do motor determinístico.

### Adicionado
- Cálculo de quatro necessidades: morte, invalidez, doenças graves e renda (DIT).
- Horizonte de proteção derivado do dependente mais novo ou da aposentadoria,
  com precedência para a escolha do cliente.
- Memória de cálculo em toda necessidade: todo número é reconstruível.
- Pesos por perfil profissional e fase de vida — alteram **prioridade**,
  nunca **capital**.
- Protection Score ponderado (0 a 100).
- Alertas determinísticos (prestamista, diária acima da renda, custo > renda).
- 36 testes: financeiros, invariantes, pesos, validação e golden tests.

### Decisões metodológicas registradas
- **Invalidez ≥ morte sempre.** Na invalidez o segurado continua consumindo e
  gera custo adicional. Travado por invariante em teste.
- **Doença grave não desconta patrimônio.** A cobertura existe para evitar o
  consumo de reservas e a venda de bens; descontá-los assumiria como aceitável
  o desfecho que a cobertura previne. [CONFIRMAR com o especialista]
- **Financiamento imobiliário com prestamista não entra na necessidade de
  morte**, porque o MIP quita o saldo.
- **Custo de inventário entra na necessidade de morte** como percentual do
  patrimônio inventariável (ITCMD + custas). Parâmetro único; varia por estado.

### Pendente de calibração
Todos os parâmetros marcados `[CALIBRAR]` em `parametros.py`, especialmente:
taxa real de desconto, parcela de consumo do segurado, custo de inventário,
acréscimo de custo na invalidez e reserva de tratamento não coberto.
