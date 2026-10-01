# Ajustes no site — Meu Guardião

Levantado testando o site em produção em 30/09/2026. Tudo nesta lista está
decidido. Implementar.

---

## 1. Marca

Trocar "DOR$ Compare" por **Meu Guardião** em todo o site e no código.

O nome ainda é provisório e pode mudar. Deixe como constante única, não
espalhado em texto, para que a próxima troca seja barata.

---

## 2. Correção do Motor — v1.3.1

Aplicar o patch descrito em `docs/CORRECAO-v1.3.1.md`.

O texto da justificativa de morte afirma ter "superado o método alternativo"
com o número maior aparecendo na mesma frase. Exemplo que apareceu no site:
"seriam necessários R$ 3.125.000... Esse valor superou o método alternativo
(R$ 5.700.000)".

Nenhum valor de cálculo muda. Só o texto.

---

## 3. Invalidez — só por acidente

No comparador, trabalhar apenas com invalidez por acidente (IPA/IPTA).

**Não remover do schema** as coberturas IFPD, ILP e IPT de lista fechada.
Deixe cadastradas e inativas. A decisão vai ser revista quando chegarem as
condições gerais das seguradoras, e aí precisa ser ligar uma chave, não
refazer.

Consequência esperada: enquanto todos os produtos tiverem a mesma cobertura, a
aderência deixa de diferenciar nessa linha. Está correto.

---

## 4. Proteção de renda é INTERNAÇÃO, não afastamento

O cálculo continua igual: `diária = renda mensal ÷ 30`.

O que muda são os textos. Trocar "afastamento" por **internação** no rótulo da
necessidade, na descrição do Mapa de Proteção e no comparador.

---

## 5. Remover o aviso de cobertura acima do necessário

O cliente escolhe o capital que quiser, sem rótulo de excesso. Não criar aviso
de "acima do necessário". A cobertura exibida continua limitada a 100%.

---

## 6. Incluir cirurgias e fraturas

Adicionar `CIRURGIA` e `FRATURA_RUPTURA` ao comparador. Já existem no schema.

---

## 7. Mostrar o tipo de cobertura no card do comparador

Hoje o card mostra "Invalidez R$ 1M" para um produto que só cobre acidente. A
barra de aderência captura a diferença, mas ninguém lê a barra — leem a linha.

Cada linha de cobertura precisa trazer a observação que o comparador já
calcula (campo `observacoes` de cada item), por exemplo:
- "Invalidez apenas por acidente"
- "Limitado a R$ 1.000.000 — abaixo do que você precisa"
- "Rol de 10 doenças"

---

## 8. Esclarecer a diferença entre necessidade e gap

O Mapa mostra "Morte R$ 3.560.000" e a tela de personalização mostra
"Sugerido: R$ 3.060.000". Está correto — um é a necessidade total, outro é o
que falta depois do seguro que o cliente já tem. Mas ninguém entende sozinho.

Explicitar na personalização: "Você já tem R$ 500.000. Falta contratar:".

---

## 9. Captura de contato antes do Mapa de Proteção

Pedir nome, e-mail e telefone **antes de exibir o Mapa**. Sem senha e sem criar
conta: só contato. Conta e senha continuam só no checkout.

Requisitos:
- Dois consentimentos separados e **não pré-marcados**: um para receber o
  resultado e ser contatado sobre a proposta, outro para marketing.
  Consentimento em bloco único não é válido.
- Link visível para a Política de Privacidade no mesmo ponto.
- Registrar data, hora, IP e a versão do texto aceito.
- Canal para revogar o consentimento e pedir exclusão.
- Instrumentar o funil para medir quantos abandonam nessa tela.

---

## 10. Disparo pós-contratação

Ao solicitar a contratação, enviar por WhatsApp e e-mail:
1. Confirmação de recebimento e o que acontece agora
2. A régua de status e o prazo esperado
3. **As condições gerais do produto e da seguradora contratada**
4. Canal de contato

O item 3 é obrigação regulatória, não cortesia. Enquanto não houver automação,
precisa haver um caminho para o backoffice enviar manualmente no mesmo dia.

---

## 11. Página "Quem somos"

Incluir. Registro SUSEP, experiência e por que o negócio existe.
