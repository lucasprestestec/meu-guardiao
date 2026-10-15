"use client";

import { Opcoes } from "@/components/campos";
import type { PerguntaDps } from "@/lib/api";

/** Respostas: sim/não = boolean, única = texto, múltipla = lista, número = number. */
export type Respostas = Record<string, boolean | string | string[] | number | undefined>;

export function visiveis(perguntas: PerguntaDps[], r: Respostas): PerguntaDps[] {
  return perguntas.filter((p) => !p.depende || r[p.depende.id] === p.depende.valor);
}

/** Mesmas regras da API (api/dps.py), para avisar antes de enviar. */
export function errosDps(perguntas: PerguntaDps[], r: Respostas): Record<string, string> {
  const e: Record<string, string> = {};
  for (const p of visiveis(perguntas, r)) {
    const v = r[p.id];
    if (v === undefined || (Array.isArray(v) && v.length === 0) || v === "") e[p.id] = "Responda esta pergunta.";
    else if (p.tipo === "numero" && (typeof v !== "number" || v < 0 || v > 1000)) e[p.id] = "Informe um número entre 0 e 1000.";
  }
  return e;
}

/** Só as respostas das perguntas que apareceram (o que não foi mostrado não é enviado). */
export function respostasParaApi(perguntas: PerguntaDps[], r: Respostas) {
  const out: Record<string, boolean | string | string[] | number> = {};
  for (const p of visiveis(perguntas, r)) {
    const v = r[p.id];
    if (v !== undefined) out[p.id] = v;
  }
  return out;
}

export function textoResposta(p: PerguntaDps, v: Respostas[string]): string {
  if (v === undefined) return "—";
  if (typeof v === "boolean") return v ? "Sim" : "Não";
  if (Array.isArray(v)) return v.join("; ");
  if (typeof v === "number") return `${v} ${p.unidade ?? ""}`.trim();
  return v;
}

type Props = {
  perguntas: PerguntaDps[];
  r: Respostas;
  onChange: (r: Respostas) => void;
  erros: Record<string, string>;
  mostrar: boolean;
};

/** As perguntas aparecem com a redação EXATA da seguradora: não resumir nem reescrever. */
export function FormDps({ perguntas, r, onChange, erros, mostrar }: Props) {
  const set = (id: string, v: Respostas[string]) => onChange({ ...r, [id]: v });
  return (
    <ol className="space-y-5">
      {visiveis(perguntas, r).map((p) => {
        const v = r[p.id];
        return (
          <li key={p.id} className="card p-5">
            <fieldset>
              <legend className="font-bold text-ink text-[16px] leading-snug">{p.texto}</legend>
              <div className="mt-3">
                {p.tipo === "sim_nao" && (
                  <Opcoes<boolean> compacto valor={typeof v === "boolean" ? v : undefined} onChange={(x) => set(p.id, x)}
                    opcoes={[{ valor: true, texto: "Sim" }, { valor: false, texto: "Não" }]} />
                )}
                {p.tipo === "unica" && (
                  <div className="space-y-2">
                    {p.opcoes.map((o) => (
                      <label key={o} className={`flex gap-3 items-start rounded-xl border-2 px-4 py-3 cursor-pointer ${v === o ? "border-teal bg-teal-tint" : "border-transparent bg-blue-tint"}`}>
                        <input type="radio" name={p.id} className="w-5 h-5 mt-0.5 accent-[var(--action)] shrink-0" checked={v === o} onChange={() => set(p.id, o)} />
                        <span className="text-ink">{o}</span>
                      </label>
                    ))}
                  </div>
                )}
                {p.tipo === "multipla" && (
                  <div className="space-y-2">
                    {p.opcoes.map((o) => {
                      const sel = Array.isArray(v) ? v : [];
                      const marcado = sel.includes(o);
                      const alternar = () => {
                        if (marcado) set(p.id, sel.filter((x) => x !== o));
                        else if (o === p.exclusiva) set(p.id, [o]); // "Nenhum desses" desmarca o resto
                        else set(p.id, [...sel.filter((x) => x !== p.exclusiva), o]);
                      };
                      return (
                        <label key={o} className={`flex gap-3 items-start rounded-xl border-2 px-4 py-3 cursor-pointer ${marcado ? "border-teal bg-teal-tint" : "border-transparent bg-blue-tint"}`}>
                          <input type="checkbox" className="w-5 h-5 mt-0.5 accent-[var(--action)] shrink-0" checked={marcado} onChange={alternar} />
                          <span className="text-ink">{o}</span>
                        </label>
                      );
                    })}
                  </div>
                )}
                {p.tipo === "numero" && (
                  <div className="flex items-center gap-3">
                    <input inputMode="numeric" className="field max-w-[140px]" aria-label={p.texto}
                      value={typeof v === "number" ? String(v) : ""}
                      onChange={(ev) => {
                        const d = ev.target.value.replace(/\D/g, "").slice(0, 4);
                        set(p.id, d === "" ? undefined : Number(d));
                      }} />
                    {p.unidade && <span className="text-muted">{p.unidade}</span>}
                  </div>
                )}
              </div>
              {mostrar && erros[p.id] && <p className="text-[13px] text-danger font-semibold mt-2">{erros[p.id]}</p>}
            </fieldset>
          </li>
        );
      })}
    </ol>
  );
}
