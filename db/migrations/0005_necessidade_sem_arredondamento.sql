-- =============================================================================
-- 0005 — Necessidade gravada exatamente como o Motor a calculou
-- O Motor trabalha em ponto flutuante (ex.: diária de R$ 833,3333...). Gravar
-- em numeric(14,2) arredondava o valor e a cotação refeita a partir do banco
-- divergia do cálculo original em centavos. double precision devolve o mesmo
-- número que o Motor produziu; o arredondamento fica só na exibição.
-- =============================================================================

BEGIN;

ALTER TABLE necessidade_item
  ALTER COLUMN capital_necessario TYPE double precision,
  ALTER COLUMN valor_existente    TYPE double precision,
  ALTER COLUMN peso               TYPE double precision;

COMMIT;
