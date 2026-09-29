-- =============================================================================
-- 0004 — Necessidade e cotação gravadas de forma auditável
--   * necessidade_item guardava codigo_cobertura com FK para o dicionário de
--     coberturas, mas o Motor produz NEC_* (necessidades), que não são
--     coberturas. Corrige o nome/FK e guarda a memória de cálculo completa.
--   * cotacao passa a registrar tudo que a reproduz: perfil, capitais
--     escolhidos e versões do motor e do comparador.
-- Tabelas ainda vazias em qualquer ambiente: migração sem perda de dados.
-- =============================================================================

BEGIN;

ALTER TABLE necessidade_item DROP CONSTRAINT necessidade_item_codigo_cobertura_fkey;
ALTER TABLE necessidade_item RENAME COLUMN codigo_cobertura TO codigo_necessidade;
ALTER TABLE necessidade_item
  ADD CONSTRAINT codigo_necessidade_valido CHECK (codigo_necessidade LIKE 'NEC\_%'),
  ADD COLUMN rotulo          text NOT NULL,
  ADD COLUMN unidade         text NOT NULL CHECK (unidade IN ('CAPITAL','DIARIA')),
  ADD COLUMN valor_existente numeric(14,2) NOT NULL DEFAULT 0,
  ADD COLUMN memoria         jsonb NOT NULL;
ALTER TABLE necessidade_item ALTER COLUMN peso TYPE numeric(8,6);

ALTER TABLE necessidade
  ADD COLUMN vulnerabilidade_principal text,
  ADD COLUMN alertas jsonb NOT NULL DEFAULT '[]'::jsonb;

ALTER TABLE cotacao
  ADD COLUMN motor_versao        text,
  ADD COLUMN comparador_versao   text NOT NULL,
  ADD COLUMN idade               smallint NOT NULL,
  ADD COLUMN sexo                char(1)  NOT NULL CHECK (sexo IN ('M','F')),
  ADD COLUMN fumante             boolean  NOT NULL,
  ADD COLUMN capitais_escolhidos jsonb,
  ADD COLUMN modo_dev_ficticio   boolean  NOT NULL DEFAULT false;

-- Cotação sem necessidade (jornada "Montar minha proteção") não tem versão de motor.
ALTER TABLE cotacao
  ADD CONSTRAINT cotacao_com_diagnostico_tem_motor
  CHECK (necessidade_id IS NULL OR motor_versao IS NOT NULL);

COMMIT;
