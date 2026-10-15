-- =============================================================================
-- 0012 — Conferência do cliente, registro de acesso ao CPF e lembretes de prazo (rodada 3)
--   * solicitacao_conferencia: depois que a equipe copia a proposta e a DPS para o portal da
--     seguradora, o cliente confere o que foi informado e confirma ou aponta erro. Resposta dada
--     não muda mais (trigger).
--   * acesso_dado_pessoal: cada vez que a equipe abre o CPF inteiro fica registrado quem, quando e de onde.
--   * notificacao.tipo: NULL = mensagem de mudança de status; 'LEMBRETE:...' = lembrete de prazo,
--     com índice único para o mesmo lembrete não ser gerado duas vezes.
-- Só acrescenta. Para desfazer:
--   DROP TABLE solicitacao_conferencia; DROP FUNCTION conferencia_imutavel();
--   DROP TABLE acesso_dado_pessoal;
--   DROP INDEX uq_notificacao_lembrete; ALTER TABLE notificacao DROP COLUMN tipo;
-- =============================================================================

BEGIN;

CREATE TABLE solicitacao_conferencia (
  id             bigserial PRIMARY KEY,
  solicitacao_id uuid NOT NULL REFERENCES solicitacao(id) ON DELETE CASCADE,
  -- hash da DPS registrada no momento do pedido: prova qual declaração o cliente conferiu
  dps_hash       char(64) NOT NULL CHECK (dps_hash ~ '^[0-9a-f]{64}$'),
  solicitada_em  timestamptz NOT NULL DEFAULT now(),
  solicitada_por text NOT NULL,
  resposta       text CHECK (resposta IN ('CONFIRMADA','CONTESTADA')),
  respondida_em  timestamptz,
  nota           text,          -- obrigatória quando CONTESTADA (o que está errado)
  ip             text,
  user_agent     text,
  CONSTRAINT resposta_completa CHECK ((resposta IS NULL) = (respondida_em IS NULL)),
  CONSTRAINT contestacao_explicada CHECK (resposta IS DISTINCT FROM 'CONTESTADA' OR length(btrim(coalesce(nota, ''))) > 0)
);

CREATE INDEX idx_conferencia_solicitacao ON solicitacao_conferencia (solicitacao_id, solicitada_em);

CREATE FUNCTION conferencia_imutavel() RETURNS trigger AS $$
BEGIN
  IF OLD.resposta IS NOT NULL THEN
    RAISE EXCEPTION 'conferência já respondida não pode ser alterada';
  END IF;
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER conferencia_sem_alteracao
  BEFORE UPDATE ON solicitacao_conferencia
  FOR EACH ROW EXECUTE FUNCTION conferencia_imutavel();

CREATE TABLE acesso_dado_pessoal (
  id             bigserial PRIMARY KEY,
  solicitacao_id uuid NOT NULL REFERENCES solicitacao(id) ON DELETE CASCADE,
  campo          text NOT NULL,
  por            text NOT NULL,
  ip             text,
  em             timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX idx_acesso_solicitacao ON acesso_dado_pessoal (solicitacao_id, em);

ALTER TABLE notificacao ADD COLUMN tipo text;

CREATE UNIQUE INDEX uq_notificacao_lembrete
  ON notificacao (solicitacao_id, canal, tipo) WHERE tipo IS NOT NULL;

COMMIT;
