# Changelog — Motor DOR$ (projeto Meu Guardião)

Versionamento semântico. **Regra imutável:** qualquer alteração que mude um
número de saída exige nova versão em `parametros.VERSAO_MOTOR` e uma entrada
aqui. Cotação gravada sob a versão X precisa ser recalculável com a versão X
para sempre.

## [1.3.1] — 2026-09-30

### Corrigido
- **Justificativa da morte afirmava falsidade.** Com `metodo_morte` fixado em
  `RENDA_PERPETUA`, o texto dizia que o valor adotado "superou o método
  alternativo" mesmo quando o alternativo era maior. Agora só afirma superação
  com `MAIOR_ENTRE`; nos demais casos apresenta o alternativo e explica a
  escolha pelo critério mais conservador. Patch do cliente
  (`docs/CORRECAO-v1.3.1.md`), travado por teste.

### Alterado (só texto)
- Rótulo da necessidade de renda: "Diária de internação" (antes
  "internação / afastamento"). O cálculo (renda mensal ÷ 30) não muda.
- Nenhum número de saída mudou.

## [Não publicado] — Rodada 2 do cliente (comparador 1.3.0)

### Desligado por configuração (código preservado)
- Protection Score, barra e percentual de aderência, selos "recomendada / menor preço /
  maior proteção" e as abas por critério: `web/lib/recursos.ts`
  (`NEXT_PUBLIC_RECURSO_SCORE`, `_ADERENCIA`, `_DESTAQUES` = "1" religa). O comparador segue
  calculando score e aderência; só a tela não mostra.
- Ordem da lista: do mais barato ao mais caro (`ParametrosComparador.ordenar_por`, "ADERENCIA"
  restaura a regra antiga).
- Proteção de renda: só a diária de internação (DIH) atende; a tabela de percentuais entre
  tipos de diária saiu.

### Novo
- Cirurgias (`CIRURGIA`) e fraturas (`FRATURA_RUPTURA`, nova no dicionário, migração 0007) como
  coberturas escolhidas direto pelo cliente: R$ 20.000 e R$ 100.000 de partida, com régua.
  Os limites reais por seguradora serão levantados depois (os do catálogo são fictícios).
- Aviso, sem bloquear, quando a régua chega ao teto: "Este produto vai até R$ X. Quer falar com
  um especialista sobre valores maiores?"
- "Falar com um especialista": pedido (sem agenda) com contato pré-preenchido, motivos de
  múltipla escolha e texto livre; chega ao backoffice com o diagnóstico completo.
- Recado livre na personalização e no checkout; aparece na ficha do backoffice.
- Mapa de Proteção sem nota: mostra as quatro necessidades, o que o cliente já tem e o que falta.
- Cobertura desligada sai do preço, mas a necessidade continua no Mapa.
- Captura de contato antes do Mapa (nome, e-mail, telefone) com dois consentimentos separados e
  não pré-marcados, registro de data, hora, IP e versão do texto, link para a Política de
  Privacidade e medição de abandono do funil. TEXTOS EM RASCUNHO (revisão jurídica).
- Rodapé e "Quem somos" com CNPJ e registro SUSEP em branco (`web/lib/empresa.ts`);
  `/privacidade` é só marcador até a revisão jurídica.
- Mensagem pós-contratação sem prazo de nenhuma etapa.

## [Não publicado] — API e banco

### Comparador 1.2.0 (decisão do cliente: invalidez só por acidente)
- `ParametrosComparador.coberturas_inativas` (padrão `IFPD`, `ILP`, `IPT_LISTA`): o
  comparador só considera IPA/IPTA para a necessidade de invalidez. As demais
  seguem no schema e no catálogo; reativar = esvaziar o conjunto.
- Catálogo fictício: Alfa e Beta passam a oferecer IPA (além das coberturas inativas).
- Efeito esperado: a aderência de invalidez fica em 35% para todos os produtos.
- `docs/contrato-comparador.json` e `contrato-motor.json` regenerados.

### Disparo pós-contratação
- Primeira mensagem: confirmação, o que acontece, régua, prazo
  (`PRAZO_ESPERADO_TEXTO`), condições gerais (link ou promessa de envio no dia),
  contato (`CANAL_CONTATO_TEXTO`).
- Ficha do backoffice alerta quando não há condições gerais cadastradas e
  oferece e-mail pronto (mailto) além do WhatsApp pronto.
- Caixa de saída para o CRM: `GET /v1/backoffice/notificacoes/pendentes` e
  `POST .../{id}/enviada`. E-mail automático por SMTP (`api/envio.py`), só com
  `SMTP_HOST`/`EMAIL_REMETENTE` e `NOTIFICACOES_ATIVAS=1`.

- WhatsApp automático pelo CRM DeskComm (`api/crm.py`, `docs/INTEGRACAO-DESKCOMM.md`):
  abre a conversa pelo telefone e envia com chave de idempotência. Falha deixa pendente.

- Banco da demonstração se atualiza sozinho (`api/preparo.py`): migrações e catálogo
  fictício completados na primeira requisição, só no modo demonstração. O seed passa a
  acrescentar cobertura nova a produto já carregado, sem alterar o existente.

Os testes de motor/comparador seguem; total 102 com API e banco.

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
