"use client";

import { useId, type ReactNode } from "react";

const nf = new Intl.NumberFormat("pt-BR", { maximumFractionDigits: 0 });

/** Campo em reais: mostra 1.500.000, guarda o número. Vazio = 0. */
export function Dinheiro({
  rotulo,
  ajuda,
  valor,
  onChange,
  sufixo,
}: {
  rotulo: string;
  ajuda?: string;
  valor: number;
  onChange: (v: number) => void;
  sufixo?: string;
}) {
  const id = useId();
  return (
    <div>
      <label htmlFor={id} className="block font-bold text-ink mb-1.5">
        {rotulo}
      </label>
      <div className="relative">
        <span className="absolute left-4 top-1/2 -translate-y-1/2 text-muted font-semibold" aria-hidden>
          R$
        </span>
        <input
          id={id}
          inputMode="numeric"
          className="field !pl-12"
          value={valor ? nf.format(valor) : ""}
          placeholder="0"
          onChange={(e) => onChange(Number(e.target.value.replace(/\D/g, "").slice(0, 12)) || 0)}
        />
        {sufixo && <span className="absolute right-4 top-1/2 -translate-y-1/2 text-muted text-sm">{sufixo}</span>}
      </div>
      {ajuda && <p className="text-[13px] text-muted mt-1.5">{ajuda}</p>}
    </div>
  );
}

export function Texto({
  rotulo,
  valor,
  onChange,
  placeholder,
  erro,
  inputMode,
  autoComplete,
  ajuda,
  maxLength,
}: {
  rotulo: string;
  valor: string;
  onChange: (v: string) => void;
  placeholder?: string;
  erro?: string;
  inputMode?: "numeric" | "email" | "tel" | "text";
  autoComplete?: string;
  ajuda?: string;
  maxLength?: number;
}) {
  const id = useId();
  return (
    <div>
      <label htmlFor={id} className="block font-bold text-ink mb-1.5 text-[15px]">
        {rotulo}
      </label>
      <input
        id={id}
        className="field"
        value={valor}
        placeholder={placeholder}
        inputMode={inputMode}
        autoComplete={autoComplete}
        maxLength={maxLength}
        aria-invalid={erro ? true : undefined}
        aria-describedby={erro ? `${id}-e` : undefined}
        onChange={(e) => onChange(e.target.value)}
      />
      {ajuda && !erro && <p className="text-[13px] text-muted mt-1.5">{ajuda}</p>}
      {erro && (
        <p id={`${id}-e`} className="text-[13px] text-danger font-semibold mt-1.5">
          {erro}
        </p>
      )}
    </div>
  );
}

export function Selecao({
  rotulo,
  valor,
  onChange,
  opcoes,
  placeholder = "Selecione",
  erro,
}: {
  rotulo: string;
  valor: string;
  onChange: (v: string) => void;
  opcoes: string[];
  placeholder?: string;
  erro?: string;
}) {
  const id = useId();
  return (
    <div>
      <label htmlFor={id} className="block font-bold text-ink mb-1.5 text-[15px]">
        {rotulo}
      </label>
      <select
        id={id}
        className="field"
        value={valor}
        aria-invalid={erro ? true : undefined}
        onChange={(e) => onChange(e.target.value)}
      >
        <option value="">{placeholder}</option>
        {opcoes.map((o) => (
          <option key={o}>{o}</option>
        ))}
      </select>
      {erro && <p className="text-[13px] text-danger font-semibold mt-1.5">{erro}</p>}
    </div>
  );
}

/** Grupo de escolha única em botões grandes (Sim/Não, 1/2/3/4+). */
export function Opcoes<T extends string | number | boolean>({
  rotulo,
  valor,
  onChange,
  opcoes,
  compacto = false,
}: {
  rotulo?: string;
  valor: T | undefined;
  onChange: (v: T) => void;
  opcoes: { valor: T; texto: string; ajuda?: string; icone?: ReactNode }[];
  compacto?: boolean;
}) {
  return (
    <fieldset>
      {rotulo && <legend className="font-bold text-ink mb-2 text-[15px]">{rotulo}</legend>}
      <div
        className={`grid gap-3 ${compacto ? "" : opcoes.length === 2 ? "sm:grid-cols-2" : "sm:grid-cols-3"}`}
        style={compacto ? { gridTemplateColumns: `repeat(${opcoes.length}, minmax(0, 1fr))` } : undefined}
      >
        {opcoes.map((o) => {
          const ativo = o.valor === valor;
          return (
            <button
              type="button"
              key={String(o.valor)}
              aria-pressed={ativo}
              onClick={() => onChange(o.valor)}
              className={`text-left rounded-2xl border-2 transition-colors ${
                compacto ? "px-3 py-3 text-center font-bold" : "p-5"
              } ${
                ativo
                  ? "border-teal bg-teal-tint text-ink"
                  : "border-transparent bg-blue-tint text-ink hover:border-[#c5d8f3]"
              }`}
            >
              <span className="flex items-center gap-3">
                {o.icone}
                <span>
                  <span className={`block ${compacto ? "" : "font-extrabold text-xl"}`}>{o.texto}</span>
                  {o.ajuda && <span className="block text-[14px] text-body mt-0.5">{o.ajuda}</span>}
                </span>
              </span>
            </button>
          );
        })}
      </div>
    </fieldset>
  );
}
