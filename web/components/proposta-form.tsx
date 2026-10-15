"use client";

import { Plus, Trash2 } from "lucide-react";
import { Dinheiro, Opcoes, Selecao, Texto } from "@/components/campos";
import type { CamposProposta } from "@/lib/api";
import { dataParaIso, mascaraData, soDigitos } from "@/lib/format";

/** Campos da proposta além dos dados pessoais (rodada 3). Tudo como o cliente digita; a conversão
 *  para o formato da API fica em `montarProposta`. */
export type Benef = { nome: string; nasc: string; parentesco: string; pct: string };

export type Extra = {
  nomeSocial: string;
  renda: number;
  peso: string;
  altura: string;
  cep: string;
  logradouro: string;
  numero: string;
  semNumero: boolean;
  complemento: string;
  bairro: string;
  pep?: boolean;
  aposentado: string;
  nacionalidade: string;
  paisNasc: string;
  paisRes: string;
  paisFiscal: string;
  usPerson?: boolean;
  origem: string;
  legais: boolean;
  beneficiarios: Benef[];
};

export const BENEF_VAZIO: Benef = { nome: "", nasc: "", parentesco: "", pct: "" };
export const EXTRA_VAZIO: Extra = {
  nomeSocial: "", renda: 0, peso: "", altura: "", cep: "", logradouro: "", numero: "", semNumero: false,
  complemento: "", bairro: "", aposentado: "", nacionalidade: "", paisNasc: "", paisRes: "",
  paisFiscal: "", origem: "", legais: false, beneficiarios: [{ ...BENEF_VAZIO, pct: "100" }],
};

const numero = (s: string) => Number(s.replace(",", ".").replace(/[^\d.]/g, ""));
export const mascaraCep = (v: string) => {
  const d = soDigitos(v).slice(0, 8);
  return d.length > 5 ? `${d.slice(0, 5)}-${d.slice(5)}` : d;
};

export function somaPct(bs: Benef[]): number {
  return Math.round(bs.reduce((t, b) => t + (numero(b.pct) || 0), 0) * 100) / 100;
}

/** Faixa em texto, só para a ficha do backoffice (a renda exata vai em renda_mensal). */
export function faixaDeRenda(r: number): string {
  if (r <= 3000) return "Até R$ 3.000";
  if (r <= 6000) return "R$ 3.000 a R$ 6.000";
  if (r <= 10000) return "R$ 6.000 a R$ 10.000";
  if (r <= 20000) return "R$ 10.000 a R$ 20.000";
  return "Acima de R$ 20.000";
}

type Regras = { campos: CamposProposta | null; sexo: "M" | "F" | undefined; fumante: boolean | undefined };

/** Erros por campo (mesmas regras da API, para avisar antes de enviar). */
export function errosExtra(x: Extra, d: { profissao: string; civil: string; cidade: string; uf: string }, r: Regras) {
  const e: Record<string, string> = {};
  const ex = new Set(r.campos?.exigidos ?? []);
  const falta = "Preencha este campo.";
  if (ex.has("profissao") && !d.profissao.trim()) e.profissao = falta;
  if (ex.has("estado_civil") && !d.civil) e.civil = falta;
  if (ex.has("cidade") && !d.cidade.trim()) e.cidade = falta;
  if (ex.has("uf") && !d.uf) e.uf = falta;
  if (ex.has("renda_mensal") && x.renda <= 0) e.renda = falta;
  const peso = numero(x.peso);
  if (ex.has("peso_kg") && !(peso >= 20 && peso <= 400)) e.peso = "Peso entre 20 e 400 kg.";
  const alt = Number(soDigitos(x.altura));
  if (ex.has("altura_cm") && !(alt >= 100 && alt <= 250)) e.altura = "Altura em cm, entre 100 e 250.";
  if (ex.has("cep") && soDigitos(x.cep).length !== 8) e.cep = "CEP com 8 dígitos.";
  if (ex.has("logradouro") && !x.logradouro.trim()) e.logradouro = falta;
  if (ex.has("numero_endereco") && !x.semNumero && !x.numero.trim()) e.numero = "Informe o número ou marque sem número.";
  if (ex.has("bairro") && !x.bairro.trim()) e.bairro = falta;
  if (ex.has("pep") && x.pep === undefined) e.pep = "Responda sim ou não.";
  if (ex.has("aposentado") && !x.aposentado) e.aposentado = falta;
  for (const [k, v] of [["nacionalidade", x.nacionalidade], ["pais_nascimento", x.paisNasc],
    ["pais_residencia", x.paisRes], ["pais_residencia_fiscal", x.paisFiscal]] as const)
    if (ex.has(k) && !v.trim()) e[k] = falta;
  if (ex.has("us_person") && x.usPerson === undefined) e.us_person = "Responda sim ou não.";
  if (ex.has("origem_recurso") && !x.origem) e.origem = falta;

  const max = r.campos?.max_beneficiarios ?? 10;
  if (!x.legais) {
    if (x.beneficiarios.length === 0) e.beneficiarios = "Indique ao menos um beneficiário.";
    else if (x.beneficiarios.length > max) e.beneficiarios = `No máximo ${max} beneficiários.`;
    x.beneficiarios.forEach((b, i) => {
      if (b.nome.trim().length < 3) e[`b${i}nome`] = falta;
      if (!dataParaIso(b.nasc)) e[`b${i}nasc`] = "Use dd/mm/aaaa.";
      if (!b.parentesco) e[`b${i}parentesco`] = falta;
      if (!(numero(b.pct) > 0 && numero(b.pct) <= 100)) e[`b${i}pct`] = "Entre 0 e 100.";
    });
    if (!e.beneficiarios && somaPct(x.beneficiarios) !== 100)
      e.beneficiarios = `A soma dos percentuais deve ser 100%; está em ${somaPct(x.beneficiarios)}%.`;
  }
  return e;
}

/** Corpo `proposta` da API. Sexo e fumante vêm da comparação (o preço depende deles). */
export function montarProposta(x: Extra, r: Regras, ex: Set<string>) {
  const txt = (s: string) => s.trim() || null;
  return {
    nome_social: txt(x.nomeSocial),
    sexo: r.sexo ?? null,
    renda_mensal: x.renda > 0 ? x.renda : null,
    peso_kg: numero(x.peso) || null,
    altura_cm: Number(soDigitos(x.altura)) || null,
    cep: soDigitos(x.cep) || null,
    logradouro: txt(x.logradouro),
    numero_endereco: x.semNumero ? "S/N" : txt(x.numero),
    complemento: txt(x.complemento),
    bairro: txt(x.bairro),
    pep: ex.has("pep") ? x.pep ?? null : null,
    fumante_24_meses: ex.has("fumante_24_meses") ? r.fumante ?? null : null,
    aposentado: ex.has("aposentado") ? x.aposentado || null : null,
    nacionalidade: ex.has("nacionalidade") ? txt(x.nacionalidade) : null,
    pais_nascimento: ex.has("pais_nascimento") ? txt(x.paisNasc) : null,
    pais_residencia: ex.has("pais_residencia") ? txt(x.paisRes) : null,
    pais_residencia_fiscal: ex.has("pais_residencia_fiscal") ? txt(x.paisFiscal) : null,
    us_person: ex.has("us_person") ? x.usPerson ?? null : null,
    origem_recurso: ex.has("origem_recurso") ? x.origem || null : null,
    beneficiarios_legais: x.legais,
    beneficiarios: x.legais
      ? []
      : x.beneficiarios.map((b) => ({
          nome: b.nome.trim(), data_nascimento: dataParaIso(b.nasc), parentesco: b.parentesco,
          percentual: numero(b.pct),
        })),
  };
}

const SIM_NAO = [{ valor: true, texto: "Sim" }, { valor: false, texto: "Não" }];

type Props = {
  x: Extra;
  set: (parcial: Partial<Extra>) => void;
  campos: CamposProposta | null;
  erros: Record<string, string>;
  mostrar: boolean; // só mostra erros depois da primeira tentativa
  fumante: boolean | undefined;
};

/** Perguntas que dependem da seguradora escolhida (Azos e Icatu). */
export function SecaoSeguradora({ x, set, campos, erros, mostrar, fumante }: Props) {
  const ex = new Set(campos?.exigidos ?? []);
  const e = (k: string) => (mostrar ? erros[k] : undefined);
  if (!ex.has("pep") && !ex.has("nacionalidade")) return null;
  return (
    <section className="card p-6 mt-5 space-y-4">
      <h2 className="text-xl font-extrabold">Perguntas da seguradora</h2>
      <p className="text-[13px] text-muted">A seguradora que você escolheu pede estas informações para emitir a proposta.</p>
      {ex.has("pep") && (
        <>
          <Opcoes<boolean> compacto rotulo="Você é pessoa politicamente exposta?" valor={x.pep} onChange={(v) => set({ pep: v })} opcoes={SIM_NAO} />
          {e("pep") && <p className="text-[13px] text-danger font-semibold">{e("pep")}</p>}
          {fumante !== undefined && (
            <p className="text-[14px] text-body">Fumou produtos com nicotina ou cigarro eletrônico nos últimos 24 meses: <b>{fumante ? "sim" : "não"}</b> (como você informou na comparação).</p>
          )}
        </>
      )}
      {ex.has("nacionalidade") && (
        <>
          <div className="grid sm:grid-cols-2 gap-4">
            <Selecao rotulo="Você é aposentado?" valor={campos?.aposentado.find((a) => a.valor === x.aposentado)?.texto ?? ""}
              onChange={(t) => set({ aposentado: campos?.aposentado.find((a) => a.texto === t)?.valor ?? "" })}
              opcoes={(campos?.aposentado ?? []).map((a) => a.texto)} erro={e("aposentado")} />
            <Selecao rotulo="Origem do recurso" valor={x.origem} onChange={(v) => set({ origem: v })} opcoes={campos?.origens_recurso ?? []} erro={e("origem")} />
            <Texto rotulo="Nacionalidade" valor={x.nacionalidade} onChange={(v) => set({ nacionalidade: v })} erro={e("nacionalidade")} />
            <Texto rotulo="País de nascimento" valor={x.paisNasc} onChange={(v) => set({ paisNasc: v })} erro={e("pais_nascimento")} />
            <Texto rotulo="País de residência atual" valor={x.paisRes} onChange={(v) => set({ paisRes: v })} erro={e("pais_residencia")} />
            <Texto rotulo="País de residência fiscal" valor={x.paisFiscal} onChange={(v) => set({ paisFiscal: v })} erro={e("pais_residencia_fiscal")} />
          </div>
          <Opcoes<boolean> compacto rotulo="Você é US Person (cidadão ou residente fiscal dos EUA)?" valor={x.usPerson} onChange={(v) => set({ usPerson: v })} opcoes={SIM_NAO} />
          {e("us_person") && <p className="text-[13px] text-danger font-semibold">{e("us_person")}</p>}
        </>
      )}
    </section>
  );
}

export function SecaoBeneficiarios({ x, set, campos, erros, mostrar }: Omit<Props, "fumante">) {
  const e = (k: string) => (mostrar ? erros[k] : undefined);
  const max = campos?.max_beneficiarios ?? 10;
  const soma = somaPct(x.beneficiarios);
  const mudar = (i: number, p: Partial<Benef>) =>
    set({ beneficiarios: x.beneficiarios.map((b, j) => (j === i ? { ...b, ...p } : b)) });
  return (
    <section className="card p-6 mt-5 space-y-4">
      <h2 className="text-xl font-extrabold">Beneficiários</h2>
      {campos?.aceita_beneficiarios_legais && (
        <Opcoes<boolean> compacto valor={x.legais} onChange={(v) => set({ legais: v })}
          opcoes={[{ valor: false, texto: "Indicar beneficiários" }, { valor: true, texto: "Deixar para os legais" }]} />
      )}
      {x.legais ? (
        <p className="text-[14px] text-body">Se ninguém for indicado, a indenização segue a legislação (cônjuge, filhos e demais herdeiros).</p>
      ) : (
        <>
          {x.beneficiarios.map((b, i) => (
            <div key={i} className="rounded-2xl bg-blue-tint p-4 space-y-3">
              <div className="flex items-center justify-between">
                <h3 className="font-bold text-ink">Beneficiário {i + 1}</h3>
                {x.beneficiarios.length > 1 && (
                  <button type="button" aria-label={`Remover beneficiário ${i + 1}`} className="text-muted hover:text-danger p-1"
                    onClick={() => set({ beneficiarios: x.beneficiarios.filter((_, j) => j !== i) })}><Trash2 size={18} /></button>
                )}
              </div>
              <div className="grid sm:grid-cols-2 gap-3">
                <Texto rotulo="Nome completo" valor={b.nome} onChange={(v) => mudar(i, { nome: v })} erro={e(`b${i}nome`)} />
                <Texto rotulo="Data de nascimento" valor={b.nasc} onChange={(v) => mudar(i, { nasc: mascaraData(v) })} placeholder="dd/mm/aaaa" inputMode="numeric" erro={e(`b${i}nasc`)} />
                <Selecao rotulo="Grau de parentesco" valor={b.parentesco} onChange={(v) => mudar(i, { parentesco: v })} opcoes={campos?.parentescos ?? []} erro={e(`b${i}parentesco`)} />
                <Texto rotulo="Participação (%)" valor={b.pct} onChange={(v) => mudar(i, { pct: v.replace(/[^\d.,]/g, "").slice(0, 6) })} inputMode="numeric" erro={e(`b${i}pct`)} />
              </div>
            </div>
          ))}
          <div className="flex flex-wrap items-center justify-between gap-3">
            <button type="button" className="btn btn-soft !py-2 !px-4 flex items-center gap-1.5" disabled={x.beneficiarios.length >= max}
              onClick={() => set({ beneficiarios: [...x.beneficiarios, { ...BENEF_VAZIO }] })}><Plus size={16} aria-hidden /> Adicionar beneficiário</button>
            <span className={`text-[14px] font-bold ${soma === 100 ? "text-teal" : "text-body"}`}>Soma: {soma}% de 100%</span>
          </div>
          {campos && !campos.lista_parentesco_completa && (
            <p className="text-[12px] text-muted">Lista de parentesco desta seguradora em conferência: se o seu não aparece, fale com a nossa equipe no recado.</p>
          )}
          {e("beneficiarios") && <p className="text-[13px] text-danger font-semibold">{e("beneficiarios")}</p>}
        </>
      )}
    </section>
  );
}

export { Dinheiro };
