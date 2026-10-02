-- =============================================================================
-- 0007 - Rodada 2 do cliente
--   * FRATURA_RUPTURA entra no dicionario (CIRURGIA ja existia)
--   * recado do cliente na cotacao (personalizacao) e na solicitacao (checkout)
--   * captura de contato com consentimentos separados e trilha de auditoria
--   * pedido de conversa com o especialista
--   * eventos do funil (medir abandono na tela de contato)
-- =============================================================================

BEGIN;

INSERT INTO cobertura_canonica
  (codigo, nome_canonico, familia, gatilho, unidade_capital, natureza_evento,
   necessidade_atendida, soma_protecao, peso_aderencia_default) VALUES
('FRATURA_RUPTURA','Fraturas e Rupturas Ligamentares','HOSPITALAR',
 'Fratura ossea ou ruptura ligamentar por acidente, conforme tabela contratada',
 'CAPITAL_UNICO','ACIDENTE','NEC_FRATURA', true, 0.400);

INSERT INTO classe_equivalencia (codigo, descricao, exige_alerta_gatilho, exige_escopo_dg)
VALUES ('EQ_FRATURA','Fraturas e rupturas por acidente', false, false);

INSERT INTO cobertura_classe (codigo_cobertura, codigo_classe)
VALUES ('FRATURA_RUPTURA','EQ_FRATURA');

ALTER TABLE cotacao     ADD COLUMN recado text;
ALTER TABLE solicitacao ADD COLUMN recado text;

-- Contato capturado ANTES do Mapa de Protecao. Sem senha, sem conta.
CREATE TABLE lead_contato (
  id             uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  necessidade_id uuid REFERENCES necessidade(id),
  nome           text NOT NULL,
  email          text NOT NULL,
  celular        text NOT NULL CHECK (celular ~ '^[0-9]{10,11}$'),
  criado_em      timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX idx_lead_necessidade ON lead_contato (necessidade_id);

-- Um registro por consentimento (separados). Guarda o texto exato, a versao, quando e de onde.
CREATE TABLE consentimento_lead (
  id           bigserial PRIMARY KEY,
  lead_id      uuid NOT NULL REFERENCES lead_contato(id) ON DELETE CASCADE,
  tipo         text NOT NULL CHECK (tipo IN ('ATENDIMENTO','MARKETING')),
  aceito       boolean NOT NULL,
  texto_versao text NOT NULL,
  texto        text NOT NULL,
  aceito_em    timestamptz NOT NULL DEFAULT now(),
  ip           text,
  user_agent   text,
  revogado_em  timestamptz,
  UNIQUE (lead_id, tipo)
);

CREATE TABLE pedido_especialista (
  id             uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  lead_id        uuid REFERENCES lead_contato(id),
  necessidade_id uuid REFERENCES necessidade(id),
  cotacao_id     uuid REFERENCES cotacao(id),
  nome           text NOT NULL,
  email          text NOT NULL,
  celular        text NOT NULL CHECK (celular ~ '^[0-9]{10,11}$'),
  motivos        text[] NOT NULL,
  mensagem       text,
  status         text NOT NULL DEFAULT 'NOVO' CHECK (status IN ('NOVO','EM_CONTATO','CONCLUIDO')),
  criado_em      timestamptz NOT NULL DEFAULT now(),
  atualizado_em  timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX idx_pedido_esp_status ON pedido_especialista (status, criado_em);

CREATE TABLE evento_funil (
  id     bigserial PRIMARY KEY,
  etapa  text NOT NULL,
  sessao text NOT NULL,
  em     timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX idx_evento_funil_etapa ON evento_funil (etapa, em);

COMMIT;
