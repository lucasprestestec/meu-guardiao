// Chaves de recursos da interface. Desligado = o código continua no projeto, só não aparece.
// Para religar, troque o valor aqui (ou defina a variável NEXT_PUBLIC_RECURSO_* = "1" no build).
//
// Rodada 2 do cliente: a regra de ponderação do Protection Score e da nota de aderência
// precisa ser revista e validada antes de voltarem. O comparador segue calculando os dois.
const liga = (v: string | undefined, padrao: boolean) => (v === undefined ? padrao : v === "1");

export const RECURSOS = {
  /** Círculo com o Protection Score no Mapa de Proteção. */
  protectionScore: liga(process.env.NEXT_PUBLIC_RECURSO_SCORE, false),
  /** Barra e percentual de aderência por produto e por cobertura. */
  aderencia: liga(process.env.NEXT_PUBLIC_RECURSO_ADERENCIA, false),
  /** Selos "recomendada", "menor preço" e "maior proteção" e as abas por critério. */
  destaques: liga(process.env.NEXT_PUBLIC_RECURSO_DESTAQUES, false),
  /** Tela de captura de contato (com consentimentos) antes do Mapa. */
  capturaDeContato: liga(process.env.NEXT_PUBLIC_RECURSO_CAPTURA_CONTATO, true),
};
