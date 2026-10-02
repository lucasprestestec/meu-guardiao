// Dados da empresa. A empresa ainda não existe: os campos ficam em branco, prontos para preencher
// (aparecem no rodapé e na página "Quem somos"). Preencher aqui troca o site todo.
export const EMPRESA = {
  razaoSocial: "",
  cnpj: "",
  registroSusep: "",
};

export const EM_BRANCO = "________________";
export const ou = (v: string) => (v.trim() ? v : EM_BRANCO);
