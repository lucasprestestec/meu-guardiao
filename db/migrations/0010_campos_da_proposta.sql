-- =============================================================================
-- 0010 — Campos da proposta (rodada 3)
-- Inventário real do que a Azos e a Icatu pedem na contratação. Os campos são
-- opcionais no banco (solicitações antigas não os têm); a obrigatoriedade por
-- seguradora é validada na API (api/proposta.py).
-- DADO SENSÍVEL: peso e altura são dado de saúde; endereço, renda e origem do
-- recurso são dados pessoais. Em produção exigem criptografia e controle de acesso.
-- Só acrescenta colunas e uma tabela. Para desfazer:
--   DROP TABLE beneficiario;
--   ALTER TABLE solicitacao DROP COLUMN nome_social, DROP COLUMN sexo, ... (lista abaixo)
-- =============================================================================

BEGIN;

ALTER TABLE solicitacao
  ADD COLUMN nome_social           text,
  ADD COLUMN sexo                  char(1) CHECK (sexo IN ('M','F')),
  ADD COLUMN renda_mensal          numeric(12,2) CHECK (renda_mensal > 0),
  ADD COLUMN peso_kg               numeric(5,1)  CHECK (peso_kg BETWEEN 20 AND 400),
  ADD COLUMN altura_cm             integer       CHECK (altura_cm BETWEEN 100 AND 250),
  ADD COLUMN cep                   char(8)       CHECK (cep ~ '^[0-9]{8}$'),
  ADD COLUMN logradouro            text,
  ADD COLUMN numero_endereco       text,
  ADD COLUMN complemento           text,
  ADD COLUMN bairro                text,
  -- Azos
  ADD COLUMN pep                   boolean,   -- pessoa politicamente exposta
  ADD COLUMN fumante_24_meses      boolean,   -- nicotina/cigarro eletrônico nos últimos 24 meses
  -- Icatu
  ADD COLUMN aposentado            text CHECK (aposentado IN ('nao','portempo','invalidezpordoenca','invalidezporacidente')),
  ADD COLUMN nacionalidade         text,
  ADD COLUMN pais_nascimento       text,
  ADD COLUMN pais_residencia       text,
  ADD COLUMN pais_residencia_fiscal text,
  ADD COLUMN us_person             boolean,
  ADD COLUMN origem_recurso        text,
  -- true = o cliente deixou para os beneficiários legais (só onde a seguradora aceita)
  ADD COLUMN beneficiarios_legais  boolean NOT NULL DEFAULT false;

CREATE TABLE beneficiario (
  id              bigserial PRIMARY KEY,
  solicitacao_id  uuid NOT NULL REFERENCES solicitacao(id) ON DELETE CASCADE,
  nome            text NOT NULL,
  data_nascimento date NOT NULL,
  parentesco      text NOT NULL,
  percentual      numeric(5,2) NOT NULL CHECK (percentual > 0 AND percentual <= 100)
);

CREATE INDEX idx_beneficiario_solicitacao ON beneficiario (solicitacao_id);

COMMIT;
