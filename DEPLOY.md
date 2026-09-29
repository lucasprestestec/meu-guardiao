# Publicar a demonstração

Três peças: **banco no Neon**, **API num host com Docker**, **front na Vercel**.
Tudo com dados fictícios. Nada aqui é para cliente real.

## 1. Banco (Neon)

1. Crie um projeto em neon.tech e copie a *connection string* (`postgresql://...?sslmode=require`).
2. No seu computador, na raiz do projeto, aplique o schema e o catálogo fictício **usando essa string
   só na variável de ambiente** (não cole em arquivo nem na conversa):

   PowerShell:
   ```powershell
   $env:DATABASE_URL = "postgresql://...sslmode=require"
   python db/migrate.py
   python db/seed_ficticio.py
   ```
   Git Bash: `DATABASE_URL="postgresql://..." python db/migrate.py` (idem para o seed).

## 2. API (host com Docker)

Crie um serviço web a partir desta repo (o `Dockerfile` da raiz já serve) com as variáveis:

| Variável | Valor |
|---|---|
| `DATABASE_URL` | a string do Neon |
| `PERMITIR_TARIFA_FICTICIA` | `1` (demonstração: sem isso a API só mostra produtos publicados, e hoje não há nenhum) |
| `BACKOFFICE_KEY` | uma chave forte e sua. **Não use `demo`.** |

Teste: `https://SUA-API/v1/saude` deve responder `{"ok":true,...,"modo_demonstracao":true}`.

Depois, para carregar as solicitações de exemplo (opcional):
```powershell
$env:API_URL = "https://SUA-API"; $env:BACKOFFICE_KEY = "a-mesma-chave"
python db/demo_data.py
```

## 3. Front (Vercel)

1. Importe a repo na Vercel e em **Root Directory** escolha `web`. Framework: Next.js (detectado).
2. Variável de ambiente **antes do primeiro build**: `API_URL` = `https://SUA-API` (sem barra no fim).
   O `next.config.ts` lê essa variável na hora do build; se mudar depois, faça um novo deploy.
3. Deploy. Abra `/diagnostico?demo=1` e `/backoffice`.

## Cuidados
- Endereço público = o backoffice fica exposto na internet, protegido só pela chave. Use chave forte.
- Não há login de cliente: quem tem o link de `/acompanhar/...` vê aquela solicitação.
- Mensagens de WhatsApp e e-mail continuam sem envio automático.
