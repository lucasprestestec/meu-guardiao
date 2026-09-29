-- =============================================================================
-- 0006 — Solicitação de contratação, régua de status, consentimentos, notificações
-- A solicitação aponta para um cotacao_item: o que o cliente pediu fica
-- congelado junto com as versões de produto, condições gerais e tarifa.
-- =============================================================================

BEGIN;

CREATE TYPE status_solicitacao AS ENUM (
  'RECEBIDA','EM_PREPARACAO','ENVIADA','EM_ANALISE','PENDENCIA',
  'APROVADA','EMITIDA','RECUSADA','CANCELADA'
);

CREATE TABLE solicitacao (
  id               uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  cliente_id       uuid NOT NULL REFERENCES cliente(id),
  cotacao_item_id  uuid NOT NULL REFERENCES cotacao_item(id),
  status           status_solicitacao NOT NULL DEFAULT 'RECEBIDA',
  status_desde     timestamptz NOT NULL DEFAULT now(),
  pendencia        text,
  numero_apolice   text,
  -- dados pessoais (PII: em produção exigem criptografia e controle de acesso)
  nome             text NOT NULL,
  cpf              char(11) NOT NULL CHECK (cpf ~ '^[0-9]{11}$'),
  data_nascimento  date NOT NULL,
  email            text NOT NULL,
  celular          text NOT NULL CHECK (celular ~ '^[0-9]{10,11}$'),
  profissao        text,
  faixa_renda      text,
  estado_civil     text,
  cidade           text,
  uf               char(2),
  -- true = produto com tarifa fictícia, só existe em demonstração
  demonstracao     boolean NOT NULL,
  criada_em        timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT pendencia_descrita CHECK (status <> 'PENDENCIA' OR pendencia IS NOT NULL)
);

CREATE INDEX idx_solicitacao_status ON solicitacao (status, status_desde);
CREATE INDEX idx_solicitacao_cliente ON solicitacao (cliente_id);

CREATE TABLE solicitacao_historico (
  id             bigserial PRIMARY KEY,
  solicitacao_id uuid NOT NULL REFERENCES solicitacao(id) ON DELETE CASCADE,
  status         status_solicitacao NOT NULL,
  nota           text,
  por            text NOT NULL,
  em             timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX idx_historico_solicitacao ON solicitacao_historico (solicitacao_id, em);

-- Trilha de consentimento: guarda o texto exato exibido e a versão dele.
CREATE TABLE consentimento (
  id             bigserial PRIMARY KEY,
  solicitacao_id uuid NOT NULL REFERENCES solicitacao(id) ON DELETE CASCADE,
  tipo           text NOT NULL,
  texto_versao   text NOT NULL,
  texto          text NOT NULL,
  aceito_em      timestamptz NOT NULL DEFAULT now(),
  UNIQUE (solicitacao_id, tipo)
);

-- Caixa de saída: cada mudança de status registra o que deve ser enviado.
-- O envio real (WhatsApp/e-mail) depende de contas externas e é etapa própria.
CREATE TABLE notificacao (
  id             bigserial PRIMARY KEY,
  solicitacao_id uuid NOT NULL REFERENCES solicitacao(id) ON DELETE CASCADE,
  canal          text NOT NULL CHECK (canal IN ('WHATSAPP','EMAIL')),
  status_destino status_solicitacao NOT NULL,
  mensagem       text NOT NULL,
  criada_em      timestamptz NOT NULL DEFAULT now(),
  enviada_em     timestamptz
);

COMMIT;
