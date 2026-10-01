# WhatsApp pelo DeskComm CRM

O Meu Guardião grava cada mensagem na caixa de saída (`notificacao`). Com o DeskComm
configurado, o WhatsApp sai sozinho a cada nova solicitação ou mudança de status.

## Como funciona (código em `api/crm.py`)

1. `POST {DESKCOMM_URL}/api/v1/conversations/open-with-contact` com o celular do cliente
   (cria o contato no CRM se ele não existir) e devolve a conversa.
2. `POST {DESKCOMM_URL}/api/v1/messages` envia o texto nessa conversa.
   O cabeçalho `Idempotency-Key` é fixo por notificação: reenviar não duplica.
3. Só então a notificação é marcada como enviada. Qualquer falha (CRM fora, 429 do ritmo de
   envio, token inválido) deixa a mensagem pendente para a próxima rodada.

Conferido no código do DeskComm (`app/api/v1/messages/route.ts`,
`app/api/v1/conversations/open-with-contact/route.ts`): as duas rotas aceitam token de
servidor (`Authorization: Bearer dsk_...`) com escopo `mcp:write`.

## O que configurar

No DeskComm: Configurações > Tokens de API, criar um token com o escopo
`mcp:write` e guardar o valor (só aparece uma vez).

No servidor do Meu Guardião (variáveis de ambiente, nunca no código):

| Variável | Valor |
|---|---|
| `DESKCOMM_URL` | endereço do CRM, ex.: `https://crm.seudominio.com.br` |
| `DESKCOMM_TOKEN` | o token `dsk_...` |
| `DESKCOMM_CHANNEL_SESSION_ID` | opcional: id do número de WhatsApp a usar. Sem ele, o CRM escolhe |
| `NOTIFICACOES_ATIVAS` | `1` para enviar automaticamente após cada ação |

Enviar o que está pendente agora (backoffice, cabeçalho `X-Backoffice-Key`):
`POST /v1/backoffice/notificacoes/enviar-whatsapp`.

## Ainda não verificado contra um CRM real

Os testes usam um servidor falso que imita o DeskComm. Faltam ser conferidos num DeskComm
de verdade: o formato exato das respostas (`data.conversation_id`), o comportamento do ritmo
de envio por token e o envio proativo a um número que nunca falou com o CRM.

## Atenção

Com o envio automático ligado, não use também o botão manual "Abrir WhatsApp com a
mensagem pronta" na mesma solicitação: o cliente receberia duas vezes.
