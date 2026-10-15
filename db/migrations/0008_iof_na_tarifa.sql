-- =============================================================================
-- 0008 — A tarifa declara se já inclui IOF
-- O prêmio exibido ao cliente inclui IOF (0,38% no seguro de vida). Tarifa
-- líquida: o comparador soma o IOF. Tarifa que já vem com IOF (valores por
-- cobertura da Azos): não soma de novo. Misturar cobra em dobro.
-- Só acrescenta coluna com padrão FALSE: as tarifas existentes (todas fictícias)
-- passam a ser tratadas como líquidas. Para desfazer:
--   ALTER TABLE tarifa_versao DROP COLUMN inclui_iof;
-- =============================================================================

BEGIN;

ALTER TABLE tarifa_versao
  ADD COLUMN inclui_iof boolean NOT NULL DEFAULT false;

COMMENT ON COLUMN tarifa_versao.inclui_iof IS
  'true = os valores da tarifa já incluem IOF; false = tarifa líquida, o comparador soma o IOF.';

COMMIT;
