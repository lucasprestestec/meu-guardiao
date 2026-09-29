-- =============================================================================
-- 0002 — Regras do HANDOFF que o schema v1.0 ainda não tinha
--   1. Tarifa carrega fonte_tarifa; FICTICIA nunca chega a PUBLICADO
--   2. Condições gerais versionadas separadamente de produto e tarifa
--   3. tarifa_linha aceita o formato de docs/tarifario-modelo.csv
-- =============================================================================

BEGIN;

-- -----------------------------------------------------------------------------
-- 1. Fonte da tarifa
-- -----------------------------------------------------------------------------

ALTER TABLE tarifa_versao
  ADD COLUMN fonte_tarifa   text NOT NULL DEFAULT 'FICTICIA'
    CONSTRAINT fonte_tarifa_valida CHECK (fonte_tarifa IN ('FICTICIA','SEGURADORA')),
  ADD COLUMN fonte_arquivo  text,
  ADD COLUMN importado_em   timestamptz NOT NULL DEFAULT now();

ALTER TABLE tarifa_linha
  ADD COLUMN capital_minimo numeric(14,2),
  ADD COLUMN capital_maximo numeric(14,2),
  ADD COLUMN fonte_ref      text,
  ADD CONSTRAINT capital_coerente
    CHECK (capital_minimo IS NULL OR capital_maximo IS NULL OR capital_maximo >= capital_minimo);

-- -----------------------------------------------------------------------------
-- 2. Condições gerais versionadas
-- -----------------------------------------------------------------------------

CREATE TABLE condicoes_gerais_versao (
  id               uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  produto_id       uuid NOT NULL REFERENCES produto(id),
  versao           text NOT NULL,
  vigencia_inicio  date NOT NULL,
  url_documento    text,
  hash_sha256      text,
  criado_em        timestamptz NOT NULL DEFAULT now(),
  UNIQUE (produto_id, versao)
);

ALTER TABLE produto_versao
  ADD COLUMN condicoes_gerais_versao_id uuid REFERENCES condicoes_gerais_versao(id);

ALTER TABLE cotacao_item
  ADD COLUMN condicoes_gerais_versao_id uuid REFERENCES condicoes_gerais_versao(id);

-- -----------------------------------------------------------------------------
-- Publicação: v1.0 + condições gerais + tarifa real
-- -----------------------------------------------------------------------------

CREATE OR REPLACE FUNCTION fn_valida_publicacao() RETURNS trigger AS $$
BEGIN
  IF NEW.status = 'PUBLICADO' THEN
    IF EXISTS (
      SELECT 1 FROM mapeamento_cobertura m
      WHERE m.produto_versao_id = NEW.id AND m.confianca <> 'VERIFICADO'
    ) THEN
      RAISE EXCEPTION
        'Produto_versao % nao pode ser publicada: existe mapeamento nao verificado', NEW.id;
    END IF;
    IF NOT EXISTS (SELECT 1 FROM produto_cobertura pc WHERE pc.produto_versao_id = NEW.id) THEN
      RAISE EXCEPTION 'Produto_versao % nao pode ser publicada sem coberturas', NEW.id;
    END IF;
    IF NEW.condicoes_gerais_versao_id IS NULL THEN
      RAISE EXCEPTION
        'Produto_versao % nao pode ser publicada sem condicoes gerais versionadas', NEW.id;
    END IF;
    IF EXISTS (
      SELECT 1 FROM tarifa_versao t
      WHERE t.produto_versao_id = NEW.id AND t.fonte_tarifa = 'FICTICIA'
    ) THEN
      RAISE EXCEPTION
        'Produto_versao % nao pode ser publicada: possui tarifa FICTICIA', NEW.id;
    END IF;
    IF NOT EXISTS (
      SELECT 1 FROM tarifa_versao t
      WHERE t.produto_versao_id = NEW.id AND t.fonte_tarifa = 'SEGURADORA'
    ) THEN
      RAISE EXCEPTION
        'Produto_versao % nao pode ser publicada sem tarifa real da seguradora', NEW.id;
    END IF;
  END IF;
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Tarifa ficticia tambem nao pode entrar depois que o produto ja esta no ar
CREATE OR REPLACE FUNCTION fn_tarifa_nao_ficticia_em_publicado() RETURNS trigger AS $$
BEGIN
  IF NEW.fonte_tarifa = 'FICTICIA' AND EXISTS (
    SELECT 1 FROM produto_versao pv
    WHERE pv.id = NEW.produto_versao_id AND pv.status = 'PUBLICADO'
  ) THEN
    RAISE EXCEPTION 'Tarifa FICTICIA nao pode ser associada a produto_versao PUBLICADO';
  END IF;
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_tarifa_nao_ficticia_em_publicado
  BEFORE INSERT OR UPDATE ON tarifa_versao
  FOR EACH ROW EXECUTE FUNCTION fn_tarifa_nao_ficticia_em_publicado();

-- -----------------------------------------------------------------------------
-- View que a API do consumidor deve usar: so o que pode ser exibido
-- -----------------------------------------------------------------------------

CREATE VIEW vw_produto_exibivel AS
SELECT pv.id AS produto_versao_id, p.id AS produto_id, s.nome AS seguradora,
       p.nome_comercial, pv.versao, pv.condicoes_gerais_versao_id
FROM produto_versao pv
JOIN produto p    ON p.id = pv.produto_id
JOIN seguradora s ON s.id = p.seguradora_id
WHERE pv.status = 'PUBLICADO' AND s.ativa;

COMMIT;
