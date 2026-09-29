# Changelog — Motor DOR$ (projeto Meu Guardião)

Versionamento semântico. **Regra imutável:** qualquer alteração que mude um
número de saída exige nova versão em `parametros.VERSAO_MOTOR` e uma entrada
aqui. Cotação gravada sob a versão X precisa ser recalculável com a versão X
para sempre.

## [Não publicado] — API e banco (Motor DOR$ continua 1.3.0)

Nenhum número do Motor mudou; os 48 testes do motor/comparador seguem iguais.

### Adicionado
- `api/`: `POST /v1/diagnostico`, `POST /v1/comparar`, `GET /v1/saude`.
- Comparador 1.1.0: `capitais_escolhidos` opcional (sliders). Sem ele, a saída é
  idêntica à 1.0.0. A aderência continua medindo contra a necessidade (gap).
- `motor_dor/projecao.py`: prêmio projetado em 10/20/30 anos (capital constante,
  tabela de hoje na idade futura).
- Banco: migrações 0001–0005 (trava de tarifa FICTICIA, condições gerais
  versionadas, IPT_LISTA, necessidade/cotação auditáveis).

## [1.3.0] — 2026-09-23

### Adicionado — Comparador
- `comparador.py`: cota produtos contra o Mapa de Proteção e ranqueia por
  aderência, com preço como desempate. Estrutura de tarifa real
  (cobertura × faixa etária × sexo × fumo), pronta para receber tarifário de
  seguradora.
- `catalogo_ficticio.py`: três arquétipos de produto com **tarifas
  inventadas**, para exercitar o comparador. Todo produto com
  `fonte_tarifa="FICTICIA"` gera alerta e não pode ser exibido ao consumidor.
  Travado por teste.
- Tabela `COBERTURAS_QUE_ATENDEM`: quanto cada cobertura realmente atende cada
  necessidade. IFPD atende 100% da necessidade de invalidez; IPT de lista
  fechada, 65%; IPA, 35%. É o que impede comparar banana com maçã.
- Qualidade estrutural penaliza temporalidade, renovação não automática,
  renovação com nova subscrição, capital decrescente, reajuste etário,
  carência longa e rol curto de doenças graves.
- 11 testes novos. Total: 48.

### Resultado que valida o desenho
No cliente de exemplo, o produto mais barato (R$ 2.257/mês) tem 11% de
aderência e nem oferece doenças graves; o recomendado custa R$ 15.709 com 94%.
Um comparador de preço puro recomendaria o primeiro.

### Pendente
- Tarifários reais. Sem eles o comparador não vai ao ar.
- Projeção de prêmio em 10/20/30 anos para produtos com reajuste etário.
- Camada de cenários por orçamento.

## [1.2.0] — 2026-09-23

### Alterado
- **Morte passa a seguir a mesma lógica da invalidez:** capital que, rendendo
  0,8% ao mês, repõe a renda mensal do segurado. O método por anos de
  dependência sai do caminho padrão (continua implementado em
  `MetodoMorte.ANOS_DEPENDENCIA` e pode ser reativado em um parâmetro).
- `idade_independencia_filho` deixa de afetar o capital. Segue em uso para
  inferir fase de vida e para exibir o horizonte de dependência ao cliente.

### Efeito sobre os casos reais
A distância entre necessidade calculada e capital proposto caiu de 3,3–8,3×
para 2,0–2,9× nos casos com orçamento folgado. O caso C (dentista, sem
reserva, orçamento apertado) segue em 8,3× — ali o corte foi comercial, não
técnico.

### Consequência a observar
Morte e invalidez agora partem do mesmo capital-base. Como morte ainda soma
dívidas, projetos e 15% do espólio, **morte passa a superar invalidez** sempre
que existir qualquer um dos três. Isso contraria a prática histórica, em que
invalidez era sistematicamente maior. Travado por teste para ficar visível.

## [1.1.0] — 2026-09-23

Substitui as fórmulas inventadas da v1.0.0 pelas **premissas definidas pelo
especialista**. Não existe consenso de mercado sobre como dimensionar capital
segurado; estas são premissas assumidas, explicáveis e ajustáveis.

### Alterado — TODOS os números de saída mudaram
- **Base de cálculo agora é a RENDA**, não o padrão de vida. "O seguro é o
  guardião da renda."
- **Morte** passa a ser o maior entre dois métodos: (a) anos até o dependente
  mais novo completar 25 × 12 × renda; (b) renda ÷ 0,8% ao mês. Somam-se
  dívidas, projetos e 15% do patrimônio inventariável (média brasileira de
  ITCMD, honorários e custas).
- **Invalidez** = renda ÷ 0,8% ao mês.
- **Doenças graves** = 24 × renda.
- **Diária** = renda ÷ 30.
- **Valor presente removido.** O especialista não usa desconto; multiplica
  direto.
- **Patrimônio não abate mais nenhuma necessidade.** O produto existe para
  preservar patrimônio, não para assumir que a família vai consumi-lo.
- **Seguro existente continua abatendo**, para mostrar o gap.

### Removido
- Invariante "invalidez ≥ morte". Com o método do maior-entre, morte passa
  invalidez em vários perfis. Consequência direta das premissas adotadas.
- Parâmetros de valor presente, liquidez do patrimônio, custo de adaptação e
  reserva de tratamento.

### Pendente
- `base_calculo_doenca_grave`: o especialista disse "sempre renda", mas o
  exemplo dado para DG usou padrão de vida. Confirmar.
- **Camada de Capital Recomendado.** `calibracao.py` mostra que a necessidade
  calculada fica de 3,3× a 8,3× acima do que foi efetivamente proposto aos
  clientes nos casos reais de morte. DG e diária batem quase exatamente.

## [1.0.0] — 2026-09-22
Primeira versão executável. Fórmulas provisórias baseadas em valor presente de
anuidade, substituídas na v1.1.0.
