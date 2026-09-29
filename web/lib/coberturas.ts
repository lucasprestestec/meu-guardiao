// Nome que o cliente entende para cada cobertura do dicionário canônico.
// O código (IFPD, IPA...) é dado técnico: quem lê o seguro vê o nome.
export const NOME_COBERTURA: Record<string, string> = {
  MORTE_QC: "Morte por qualquer causa",
  MORTE_ACID: "Morte acidental",
  IPA: "Invalidez por acidente",
  IPTA: "Invalidez total por acidente",
  IFPD: "Invalidez funcional por doença",
  ILP: "Invalidez laborativa por doença",
  IPT_LISTA: "Invalidez total (lista fechada de perdas)",
  DG: "Doenças graves",
  DG_ONCO: "Doenças graves — só câncer",
  DG_CARDIO: "Doenças graves — só cardiovascular",
  DIT: "Diária por incapacidade temporária",
  DIT_A: "Diária por incapacidade (só acidente)",
  DIH: "Diária de internação",
  DIH_UTI: "Diária de internação em UTI",
  RENDA_INVALIDEZ: "Renda mensal por invalidez",
  RENDA_PENSAO: "Pensão por morte",
};

export const nomeCobertura = (codigo: string | null | undefined) =>
  (codigo && NOME_COBERTURA[codigo]) || codigo || "";

const CODIGOS = new RegExp(`\\b(${Object.keys(NOME_COBERTURA).join("|")})\\b`, "g");

/** Troca códigos técnicos que apareçam dentro de uma frase pelo nome da cobertura. */
export const humanizar = (texto: string) =>
  texto.replace(CODIGOS, (c) => nomeCobertura(c).replace(/^./, (x) => x.toLowerCase()));
