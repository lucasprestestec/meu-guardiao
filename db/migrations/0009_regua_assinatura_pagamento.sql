-- =============================================================================
-- 0009 — Régua: aguardando assinatura e aguardando pagamento (rodada 3)
-- As duas jornadas (Azos e Icatu) terminam em assinatura eletrônica e o pagamento
-- é coletado no ambiente da seguradora. São dois momentos em que o CLIENTE precisa
-- agir, com prazo, e a proposta morre sozinha se ninguém cobrar.
--   * dois valores novos em status_solicitacao;
--   * prazo_acao: data-limite informada pelo backoffice quando a vez é do cliente.
-- ATENÇÃO: valor de enum não se remove no PostgreSQL. Para desfazer, basta não
-- usar os status novos; a coluna sai com
--   ALTER TABLE solicitacao DROP COLUMN prazo_acao;
-- =============================================================================

ALTER TYPE status_solicitacao ADD VALUE IF NOT EXISTS 'AGUARDANDO_ASSINATURA' AFTER 'EM_PREPARACAO';
ALTER TYPE status_solicitacao ADD VALUE IF NOT EXISTS 'AGUARDANDO_PAGAMENTO' AFTER 'EM_ANALISE';

ALTER TABLE solicitacao ADD COLUMN IF NOT EXISTS prazo_acao date;

COMMENT ON COLUMN solicitacao.prazo_acao IS
  'Data-limite para o cliente assinar ou pagar (informada pelo backoffice, vem da seguradora). Só vale nos status AGUARDANDO_*.';
