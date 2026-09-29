-- =============================================================================
-- 0003 — IPT de lista fechada
-- O comparador (COBERTURAS_QUE_ATENDEM) e o HANDOFF (regra 6) tratam IPT de
-- lista fechada como cobertura distinta de IFPD, ILP e IPA. O dicionário v1.0
-- não a tinha, o que impedia carregar qualquer produto que a ofereça.
-- =============================================================================

BEGIN;

INSERT INTO cobertura_canonica
  (codigo, nome_canonico, familia, gatilho, unidade_capital, natureza_evento,
   necessidade_atendida, soma_protecao, peso_aderencia_default) VALUES
('IPT_LISTA','Invalidez Permanente Total - Lista Fechada de Perdas','INVALIDEZ',
 'Invalidez permanente total apenas nas situacoes de uma lista fechada de perdas',
 'CAPITAL_UNICO','AMBOS','NEC_INVALIDEZ', true, 0.650);

INSERT INTO classe_equivalencia (codigo, descricao, exige_alerta_gatilho, exige_escopo_dg)
VALUES ('EQ_INVAL_LISTA','Invalidez por lista fechada de perdas', true, false);

INSERT INTO cobertura_classe (codigo_cobertura, codigo_classe)
VALUES ('IPT_LISTA','EQ_INVAL_LISTA');

COMMIT;
