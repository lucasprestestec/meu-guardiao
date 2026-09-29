# Handoff técnico — Meu Guardião

Para quem vai construir o MVP. Este documento diz o que está decidido, o que é
sua decisão, e o que você pode programar hoje mesmo sem depender de ninguém.

---

## 1. O que já existe e não precisa ser refeito

| Peça | Estado | Onde |
|---|---|---|
| Motor de cálculo de necessidade | v1.3.0, 48 testes | `motor_dor/` |
| Comparador por aderência | funcionando | `motor_dor/comparador.py` |
| Insurance Schema (dicionário de coberturas) | especificado + DDL PostgreSQL | `dor-insurance-schema-v1.md`, `.sql` |
| Protótipo navegável das 3 jornadas | no ar | link enviado à parte |
| Catálogo de produtos fictício | funcionando | `motor_dor/catalogo_ficticio.py` |

**O motor está fechado.** As fórmulas foram extraídas do método real de um
corretor com 600 clientes e calibradas contra cinco vendas reais. Elas parecem
arbitrárias de fora e não são: `renda ÷ 0,8% ao mês` para morte e invalidez,
`24 × renda` para doenças graves, `renda ÷ 30` para a diária, `15%` do
patrimônio inventariável para custo de inventário. Cada uma está justificada no
`CHANGELOG.md`.

Se algo no motor parecer errado, **é conversa antes de mudança**. Toda
alteração que muda um número de saída exige nova versão. Uma cotação gravada
sob a versão 1.3.0 precisa ser recalculável com a 1.3.0 daqui a dez anos,
inclusive dentro de um processo judicial.

Tudo o mais — stack, framework, hospedagem, banco, fila, front — está aberto e
é sua decisão.

---

## 2. O que você pode programar hoje, sem tarifário

Esse é o ponto principal deste documento. A falta de tarifário **não bloqueia
nada** além dos números finais, porque os formatos de entrada e saída já estão
definidos.

### Contrato do motor

`docs/contrato-motor.json` tem um request e um response reais, gerados pelo
motor rodando. Construa o front contra esse formato. Quando plugar o motor de
verdade, encaixa.

```
POST /v1/diagnostico   → recebe as respostas do questionário
                       → devolve protection_score, 4 necessidades, gap,
                         peso, memória de cálculo e justificativa em
                         linguagem humana
```

Cada necessidade vem com `memoria`, um objeto com todos os números
intermediários. O `test_memoria_de_calculo_completa` prova que o valor final é
reconstruível a partir dela. Isso não é decoração: é o que permite explicar
qualquer número a um cliente, a um auditor ou a um juiz.

### Contrato do comparador

`docs/contrato-comparador.json`, também real.

```
POST /v1/comparar      → recebe os capitais escolhidos pelo cliente
                       → devolve produtos ordenados por aderência, com
                         prêmio, capital contratado por cobertura,
                         observações e alertas
```

### Formato do tarifário

`docs/tarifario-modelo.csv` e `docs/agravos-modelo.csv` definem como uma tabela
de seguradora entra no sistema. Construa o importador contra esse formato. Toda
seguradora manda a tabela em layout diferente; a conversão para este formato é
trabalho manual de backoffice, feito uma vez por seguradora.

A chave de tarifa é sempre:
`(cobertura, faixa etária, sexo, fumante, classe de risco)`.

Capital usa `taxa_por_mil` — prêmio mensal por mil reais de capital. Diária usa
`premio_por_unidade` — prêmio mensal por real de diária. Exatamente uma das
duas é preenchida por linha; a outra fica vazia.

### Trava de segurança obrigatória

Todo produto carrega `fonte_tarifa`. Enquanto for `FICTICIA`, ele **não pode
aparecer para o consumidor**. Já está travado por teste
(`test_tarifa_ficticia_sempre_alerta`) e precisa continuar travado em produção.
Exibir preço inventado como se fosse real é problema regulatório, não bug.

---

## 3. Regras de negócio que não são negociáveis

Estas nasceram de erro conhecido do setor. Todas devem virar constraint,
trigger ou teste — não comentário.

1. **`1 cliente → N apólices → N seguradoras`** no modelo de dados, desde o
   dia 1, mesmo que o MVP venda uma apólice por vez. Retrofit disso depois é
   caro.
2. **Produto, condições gerais e tarifa são versionados separadamente.** Tarifa
   muda muito mais rápido que condição geral. Toda cotação grava as duas
   versões.
3. **Nenhum produto vai ao ar com mapeamento de cobertura não verificado.** O
   que a seguradora chama de "invalidez" precisa ter sido lido nas condições
   gerais e classificado, com página e cláusula registradas.
4. **Doenças graves não existe sem o rol.** Duas apólices de R$ 500 mil em
   doenças graves, uma com 10 doenças e outra com 40, não são comparáveis.
5. **Produto com reajuste por faixa etária só pode ser exibido com projeção de
   prêmio em 10, 20 e 30 anos.** Mostrar só o preço do ano 1 é propaganda, não
   informação.
6. **IFPD, ILP, IPT de lista fechada e IPA não são a mesma cobertura.** São
   quatro coisas diferentes com nomes parecidos, e é o erro mais caro que um
   comparador pode cometer.
7. **Nada de cartão bruto ou CVV no nosso banco.** Pagamento por token.
8. **DPS é dado sensível de saúde.** Base legal, retenção e trilha de
   consentimento definidas desde o desenho.
9. **A IA não decide capital segurado.** Ela explica o que o motor
   determinístico calculou. Nunca o contrário.

---

## 4. A jornada, resumida

Três portas convergentes:

- **Descobrir quanto preciso** — diagnóstico → motor → Mapa de Proteção com
  Protection Score → personalização por sliders → comparação.
- **Montar minha proteção** — sliders direto → comparação. É a jornada mais
  curta e deve continuar sendo.
- **Já tenho seguro** — informa ou envia apólices → normaliza → calcula gap →
  comparação. Linguagem sempre de **complementar**, nunca de cancelar.

Depois: contratação com DPS, e acompanhamento em régua de status
(recebida → em preparação → enviada → em análise → pendência → aprovada →
emitida), com WhatsApp e e-mail a cada mudança. Esse acompanhamento é MVP
obrigatório, não enfeite: é o que diferencia de sumir num buraco negro depois
do pagamento.

Backoffice mostra cliente, seguradora, produto, valor, status, pendências,
quem precisa agir e há quanto tempo está parado naquela etapa.

**Decisão já tomada, não reabrir:** a tela principal de comparação não mistura
seguradoras. Nada de morte na seguradora A com doenças graves na B. Isso pode
existir depois, como recomendação consultiva do especialista, nunca como
confusão no checkout.

---

## 5. Onde a operação manual entra

Sem API, o fluxo é: o cliente solicita no site, o backoffice lança a proposta
no portal da seguradora e marca o status no nosso sistema, o que dispara
automaticamente a notificação ao cliente.

O cliente não percebe a diferença. A única parte que não sobrevive ao manual é
a **cotação**, porque precisa ser instantânea — e para isso o tarifário em
planilha resolve, com o cálculo feito no nosso banco.

Por isso a prioridade é tarifário antes de API. Com tarifário e operação
manual, o produto vai ao ar.

---

## 6. Sugestão de primeiro marco

Algo emitindo de ponta a ponta com uma seguradora e operação manual, em vez de
tudo pela metade com quatro:

1. Banco com o Insurance Schema, uma seguradora carregada, tarifa importada do
   CSV.
2. API com `/diagnostico` e `/comparar`, motor plugado.
3. Front das jornadas A e B, contratação e régua de status.
4. Backoffice mínimo: lista, mudança de status, disparo de notificação.
5. Jornada C e leitor de apólice ficam para a fase seguinte.

---

## 7. O que ainda não existe e é dependência externa

Tarifários reais, acordo comercial com seguradoras, e o parecer jurídico sobre
a arquitetura societária. Nenhum depende de código, e o terceiro é o único
capaz de invalidar o projeto em vez de só atrasá-lo.

Vale saber disso antes de estimar prazo.
