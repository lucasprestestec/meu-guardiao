// Tipos e chamadas da API. Os formatos vêm de docs/contrato-*.json e de api/*.py.

export type Necessidade = {
  codigo: string;
  rotulo: string;
  unidade: "CAPITAL" | "DIARIA";
  valor_necessario: number;
  valor_existente: number;
  gap: number;
  cobertura: number;
  peso: number;
  justificativa: string;
  memoria: Record<string, number>;
};

export type Mapa = {
  necessidade_id: string;
  versao_motor: string;
  protection_score: number;
  vulnerabilidade_principal: string | null;
  alertas: string[];
  necessidades: Necessidade[];
};

export type ItemOpcao = {
  necessidade: string;
  cobertura: string | null;
  capital_contratado: number;
  premio_mensal: number;
  aderencia: number;
  observacoes: string[];
};

export type Opcao = {
  produto_versao_id: string;
  produto: { seguradora: string; nome: string; fonte_tarifa: string };
  exibivel_ao_consumidor: boolean;
  premio_mensal: number;
  aderencia_total: number;
  coberturas_ausentes: string[];
  itens: ItemOpcao[];
  projecao_premio: { ano_10: number; ano_20: number; ano_30: number; premissa: string } | null;
  alertas: string[];
};

export type Comparacao = {
  cotacao_id: string | null;
  motor_versao: string | null;
  modo_demonstracao: boolean;
  opcoes: Opcao[];
  destaques: { recomendado: string | null; menor_preco: string | null; maior_protecao: string | null };
  excluidos: { produto: string; motivo: string }[];
  alertas_gerais: string[];
};

export type PassoRegua = {
  codigo: string;
  rotulo: string;
  descricao: string;
  estado: "CONCLUIDO" | "EM_ANDAMENTO" | "AGUARDANDO";
  em: string | null;
};

export type Plano = {
  produto_versao_id: string;
  seguradora: string;
  produto: string;
  premio_mensal: number;
  aderencia_total: number | null;
  itens: ItemOpcao[];
  projecao_premio: { ano_10: number; ano_20: number; ano_30: number } | null;
};

export type Notificacao = { canal: "WHATSAPP" | "EMAIL"; mensagem: string; criada_em: string };

export type Acompanhamento = {
  id: string;
  status: string;
  status_desde: string;
  pendencia: string | null;
  prazo_acao: string | null;
  numero_apolice: string | null;
  demonstracao: boolean;
  primeiro_nome: string;
  criada_em: string;
  regua: PassoRegua[];
  plano: Plano;
  notificacoes: Notificacao[];
};

export type LinhaFila = {
  id: string;
  nome: string;
  seguradora: string;
  produto: string;
  premio_mensal: number;
  status: string;
  pendencia: string | null;
  prazo_acao: string | null;
  status_desde: string;
  com_quem: "NOS" | "CLIENTE" | "SEGURADORA" | "FIM";
  demonstracao: boolean;
};

/** O que o formulário deve pedir para a seguradora escolhida (GET /v1/proposta/campos). */
export type CamposProposta = {
  perfil: "COMUM" | "AZOS" | "ICATU";
  exigidos: string[];
  parentescos: string[];
  lista_parentesco_completa: boolean;
  aceita_beneficiarios_legais: boolean;
  origens_recurso: string[];
  aposentado: { valor: string; texto: string }[];
  max_beneficiarios: number;
};

/** Pergunta da DPS com a redação da seguradora (GET /v1/dps/questionario). */
export type PerguntaDps = {
  id: string;
  texto: string;
  tipo: "sim_nao" | "unica" | "multipla" | "numero";
  opcoes: string[];
  exclusiva: string | null;
  depende: { id: string; valor: boolean } | null;
  unidade: string | null;
};
export type QuestionarioDps = {
  existe: boolean;
  perfil?: string;
  versao?: string;
  confirmado?: boolean;
  perguntas?: PerguntaDps[];
};
export type DpsFicha = {
  perfil: string;
  versao: string;
  redacao_confirmada: boolean;
  respondido_em: string;
  hash: string;
  itens: { id: string; pergunta: string; resposta_texto: string }[];
};

export type PropostaFicha = {
  perfil: string;
  campos: Record<string, string | number | boolean | null>;
  beneficiarios_legais: boolean;
  beneficiarios: { nome: string; data_nascimento: string; parentesco: string; percentual: number }[];
};

export type Ficha = {
  id: string;
  status: string;
  status_desde: string;
  com_quem: LinhaFila["com_quem"];
  pendencia: string | null;
  prazo_acao: string | null;
  proposta: PropostaFicha;
  dps: DpsFicha | null;
  numero_apolice: string | null;
  demonstracao: boolean;
  condicoes_gerais: { url: string | null; versao: string | null };
  recados: { checkout: string | null; personalizacao: string | null };
  proximos_status: string[];
  cliente: {
    nome: string;
    celular: string;
    email: string;
    cidade: string | null;
    uf: string | null;
    profissao: string | null;
    faixa_renda: string | null;
    estado_civil: string | null;
    data_nascimento: string;
    cpf_final: string;
  };
  plano: Plano;
  regua: PassoRegua[];
  historico: { status: string; nota: string | null; por: string; em: string }[];
  notificacoes: Notificacao[];
};

export class ErroApi extends Error {
  constructor(public status: number, message: string) {
    super(message);
  }
}

function mensagemDeErro(corpo: unknown): string {
  const d = (corpo as { detail?: unknown })?.detail;
  if (typeof d === "string") return d;
  if (Array.isArray(d)) {
    // erros de validação do FastAPI: pega a mensagem do primeiro campo
    const e = d[0] as { loc?: string[]; msg?: string };
    const campo = e?.loc?.slice(1).join(".") ?? "";
    return `${campo ? campo + ": " : ""}${e?.msg ?? "dados inválidos"}`;
  }
  return "Não foi possível concluir. Tente novamente.";
}

export async function api<T>(
  caminho: string,
  opcoes: { method?: string; corpo?: unknown; headers?: Record<string, string>; signal?: AbortSignal } = {},
): Promise<T> {
  let resp: Response;
  try {
    resp = await fetch(`/api${caminho}`, {
      method: opcoes.method ?? (opcoes.corpo ? "POST" : "GET"),
      headers: { "content-type": "application/json", ...opcoes.headers },
      body: opcoes.corpo ? JSON.stringify(opcoes.corpo) : undefined,
      signal: opcoes.signal,
    });
  } catch (e) {
    if ((e as Error).name === "AbortError") throw e;
    throw new ErroApi(0, "Sem conexão com o servidor. Verifique sua internet e tente novamente.");
  }
  const json = await resp.json().catch(() => null);
  if (!resp.ok) throw new ErroApi(resp.status, mensagemDeErro(json));
  return json as T;
}
