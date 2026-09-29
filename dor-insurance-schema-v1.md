# DOR$ INSURANCE SCHEMA v1.0
### Dicionário universal de coberturas de vida individual no Brasil

**Status:** v1.0 — estrutura fechada, catálogo aberto a ajuste
**Classificação:** MVP obrigatório
**Depende de:** nada
**Destrava:** Motor DOR$, comparador, motor tarifário, integrações, área do cliente

---

## 0. Por que este documento existe antes de tudo

Um comparador de seguro de vida quebra sempre no mesmo lugar: ele coloca lado a
lado dois preços que não se referem à mesma coisa.

Exemplos reais do que acontece sem um schema:

- Seguradora A oferece "Invalidez R$ 1.000.000" e é **IPA** (acidente, com tabela
  de percentuais por membro). Seguradora B oferece "Invalidez R$ 1.000.000" e é
  **IFPD** (doença, com gatilho funcional). Não são concorrentes — são coberturas
  complementares. Colocá-las na mesma linha é erro material.
- Seguradora A oferece "Doenças Graves R$ 500.000" cobrindo 3 doenças com
  sobrevivência de 30 dias. Seguradora B oferece "Doenças Graves R$ 500.000"
  cobrindo 40 doenças com estágios iniciais. O prêmio de A será menor. A conclusão
  "A é mais barata" é falsa.
- Seguradora A é capital nivelado vitalício. Seguradora B é temporário renovável
  com reajuste por faixa etária. No ano 1, B é 60% mais barata. No ano 25, B é
  impagável. Comparar prêmio do ano 1 é enganar o consumidor.

O Insurance Schema existe para tornar essas diferenças **estruturais e obrigatórias
no dado**, não opcionais na interface. Se a informação não couber no schema, a
comparação não é exibida.

**Regra de ouro:** nenhum produto entra no comparador sem que cada uma de suas
coberturas esteja mapeada para um código canônico com nível de confiança
`VERIFICADO`.

---

## 1. Arquitetura em cinco camadas

```
CAMADA 1   Dicionário canônico de coberturas        (o vocabulário)
CAMADA 2   Atributos normalizados por cobertura      (a gramática)
CAMADA 3   Modelo de produto, versão e tarifa        (o acervo)
CAMADA 4   Adaptadores por seguradora                (a tradução)
CAMADA 5   Equivalência, aderência e comparabilidade (o julgamento)
```

Cada camada só conhece a camada abaixo. O comparador nunca fala com uma
seguradora; fala com a Camada 5. O Motor DOR$ nunca fala com um produto; fala com
a Camada 1.

---

## 2. CAMADA 1 — Dicionário canônico de coberturas

### 2.1 Estrutura de cada verbete

| Campo | Descrição |
|---|---|
| `codigo` | Identificador estável, imutável. Nunca reutilizado. |
| `nome_canonico` | Nome exibível ao consumidor. |
| `familia` | MORTE, INVALIDEZ, DOENCA, RENDA, HOSPITALAR, SERVICO, ACESSORIA |
| `gatilho` | O evento que gera direito à indenização, em uma frase. |
| `unidade_capital` | CAPITAL_UNICO, DIARIA, RENDA_MENSAL, PERCENTUAL_TABELA, REEMBOLSO, SERVICO |
| `natureza_evento` | ACIDENTE, DOENCA, AMBOS |
| `necessidade_atendida` | Qual saída do Motor DOR$ esta cobertura atende. |
| `referencia_capital` | Código da cobertura que serve de base, quando o capital é derivado. |
| `exige` / `exclui` | Coberturas obrigatoriamente presentes ou mutuamente exclusivas. |

### 2.2 Catálogo v1.0 — 23 coberturas

> As tabelas abaixo agrupam as coberturas pelo **contexto comercial** em que a
> seguradora as vende. A `familia` gravada no banco pode ser outra: `FUNERAL_IND`,
> `FUNERAL_FAM`, `ISENCAO_PREMIO` e `SOM` têm `familia = SERVICO`, porque não
> entregam capital indenizatório e, portanto, nunca somam proteção.

#### Família MORTE

| Código | Nome canônico | Gatilho | Unidade | Natureza |
|---|---|---|---|---|
| `MORTE_QC` | Morte por Qualquer Causa | Falecimento do segurado por qualquer causa coberta | CAPITAL_UNICO | AMBOS |
| `MORTE_ACID` | Morte Acidental (adicional) | Falecimento decorrente exclusivamente de acidente pessoal | CAPITAL_UNICO | ACIDENTE |
| `ADT` | Antecipação por Doença Terminal | Diagnóstico de doença terminal com expectativa de vida abaixo do limite previsto | CAPITAL_UNICO | DOENCA |
| `FUNERAL_IND` | Assistência Funeral Individual | Falecimento do segurado | SERVICO ou REEMBOLSO | AMBOS |
| `FUNERAL_FAM` | Assistência Funeral Familiar | Falecimento do segurado ou de dependente previsto | SERVICO ou REEMBOLSO | AMBOS |

> `ADT` é antecipação, não cobertura adicional: reduz `MORTE_QC`. O schema precisa
> marcar isso, senão o comparador soma capital que não existe.

#### Família INVALIDEZ

| Código | Nome canônico | Gatilho | Unidade | Natureza |
|---|---|---|---|---|
| `IPA` | Invalidez Permanente Total ou Parcial por Acidente | Invalidez permanente por acidente, indenizada por tabela de percentuais | PERCENTUAL_TABELA | ACIDENTE |
| `IPTA` | Invalidez Permanente Total por Acidente | Invalidez permanente **total** por acidente | CAPITAL_UNICO | ACIDENTE |
| `IFPD` | Invalidez Funcional Permanente Total por Doença | Perda da existência independente por doença, conforme critério funcional das condições gerais | CAPITAL_UNICO | DOENCA |
| `ILP` | Invalidez Laborativa Permanente Total por Doença | Incapacidade permanente para a atividade laborativa principal | CAPITAL_UNICO | DOENCA |
| `ISENCAO_PREMIO` | Isenção de Pagamento de Prêmio | Invalidez ou evento previsto suspende a obrigação de pagar prêmio, mantendo a apólice | SERVICO | AMBOS |

> `IPA` e `IPTA` não coexistem no mesmo produto. `IFPD` e `ILP` têm gatilhos
> radicalmente diferentes de severidade — `ILP` é substancialmente mais fácil de
> acionar. Tratá-las como sinônimo é o erro mais caro do mercado.

#### Família DOENÇA

| Código | Nome canônico | Gatilho | Unidade | Natureza |
|---|---|---|---|---|
| `DG` | Doenças Graves | Diagnóstico de doença constante do rol contratado, cumprido o período de sobrevivência | CAPITAL_UNICO | DOENCA |
| `DG_ONCO` | Doenças Graves — Escopo Oncológico | Diagnóstico de câncer conforme definição contratual | CAPITAL_UNICO | DOENCA |
| `DG_CARDIO` | Doenças Graves — Escopo Cardiovascular | Evento cardiovascular conforme rol contratado | CAPITAL_UNICO | DOENCA |
| `SOM` | Segunda Opinião Médica | Diagnóstico de condição elegível | SERVICO | DOENCA |

> `DG` **não é comparável entre seguradoras sem o atributo `escopo_dg`** (ver 3.6).
> Esta é a exceção mais importante do schema.

#### Família RENDA

| Código | Nome canônico | Gatilho | Unidade | Natureza |
|---|---|---|---|---|
| `DIT` | Diária de Incapacidade Temporária | Afastamento temporário da atividade, por acidente ou doença, após franquia | DIARIA | AMBOS |
| `DIT_A` | Diária de Incapacidade Temporária por Acidente | Idem, restrito a acidente | DIARIA | ACIDENTE |
| `RENDA_INVALIDEZ` | Renda Mensal por Invalidez | Invalidez coberta, paga em parcelas mensais por prazo certo | RENDA_MENSAL | AMBOS |
| `RENDA_PENSAO` | Pensão por Morte / Renda aos Beneficiários | Morte do segurado, paga em parcelas mensais | RENDA_MENSAL | AMBOS |

#### Família HOSPITALAR

| Código | Nome canônico | Gatilho | Unidade | Natureza |
|---|---|---|---|---|
| `DIH` | Diária de Internação Hospitalar | Internação hospitalar acima da franquia | DIARIA | AMBOS |
| `DIH_UTI` | Diária de Internação em UTI | Internação em UTI, geralmente múltiplo da DIH | DIARIA | AMBOS |
| `CIRURGIA` | Eventos Cirúrgicos | Realização de procedimento constante da tabela contratada | PERCENTUAL_TABELA | AMBOS |

#### Família ACESSÓRIA

| Código | Nome canônico | Observação |
|---|---|---|
| `SORTEIO` | Sorteio / Título de Capitalização anexo | Não é cobertura securitária. Nunca entra em cálculo de proteção. |
| `ASSIST_PESSOAL` | Assistências (residencial, viagem, pet, etc.) | Serviço. Peso zero na aderência. |

> Coberturas ACESSÓRIA existem no schema apenas para que o comparador possa
> **exibi-las e neutralizá-las**. Elas nunca somam capital e nunca melhoram score.

---

## 3. CAMADA 2 — Atributos normalizados

Todo par (produto, cobertura) carrega obrigatoriamente os atributos abaixo. Campo
não preenchido = produto não publicável.

### 3.1 Estrutura do capital
- `tipo_capital`: `NIVELADO` | `DECRESCENTE` | `ATUALIZADO_INDICE`
- `indice_atualizacao`: IPCA, IGP-M, nenhum
- `capital_minimo`, `capital_maximo`
- `limite_percentual_referencia` + `referencia_capital` — ex.: DG limitada a 50% de `MORTE_QC`

### 3.2 Temporalidade
- `temporalidade`: `VITALICIO` | `TEMPORARIO` | `ATE_IDADE`
- `idade_limite_cobertura`
- `idade_min_contratacao`, `idade_max_contratacao`

### 3.3 Renovação e reajuste — o campo que decide comparações
- `renovacao`: `AUTOMATICA_GARANTIDA` | `AUTOMATICA_NAO_GARANTIDA` | `NAO_RENOVAVEL`
- `reajuste`: `PREMIO_NIVELADO` | `FAIXA_ETARIA` | `ANUAL_INDICE` | `SINISTRALIDADE` | `MISTO`
- `periodicidade_reagravamento_anos`

> **Exigência de produto:** onde `reajuste != PREMIO_NIVELADO`, o comparador é
> obrigado a exibir prêmio hoje **e** projeção em 10, 20 e 30 anos. Sem isso, o
> preço exibido é propaganda, não informação.

### 3.4 Carência e franquia
- `carencia_dias_geral`
- `carencia_dias_especifica` (JSON por causa)
- `carencia_suicidio_dias` — padrão 730 (art. 798, Código Civil)
- `franquia_dias` (DIT/DIH)
- `periodo_maximo_indenizacao_dias`
- `periodo_sobrevivencia_dias` (DG)

### 3.5 Exclusões e restrições
- `exclusoes` — lista normalizada, não texto livre
- `doencas_preexistentes_tratamento`
- `agravo_profissao_aplicavel`, `agravo_esporte_aplicavel`
- `cobertura_geografica`

### 3.6 `escopo_dg` — objeto obrigatório para DG
```
{
  "quantidade_doencas": 40,
  "rol": ["CANCER_INVASIVO", "INFARTO_AGUDO_MIOCARDIO", "AVC", ...],
  "cobre_estagio_inicial": true,
  "carcinoma_in_situ": "PARCIAL_25_PCT",
  "periodo_sobrevivencia_dias": 30,
  "pagamento": "UNICO_POR_EVENTO" | "MULTIPLO_POR_GRUPO",
  "reduz_capital_morte": false
}
```
O rol usa codificação canônica própria de doenças (`DOENCA_*`), não o nome
comercial da seguradora. Duas seguradoras que chamam a mesma condição de nomes
diferentes precisam colidir no mesmo código.

### 3.7 Econômicos
- `valor_resgate`: SIM/NAO
- `portabilidade`: SIM/NAO
- `comissionamento_pct` (interno, nunca exposto ao consumidor)
- `forma_pagamento_aceita`

---

## 4. CAMADA 3 — Produto, versão e tarifa

Três entidades separadas, e isso não é detalhe:

- **`produto`** — a identidade comercial (nome, seguradora, processo SUSEP).
- **`produto_versao`** — o conjunto de condições gerais vigentes em um período.
- **`tarifa_versao`** — a tabela de preços, que muda com frequência muito maior
  que as condições gerais.

Toda cotação grava `produto_versao_id` **e** `tarifa_versao_id`. Uma cotação de
janeiro tem que ser reproduzível bit a bit em dezembro, inclusive em juízo.

Tarifa canônica:
`(cobertura, faixa_idade, sexo, fumante, classe_risco) → taxa_por_mil` ou
`taxa_por_unidade_diaria`, mais multiplicadores de agravo e carregamentos.

---

## 5. CAMADA 4 — Adaptadores por seguradora

Cada seguradora tem um adaptador que responde a uma pergunta só:
**"o que esta seguradora chama de X é, canonicamente, o quê?"**

Cada mapeamento guarda:
- `rotulo_original` — o nome exato usado pela seguradora
- `codigo_canonico`
- `confianca`: `VERIFICADO` (lido nas condições gerais) | `INFERIDO` (deduzido de
  material comercial) | `A_VERIFICAR`
- `fonte` — documento, página, data
- `revisado_por`, `revisado_em`

**Regra operacional:** `confianca != VERIFICADO` ⇒ o produto não aparece no
comparador ao consumidor. Pode aparecer no backoffice, marcado.

Isso é o que separa este projeto de um agregador de preços. É também trabalho
manual e chato — e é exatamente por isso que vira barreira de entrada.

---

## 6. CAMADA 5 — Equivalência, aderência e comparabilidade

### 6.1 Classes de equivalência
Duas coberturas de produtos diferentes são comparáveis quando pertencem à mesma
**classe de equivalência**, não apenas ao mesmo código. A classe considera código
canônico + natureza do evento + gatilho de severidade.

| Classe | Coberturas |
|---|---|
| `EQ_MORTE` | `MORTE_QC` |
| `EQ_MORTE_ACID` | `MORTE_ACID`, parcela acidental de `MORTE_QC` quando destacada |
| `EQ_INVAL_ACID` | `IPA`, `IPTA` — com nota de diferença de gatilho |
| `EQ_INVAL_DOENCA` | `IFPD`, `ILP` — **com alerta obrigatório de severidade** |
| `EQ_DG` | `DG`, `DG_ONCO`, `DG_CARDIO` — só comparáveis com `escopo_dg` preenchido |
| `EQ_RENDA_TEMP` | `DIT`, `DIT_A` |
| `EQ_HOSPITALAR` | `DIH`, `DIH_UTI` |

Quando dois produtos caem na mesma classe mas diferem em gatilho, o comparador
exibe o preço **e** a diferença. Nunca só o preço.

### 6.2 Aderência (estrutura, calibração pendente)

Para cada necessidade `n` produzida pelo Motor DOR$:

```
aderencia(n) = cobertura_capital(n) × qualidade_estrutural(n) × penalidade_restricao(n)

cobertura_capital     = min(1, capital_ofertado / capital_necessario)
qualidade_estrutural  = f(temporalidade, renovacao, tipo_capital, reajuste)
penalidade_restricao  = g(carencia, franquia, exclusoes, escopo_dg)
```

`aderencia_total` = média ponderada pelas necessidades, com pesos vindos do Motor
(a vulnerabilidade maior pesa mais).

**Pendência declarada:** os pesos de `f` e `g` são a fronteira entre este
documento e o Motor DOR$ v1.0. Ficam em aberto de propósito. O que o schema
garante é que **todos os insumos de `f` e `g` são campos obrigatórios e
auditáveis** — nenhum deles é inferido por IA em tempo de execução.

---

## 7. O que este schema proíbe

1. Somar capitais de coberturas de famílias diferentes em um número único de
   "proteção total" sem discriminar.
2. Somar `ADT` ao capital de morte.
3. Somar coberturas `ACESSORIA` a qualquer capital.
4. Comparar `DG` sem `escopo_dg`.
5. Exibir prêmio de produto com reajuste por faixa etária sem projeção.
6. Publicar produto com mapeamento `INFERIDO` ou `A_VERIFICAR`.
7. Tratar `IFPD` e `ILP` como a mesma coisa.

Essas sete regras devem ser **constraints e testes automatizados**, não
orientação para o time.

---

## 8. Pendências desta versão

| Item | Responsável | Bloqueia |
|---|---|---|
| Codificação canônica de doenças (`DOENCA_*`) — lista fechada | Produto | `escopo_dg`, comparação de DG |
| Tabela normalizada de exclusões | Produto | Camada 2 |
| Condições gerais reais de cada produto a mapear | Seguradoras | Camada 4 inteira |
| Tabela de percentuais de `IPA` e `CIRURGIA` — são tabelas, não números | Produto | Camada 5 |
| Verificação dos processos SUSEP de cada produto | Backoffice | Publicação |
| Calibração de `f` e `g` | Motor DOR$ v1.0 | Ranking do comparador |

---

## 9. Registro de decisões — v1.0

- **Decidido:** arquitetura em 5 camadas; catálogo canônico de 23 coberturas;
  `confianca` de mapeamento como gate de publicação; versionamento separado de
  produto, condições e tarifa; 7 proibições estruturais viram constraint e teste.
- **Decidido:** coberturas acessórias entram no schema apenas para neutralização.
- **Aberto:** codificação canônica de doenças, tabela de exclusões, calibração dos
  pesos de aderência (vai para o Motor DOR$ v1.0), tabelas de percentuais de IPA e
  cirurgia.
