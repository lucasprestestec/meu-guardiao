import { brl } from "@/lib/format";

/** Nomes em português dos campos da proposta (backoffice e conferência do cliente). */
export const ROTULO_CAMPO: Record<string, string> = {
  nome_social: "Nome social", sexo: "Sexo", renda_mensal: "Renda mensal", peso_kg: "Peso (kg)",
  altura_cm: "Altura (cm)", cep: "CEP", logradouro: "Logradouro", numero_endereco: "Número",
  complemento: "Complemento", bairro: "Bairro", pep: "Pessoa politicamente exposta",
  fumante_24_meses: "Fumou nos últimos 24 meses", aposentado: "Aposentado", nacionalidade: "Nacionalidade",
  pais_nascimento: "País de nascimento", pais_residencia: "País de residência atual",
  pais_residencia_fiscal: "País de residência fiscal", us_person: "US Person", origem_recurso: "Origem do recurso",
};

export function valorCampo(k: string, v: string | number | boolean): string {
  if (typeof v === "boolean") return v ? "Sim" : "Não";
  if (k === "renda_mensal") return brl(Number(v));
  if (k === "sexo") return v === "M" ? "Masculino" : "Feminino";
  return String(v);
}
