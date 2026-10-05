// Dados da empresa. A empresa ainda não existe: os campos ficam em branco, prontos para preencher
// (aparecem no rodapé e na página "Quem somos"). Preencher aqui troca o site todo.
export const EMPRESA = {
  razaoSocial: "DOR Planejamento Financeiro e Corretagem de Seguros Ltda",
  cnpj: "33.538.131/0001-86",
  registroSusep: "",
};

export const EM_BRANCO = "________________";
export const ou = (v: string) => (v.trim() ? v : EM_BRANCO);
