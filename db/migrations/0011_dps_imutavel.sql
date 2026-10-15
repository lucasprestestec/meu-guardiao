-- =============================================================================
-- 0011 — DPS (declaração pessoal de saúde) guardada de forma imutável (rodada 3)
-- A DPS é declaração do segurado e a equipe a transcreve para o portal da seguradora. Erro de
-- transcrição pode virar negativa de sinistro, então o que o cliente respondeu fica registrado
-- exatamente como foi, com o TEXTO das perguntas que ele viu, a versão do questionário, data e hora,
-- e um hash. Esse registro não pode ser editado, nem pelo backoffice.
-- DADO SENSÍVEL (saúde): em produção exige criptografia e controle de acesso.
-- Apagar só por procedimento explícito (LGPD): SET LOCAL dor.apagar_dps = 'sim' na transação.
-- Para desfazer a migração: DROP TABLE dps_resposta; DROP FUNCTION dps_resposta_imutavel();
-- =============================================================================

BEGIN;

CREATE TABLE dps_resposta (
  id                  bigserial PRIMARY KEY,
  solicitacao_id      uuid NOT NULL UNIQUE REFERENCES solicitacao(id) ON DELETE CASCADE,
  perfil              text NOT NULL,
  questionario_versao text NOT NULL,
  -- false = a redação ainda não foi conferida com a seguradora; só existe em demonstração
  redacao_confirmada  boolean NOT NULL,
  conteudo            jsonb NOT NULL,   -- perguntas (texto exato) + respostas
  hash_sha256         char(64) NOT NULL CHECK (hash_sha256 ~ '^[0-9a-f]{64}$'),
  respondido_em       timestamptz NOT NULL DEFAULT now(),
  ip                  text,
  user_agent          text
);

CREATE FUNCTION dps_resposta_imutavel() RETURNS trigger AS $$
BEGIN
  IF TG_OP = 'DELETE' AND current_setting('dor.apagar_dps', true) = 'sim' THEN
    RETURN OLD;
  END IF;
  RAISE EXCEPTION 'dps_resposta é imutável: não pode ser % (guarda a declaração original do cliente)', TG_OP;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER dps_resposta_sem_alteracao
  BEFORE UPDATE OR DELETE ON dps_resposta
  FOR EACH ROW EXECUTE FUNCTION dps_resposta_imutavel();

COMMIT;
