-- =============================================================================
-- DOR$ INSURANCE SCHEMA v1.0 — PostgreSQL 15+
-- Dicionário universal de coberturas de vida individual (Brasil)
-- =============================================================================
-- Princípios aplicados:
--   1 cliente -> N apolices -> N seguradoras (desde o dia 1)
--   Produto, condicoes gerais e tarifa sao versionados separadamente
--   Nenhuma cotacao e' gravada sem as versoes de regra que a produziram
--   As 7 proibicoes do spec sao CHECK/trigger, nao orientacao
-- =============================================================================

BEGIN;

CREATE EXTENSION IF NOT EXISTS pgcrypto;

-- -----------------------------------------------------------------------------
-- TIPOS
-- -----------------------------------------------------------------------------

CREATE TYPE familia_cobertura AS ENUM (
  'MORTE','INVALIDEZ','DOENCA','RENDA','HOSPITALAR','SERVICO','ACESSORIA'
);

CREATE TYPE unidade_capital AS ENUM (
  'CAPITAL_UNICO','DIARIA','RENDA_MENSAL','PERCENTUAL_TABELA','REEMBOLSO','SERVICO'
);

CREATE TYPE natureza_evento AS ENUM ('ACIDENTE','DOENCA','AMBOS');

CREATE TYPE tipo_capital AS ENUM ('NIVELADO','DECRESCENTE','ATUALIZADO_INDICE');

CREATE TYPE temporalidade AS ENUM ('VITALICIO','TEMPORARIO','ATE_IDADE');

CREATE TYPE tipo_renovacao AS ENUM (
  'AUTOMATICA_GARANTIDA','AUTOMATICA_NAO_GARANTIDA','NAO_RENOVAVEL'
);

CREATE TYPE tipo_reajuste AS ENUM (
  'PREMIO_NIVELADO','FAIXA_ETARIA','ANUAL_INDICE','SINISTRALIDADE','MISTO'
);

CREATE TYPE nivel_confianca AS ENUM ('VERIFICADO','INFERIDO','A_VERIFICAR');

CREATE TYPE status_publicacao AS ENUM ('RASCUNHO','HOMOLOGACAO','PUBLICADO','SUSPENSO');

-- -----------------------------------------------------------------------------
-- CAMADA 1 — DICIONARIO CANONICO
-- -----------------------------------------------------------------------------

CREATE TABLE cobertura_canonica (
  codigo                  text PRIMARY KEY,
  nome_canonico           text        NOT NULL,
  familia                 familia_cobertura NOT NULL,
  gatilho                 text        NOT NULL,
  unidade_capital         unidade_capital   NOT NULL,
  natureza_evento         natureza_evento   NOT NULL,
  necessidade_atendida    text,                    -- chave de saida do Motor DOR$
  referencia_capital      text REFERENCES cobertura_canonica(codigo),
  antecipa_capital_de     text REFERENCES cobertura_canonica(codigo),
  soma_protecao           boolean     NOT NULL DEFAULT true,
  peso_aderencia_default  numeric(4,3) NOT NULL DEFAULT 1.000,
  criado_em               timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT codigo_maiusculo CHECK (codigo = upper(codigo)),
  -- Proibicao 3: acessoria nunca soma protecao
  CONSTRAINT acessoria_nao_soma
    CHECK (familia <> 'ACESSORIA' OR (soma_protecao = false AND peso_aderencia_default = 0)),
  -- Proibicao 2: cobertura que antecipa nao soma capital
  CONSTRAINT antecipacao_nao_soma
    CHECK (antecipa_capital_de IS NULL OR soma_protecao = false)
);

CREATE TABLE cobertura_incompativel (
  codigo_a text NOT NULL REFERENCES cobertura_canonica(codigo),
  codigo_b text NOT NULL REFERENCES cobertura_canonica(codigo),
  motivo   text NOT NULL,
  PRIMARY KEY (codigo_a, codigo_b),
  CONSTRAINT ordem_canonica CHECK (codigo_a < codigo_b)
);

CREATE TABLE classe_equivalencia (
  codigo              text PRIMARY KEY,
  descricao           text NOT NULL,
  exige_alerta_gatilho boolean NOT NULL DEFAULT false,
  exige_escopo_dg      boolean NOT NULL DEFAULT false
);

CREATE TABLE cobertura_classe (
  codigo_cobertura text NOT NULL REFERENCES cobertura_canonica(codigo),
  codigo_classe    text NOT NULL REFERENCES classe_equivalencia(codigo),
  PRIMARY KEY (codigo_cobertura, codigo_classe)
);

CREATE TABLE doenca_canonica (
  codigo    text PRIMARY KEY,
  nome      text NOT NULL,
  grupo     text NOT NULL,        -- ONCOLOGICO, CARDIOVASCULAR, NEUROLOGICO, ORGAO, OUTRO
  cid10     text[]                -- referencia, nao definicao contratual
);

-- -----------------------------------------------------------------------------
-- CAMADA 3 — SEGURADORA, PRODUTO, VERSAO
-- -----------------------------------------------------------------------------

CREATE TABLE seguradora (
  id            uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  nome          text NOT NULL UNIQUE,
  cnpj          text UNIQUE,
  codigo_susep  text,
  ativa         boolean NOT NULL DEFAULT true
);

CREATE TABLE produto (
  id             uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  seguradora_id  uuid NOT NULL REFERENCES seguradora(id),
  nome_comercial text NOT NULL,
  ramo_susep     text NOT NULL,
  processo_susep text,
  UNIQUE (seguradora_id, nome_comercial)
);

CREATE TABLE produto_versao (
  id                    uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  produto_id            uuid NOT NULL REFERENCES produto(id),
  versao                text NOT NULL,
  vigencia_inicio       date NOT NULL,
  vigencia_fim          date,
  url_condicoes_gerais  text,
  status                status_publicacao NOT NULL DEFAULT 'RASCUNHO',
  criado_em             timestamptz NOT NULL DEFAULT now(),
  UNIQUE (produto_id, versao),
  CONSTRAINT vigencia_coerente CHECK (vigencia_fim IS NULL OR vigencia_fim > vigencia_inicio)
);

CREATE INDEX idx_produto_versao_vigente
  ON produto_versao (produto_id, vigencia_inicio DESC)
  WHERE status = 'PUBLICADO';

-- -----------------------------------------------------------------------------
-- CAMADA 2 — ATRIBUTOS NORMALIZADOS (coracao do schema)
-- -----------------------------------------------------------------------------

CREATE TABLE produto_cobertura (
  id                          uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  produto_versao_id           uuid NOT NULL REFERENCES produto_versao(id) ON DELETE CASCADE,
  codigo_cobertura            text NOT NULL REFERENCES cobertura_canonica(codigo),
  obrigatoria                 boolean NOT NULL DEFAULT false,

  -- capital
  tipo_capital                tipo_capital NOT NULL,
  indice_atualizacao          text,
  capital_minimo              numeric(14,2),
  capital_maximo              numeric(14,2),
  referencia_capital          text REFERENCES cobertura_canonica(codigo),
  limite_percentual_referencia numeric(5,2),

  -- temporalidade
  temporalidade               temporalidade NOT NULL,
  idade_limite_cobertura      smallint,
  idade_min_contratacao       smallint NOT NULL,
  idade_max_contratacao       smallint NOT NULL,

  -- renovacao e reajuste
  renovacao                   tipo_renovacao NOT NULL,
  reajuste                    tipo_reajuste  NOT NULL,
  periodicidade_reagravamento_anos smallint,

  -- carencia e franquia
  carencia_dias_geral         smallint NOT NULL DEFAULT 0,
  carencia_dias_especifica    jsonb    NOT NULL DEFAULT '{}'::jsonb,
  carencia_suicidio_dias      smallint NOT NULL DEFAULT 730,
  franquia_dias               smallint,
  periodo_maximo_indenizacao_dias smallint,
  periodo_sobrevivencia_dias  smallint,

  -- escopo DG
  escopo_dg                   jsonb,

  -- restricoes
  exclusoes                   text[] NOT NULL DEFAULT '{}',
  agravo_profissao_aplicavel  boolean NOT NULL DEFAULT true,
  agravo_esporte_aplicavel    boolean NOT NULL DEFAULT true,
  cobertura_geografica        text NOT NULL DEFAULT 'GLOBAL',

  -- economicos
  valor_resgate               boolean NOT NULL DEFAULT false,
  portabilidade               boolean NOT NULL DEFAULT false,
  comissionamento_pct         numeric(5,2),

  UNIQUE (produto_versao_id, codigo_cobertura),

  CONSTRAINT idade_coerente CHECK (idade_max_contratacao >= idade_min_contratacao),
  CONSTRAINT ate_idade_exige_limite
    CHECK (temporalidade <> 'ATE_IDADE' OR idade_limite_cobertura IS NOT NULL),
  CONSTRAINT indice_exige_tipo
    CHECK (tipo_capital <> 'ATUALIZADO_INDICE' OR indice_atualizacao IS NOT NULL),
  CONSTRAINT limite_exige_referencia
    CHECK (limite_percentual_referencia IS NULL OR referencia_capital IS NOT NULL),
  -- Proibicao 4: DG sem escopo_dg nao existe
  CONSTRAINT dg_exige_escopo CHECK (
    codigo_cobertura NOT IN ('DG','DG_ONCO','DG_CARDIO')
    OR (escopo_dg IS NOT NULL
        AND escopo_dg ? 'rol'
        AND escopo_dg ? 'periodo_sobrevivencia_dias')
  ),
  -- diaria exige franquia e teto declarados
  CONSTRAINT diaria_exige_limites CHECK (
    codigo_cobertura NOT IN ('DIT','DIT_A','DIH','DIH_UTI')
    OR (franquia_dias IS NOT NULL AND periodo_maximo_indenizacao_dias IS NOT NULL)
  )
);

CREATE INDEX idx_produto_cobertura_codigo ON produto_cobertura (codigo_cobertura);
CREATE INDEX idx_produto_cobertura_escopo ON produto_cobertura USING gin (escopo_dg);

-- -----------------------------------------------------------------------------
-- CAMADA 4 — ADAPTADORES / MAPEAMENTO
-- -----------------------------------------------------------------------------

CREATE TABLE mapeamento_cobertura (
  id                   uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  produto_versao_id    uuid NOT NULL REFERENCES produto_versao(id) ON DELETE CASCADE,
  rotulo_original      text NOT NULL,
  codigo_cobertura     text NOT NULL REFERENCES cobertura_canonica(codigo),
  confianca            nivel_confianca NOT NULL DEFAULT 'A_VERIFICAR',
  fonte_documento      text,
  fonte_pagina         text,
  revisado_por         text,
  revisado_em          timestamptz,
  observacao           text,
  UNIQUE (produto_versao_id, rotulo_original),
  CONSTRAINT verificado_exige_fonte CHECK (
    confianca <> 'VERIFICADO'
    OR (fonte_documento IS NOT NULL AND revisado_por IS NOT NULL AND revisado_em IS NOT NULL)
  )
);

-- Proibicao 6: produto so vai a PUBLICADO com todos os mapeamentos VERIFICADO
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
  END IF;
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_valida_publicacao
  BEFORE INSERT OR UPDATE OF status ON produto_versao
  FOR EACH ROW EXECUTE FUNCTION fn_valida_publicacao();

-- -----------------------------------------------------------------------------
-- TARIFA (versionada separadamente do produto)
-- -----------------------------------------------------------------------------

CREATE TABLE tarifa_versao (
  id                uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  produto_versao_id uuid NOT NULL REFERENCES produto_versao(id),
  versao            text NOT NULL,
  vigencia_inicio   date NOT NULL,
  vigencia_fim      date,
  UNIQUE (produto_versao_id, versao)
);

CREATE TABLE tarifa_linha (
  id                uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  tarifa_versao_id  uuid NOT NULL REFERENCES tarifa_versao(id) ON DELETE CASCADE,
  codigo_cobertura  text NOT NULL REFERENCES cobertura_canonica(codigo),
  idade_min         smallint NOT NULL,
  idade_max         smallint NOT NULL,
  sexo              char(1),              -- M, F ou NULL = unissex
  fumante           boolean,              -- NULL = indiferente
  classe_risco      text,
  taxa_por_mil      numeric(12,6),        -- capital unico
  premio_por_unidade numeric(12,6),       -- diaria / renda mensal
  CONSTRAINT faixa_coerente CHECK (idade_max >= idade_min),
  CONSTRAINT uma_metrica CHECK (num_nonnulls(taxa_por_mil, premio_por_unidade) = 1)
);

CREATE INDEX idx_tarifa_lookup
  ON tarifa_linha (tarifa_versao_id, codigo_cobertura, idade_min, idade_max);

CREATE TABLE agravo (
  id               uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  tarifa_versao_id uuid NOT NULL REFERENCES tarifa_versao(id) ON DELETE CASCADE,
  tipo             text NOT NULL,          -- PROFISSAO, ESPORTE, IMC, CLINICO
  chave            text NOT NULL,
  multiplicador    numeric(6,3) NOT NULL CHECK (multiplicador > 0),
  UNIQUE (tarifa_versao_id, tipo, chave)
);

-- -----------------------------------------------------------------------------
-- CLIENTE, NECESSIDADE, APOLICE, COTACAO
-- -----------------------------------------------------------------------------

CREATE TABLE cliente (
  id          uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  nome        text,
  email       text,
  criado_em   timestamptz NOT NULL DEFAULT now()
);

-- Saida do Motor DOR$, versionada e auditavel
CREATE TABLE necessidade (
  id                 uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  cliente_id         uuid NOT NULL REFERENCES cliente(id),
  motor_versao       text NOT NULL,
  entradas           jsonb NOT NULL,      -- respostas do diagnostico
  protection_score   smallint CHECK (protection_score BETWEEN 0 AND 100),
  calculado_em       timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE necessidade_item (
  necessidade_id    uuid NOT NULL REFERENCES necessidade(id) ON DELETE CASCADE,
  codigo_cobertura  text NOT NULL REFERENCES cobertura_canonica(codigo),
  capital_necessario numeric(14,2) NOT NULL,
  peso              numeric(4,3) NOT NULL,
  justificativa     text NOT NULL,        -- deterministica, gerada pelo motor
  PRIMARY KEY (necessidade_id, codigo_cobertura)
);

-- 1 cliente -> N apolices -> N seguradoras
CREATE TABLE apolice (
  id                uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  cliente_id        uuid NOT NULL REFERENCES cliente(id),
  seguradora_id     uuid NOT NULL REFERENCES seguradora(id),
  produto_versao_id uuid REFERENCES produto_versao(id),
  numero_apolice    text,
  origem            text NOT NULL DEFAULT 'INFORMADA',  -- INFORMADA, UPLOAD, EMITIDA, OPEN_INSURANCE
  inicio_vigencia   date,
  premio_mensal     numeric(12,2),
  status            text NOT NULL DEFAULT 'ATIVA'
);

CREATE INDEX idx_apolice_cliente ON apolice (cliente_id);

CREATE TABLE apolice_cobertura (
  apolice_id        uuid NOT NULL REFERENCES apolice(id) ON DELETE CASCADE,
  codigo_cobertura  text NOT NULL REFERENCES cobertura_canonica(codigo),
  capital           numeric(14,2),
  valor_diaria      numeric(12,2),
  confianca         nivel_confianca NOT NULL DEFAULT 'A_VERIFICAR',
  PRIMARY KEY (apolice_id, codigo_cobertura)
);

CREATE TABLE cotacao (
  id                uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  cliente_id        uuid NOT NULL REFERENCES cliente(id),
  necessidade_id    uuid REFERENCES necessidade(id),
  schema_versao     text NOT NULL DEFAULT '1.0',
  criada_em         timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE cotacao_item (
  id                uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  cotacao_id        uuid NOT NULL REFERENCES cotacao(id) ON DELETE CASCADE,
  produto_versao_id uuid NOT NULL REFERENCES produto_versao(id),
  tarifa_versao_id  uuid NOT NULL REFERENCES tarifa_versao(id),
  premio_mensal     numeric(12,2) NOT NULL,
  premio_ano_10     numeric(12,2),
  premio_ano_20     numeric(12,2),
  premio_ano_30     numeric(12,2),
  aderencia_total   numeric(5,4),
  motivo_ranking    jsonb
);

-- Proibicao 5: reajuste nao nivelado exige projecao
CREATE OR REPLACE FUNCTION fn_exige_projecao() RETURNS trigger AS $$
DECLARE tem_reajuste boolean;
BEGIN
  SELECT EXISTS (
    SELECT 1 FROM produto_cobertura pc
    WHERE pc.produto_versao_id = NEW.produto_versao_id
      AND pc.reajuste <> 'PREMIO_NIVELADO'
  ) INTO tem_reajuste;

  IF tem_reajuste AND (NEW.premio_ano_10 IS NULL
                    OR NEW.premio_ano_20 IS NULL
                    OR NEW.premio_ano_30 IS NULL) THEN
    RAISE EXCEPTION
      'Produto com reajuste nao nivelado exige projecao de premio em 10/20/30 anos';
  END IF;
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_exige_projecao
  BEFORE INSERT OR UPDATE ON cotacao_item
  FOR EACH ROW EXECUTE FUNCTION fn_exige_projecao();

-- -----------------------------------------------------------------------------
-- VIEW: protecao consolidada do cliente (Proibicao 1 e 3 aplicadas)
-- -----------------------------------------------------------------------------

CREATE VIEW vw_protecao_cliente AS
SELECT
  a.cliente_id,
  cc.familia,
  ac.codigo_cobertura,
  cc.nome_canonico,
  sum(coalesce(ac.capital, 0))      AS capital_total,
  sum(coalesce(ac.valor_diaria, 0)) AS diaria_total,
  count(*)                          AS qtd_apolices
FROM apolice a
JOIN apolice_cobertura ac ON ac.apolice_id = a.id
JOIN cobertura_canonica cc ON cc.codigo = ac.codigo_cobertura
WHERE a.status = 'ATIVA'
  AND cc.soma_protecao = true          -- exclui ADT, sorteio, assistencias
GROUP BY a.cliente_id, cc.familia, ac.codigo_cobertura, cc.nome_canonico;

-- =============================================================================
-- SEED — CATALOGO CANONICO v1.0
-- =============================================================================

INSERT INTO cobertura_canonica
  (codigo, nome_canonico, familia, gatilho, unidade_capital, natureza_evento,
   necessidade_atendida, soma_protecao, peso_aderencia_default) VALUES
-- MORTE
('MORTE_QC','Morte por Qualquer Causa','MORTE',
 'Falecimento do segurado por qualquer causa coberta','CAPITAL_UNICO','AMBOS',
 'NEC_MORTE', true, 1.000),
('MORTE_ACID','Morte Acidental (adicional)','MORTE',
 'Falecimento decorrente exclusivamente de acidente pessoal','CAPITAL_UNICO','ACIDENTE',
 'NEC_MORTE', true, 0.300),
('FUNERAL_IND','Assistencia Funeral Individual','SERVICO',
 'Falecimento do segurado','SERVICO','AMBOS', NULL, false, 0.100),
('FUNERAL_FAM','Assistencia Funeral Familiar','SERVICO',
 'Falecimento do segurado ou de dependente previsto','SERVICO','AMBOS', NULL, false, 0.100),
-- INVALIDEZ
('IPA','Invalidez Permanente Total ou Parcial por Acidente','INVALIDEZ',
 'Invalidez permanente por acidente, indenizada por tabela de percentuais','PERCENTUAL_TABELA','ACIDENTE',
 'NEC_INVALIDEZ', true, 0.700),
('IPTA','Invalidez Permanente Total por Acidente','INVALIDEZ',
 'Invalidez permanente total por acidente','CAPITAL_UNICO','ACIDENTE',
 'NEC_INVALIDEZ', true, 0.600),
('IFPD','Invalidez Funcional Permanente Total por Doenca','INVALIDEZ',
 'Perda da existencia independente por doenca, conforme criterio funcional','CAPITAL_UNICO','DOENCA',
 'NEC_INVALIDEZ', true, 1.000),
('ILP','Invalidez Laborativa Permanente Total por Doenca','INVALIDEZ',
 'Incapacidade permanente para a atividade laborativa principal','CAPITAL_UNICO','DOENCA',
 'NEC_INVALIDEZ', true, 1.000),
('ISENCAO_PREMIO','Isencao de Pagamento de Premio','SERVICO',
 'Evento previsto suspende a obrigacao de pagar premio, mantendo a apolice','SERVICO','AMBOS',
 NULL, false, 0.200),
-- DOENCA
('DG','Doencas Graves','DOENCA',
 'Diagnostico de doenca do rol contratado, cumprido o periodo de sobrevivencia','CAPITAL_UNICO','DOENCA',
 'NEC_DOENCA_GRAVE', true, 1.000),
('DG_ONCO','Doencas Graves - Escopo Oncologico','DOENCA',
 'Diagnostico de cancer conforme definicao contratual','CAPITAL_UNICO','DOENCA',
 'NEC_DOENCA_GRAVE', true, 0.500),
('DG_CARDIO','Doencas Graves - Escopo Cardiovascular','DOENCA',
 'Evento cardiovascular conforme rol contratado','CAPITAL_UNICO','DOENCA',
 'NEC_DOENCA_GRAVE', true, 0.400),
('SOM','Segunda Opiniao Medica','SERVICO',
 'Diagnostico de condicao elegivel','SERVICO','DOENCA', NULL, false, 0.050),
-- RENDA
('DIT','Diaria de Incapacidade Temporaria','RENDA',
 'Afastamento temporario da atividade, por acidente ou doenca, apos franquia','DIARIA','AMBOS',
 'NEC_RENDA', true, 1.000),
('DIT_A','Diaria de Incapacidade Temporaria por Acidente','RENDA',
 'Afastamento temporario da atividade por acidente, apos franquia','DIARIA','ACIDENTE',
 'NEC_RENDA', true, 0.400),
('RENDA_INVALIDEZ','Renda Mensal por Invalidez','RENDA',
 'Invalidez coberta, paga em parcelas mensais por prazo certo','RENDA_MENSAL','AMBOS',
 'NEC_INVALIDEZ', true, 0.900),
('RENDA_PENSAO','Pensao por Morte aos Beneficiarios','RENDA',
 'Morte do segurado, paga em parcelas mensais','RENDA_MENSAL','AMBOS',
 'NEC_MORTE', true, 0.900),
-- HOSPITALAR
('DIH','Diaria de Internacao Hospitalar','HOSPITALAR',
 'Internacao hospitalar acima da franquia','DIARIA','AMBOS',
 'NEC_HOSPITALAR', true, 0.500),
('DIH_UTI','Diaria de Internacao em UTI','HOSPITALAR',
 'Internacao em UTI','DIARIA','AMBOS',
 'NEC_HOSPITALAR', true, 0.500),
('CIRURGIA','Eventos Cirurgicos','HOSPITALAR',
 'Realizacao de procedimento constante da tabela contratada','PERCENTUAL_TABELA','AMBOS',
 'NEC_HOSPITALAR', true, 0.400),
-- ACESSORIA
('SORTEIO','Sorteio / Titulo de Capitalizacao anexo','ACESSORIA',
 'Contemplacao em sorteio','SERVICO','AMBOS', NULL, false, 0.000),
('ASSIST_PESSOAL','Assistencias diversas','ACESSORIA',
 'Acionamento de servico de assistencia','SERVICO','AMBOS', NULL, false, 0.000);

-- ADT depende de MORTE_QC, por isso entra depois
INSERT INTO cobertura_canonica
  (codigo, nome_canonico, familia, gatilho, unidade_capital, natureza_evento,
   necessidade_atendida, antecipa_capital_de, soma_protecao, peso_aderencia_default) VALUES
('ADT','Antecipacao por Doenca Terminal','MORTE',
 'Diagnostico de doenca terminal com expectativa de vida abaixo do limite previsto',
 'CAPITAL_UNICO','DOENCA', NULL, 'MORTE_QC', false, 0.200);

-- Incompatibilidades conhecidas
INSERT INTO cobertura_incompativel (codigo_a, codigo_b, motivo) VALUES
('IPA','IPTA','Mesma natureza e gatilho concorrente: um produto oferece uma ou outra'),
('DG','DG_ONCO','Escopo restrito e subconjunto do escopo amplo'),
('DG','DG_CARDIO','Escopo restrito e subconjunto do escopo amplo'),
('DIT','DIT_A','DIT_A e subconjunto de DIT');

-- Classes de equivalencia
INSERT INTO classe_equivalencia (codigo, descricao, exige_alerta_gatilho, exige_escopo_dg) VALUES
('EQ_MORTE','Morte por qualquer causa', false, false),
('EQ_MORTE_ACID','Morte acidental', false, false),
('EQ_INVAL_ACID','Invalidez por acidente', true,  false),
('EQ_INVAL_DOENCA','Invalidez por doenca', true,  false),
('EQ_DG','Doencas graves', true,  true),
('EQ_RENDA_TEMP','Renda por incapacidade temporaria', true, false),
('EQ_RENDA_LONGA','Renda mensal de longo prazo', true, false),
('EQ_HOSPITALAR','Cobertura hospitalar', false, false);

INSERT INTO cobertura_classe (codigo_cobertura, codigo_classe) VALUES
('MORTE_QC','EQ_MORTE'),
('RENDA_PENSAO','EQ_RENDA_LONGA'),
('MORTE_ACID','EQ_MORTE_ACID'),
('IPA','EQ_INVAL_ACID'),
('IPTA','EQ_INVAL_ACID'),
('IFPD','EQ_INVAL_DOENCA'),
('ILP','EQ_INVAL_DOENCA'),
('RENDA_INVALIDEZ','EQ_RENDA_LONGA'),
('DG','EQ_DG'),
('DG_ONCO','EQ_DG'),
('DG_CARDIO','EQ_DG'),
('DIT','EQ_RENDA_TEMP'),
('DIT_A','EQ_RENDA_TEMP'),
('DIH','EQ_HOSPITALAR'),
('DIH_UTI','EQ_HOSPITALAR'),
('CIRURGIA','EQ_HOSPITALAR');

COMMIT;
