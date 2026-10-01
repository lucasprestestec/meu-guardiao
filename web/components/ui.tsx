import type { ReactNode } from "react";
import {
  AlertTriangle,
  Accessibility,
  BarChart3,
  Check,
  HeartPulse,
  Info,
  ShieldCheck,
  type LucideIcon,
} from "lucide-react";
import { capitalCurto, nomeSeguradora } from "@/lib/format";
import { humanizar } from "@/lib/coberturas";
import type { ItemOpcao } from "@/lib/api";
import { MARCA } from "@/lib/marca";

// Componentes sem estado: servem a páginas de servidor e de cliente.

export function Logo({ small = false }: { small?: boolean }) {
  return (
    <span
      className={`font-extrabold tracking-tight text-ink leading-none whitespace-nowrap ${small ? "text-lg" : "text-[22px] sm:text-[28px]"}`}
    >
      {MARCA.split(" ")[0]}
      <span className="font-bold text-teal"> {MARCA.split(" ").slice(1).join(" ")}</span>
    </span>
  );
}

/** As quatro necessidades do Motor, com o mesmo ícone/cor em toda a jornada. */
export const NEC: Record<
  string,
  { rotulo: string; curto: string; descricao: string; Icon: LucideIcon; cor: string; tint: string; texto: string }
> = {
  NEC_MORTE: {
    rotulo: "Morte",
    curto: "Morte",
    descricao: "Proteção para sua família em caso de falecimento.",
    Icon: ShieldCheck,
    cor: "#1560e8",
    tint: "var(--blue-tint)",
    texto: "text-action",
  },
  NEC_INVALIDEZ: {
    rotulo: "Invalidez",
    curto: "Invalidez",
    descricao: "Garante estabilidade em caso de invalidez causada por acidente.",
    Icon: Accessibility,
    cor: "#0c8f88",
    tint: "var(--teal-tint)",
    texto: "text-teal",
  },
  NEC_DOENCA_GRAVE: {
    rotulo: "Doenças graves",
    curto: "Doenças graves",
    descricao: "Ajuda com os custos de tratamento e manutenção da sua rotina.",
    Icon: HeartPulse,
    cor: "#b7791f",
    tint: "var(--amber-tint)",
    texto: "text-amber",
  },
  NEC_RENDA: {
    rotulo: "Proteção de renda",
    curto: "Proteção de renda",
    descricao: "Garante uma renda diária enquanto você estiver internado.",
    Icon: BarChart3,
    cor: "#5b48d6",
    tint: "var(--violet-tint)",
    texto: "text-violet",
  },
};
export const ORDEM_NEC = ["NEC_MORTE", "NEC_INVALIDEZ", "NEC_DOENCA_GRAVE", "NEC_RENDA"];

export function IconeNec({ codigo, size = 44 }: { codigo: string; size?: number }) {
  const n = NEC[codigo];
  const { Icon } = n;
  return (
    <span
      className="grid place-items-center rounded-2xl shrink-0"
      style={{ width: size, height: size, background: n.tint, color: n.cor }}
    >
      <Icon size={size * 0.5} strokeWidth={2} aria-hidden />
    </span>
  );
}

const ETAPAS = ["Diagnóstico", "Personalização", "Comparação", "Contratação"];

/** Trilha de 4 etapas do topo das telas de compra. `atual` vai de 1 a 4. */
export function Etapas({ atual }: { atual: 1 | 2 | 3 | 4 }) {
  return (
    <>
    <p className="sm:hidden text-[14px] font-semibold text-ink">
      Etapa {atual} de 4 · <span className="text-action">{ETAPAS[atual - 1]}</span>
    </p>
    <ol className="hidden sm:flex items-center gap-2 sm:gap-3 text-[14px] font-semibold" aria-label="Etapas">
      {ETAPAS.map((nome, i) => {
        const n = i + 1;
        const feito = n < atual;
        const ativo = n === atual;
        return (
          <li key={nome} className="flex items-center gap-2 sm:gap-3 shrink-0" aria-current={ativo ? "step" : undefined}>
            <span
              className={`grid place-items-center w-8 h-8 rounded-full text-sm ${
                ativo ? "bg-action text-white" : feito ? "bg-blue-tint text-action" : "bg-blue-tint text-muted"
              }`}
            >
              {feito ? <Check size={16} strokeWidth={3} aria-hidden /> : n}
            </span>
            <span className={ativo ? "text-action" : feito ? "text-ink" : "text-muted"}>{nome}</span>
            {n < 4 && <span className={`w-6 sm:w-10 h-px ${feito ? "bg-action" : "bg-line"}`} aria-hidden />}
          </li>
        );
      })}
    </ol>
    </>
  );
}

export function Barra({ valor, cor = "var(--teal)", alto = 8 }: { valor: number; cor?: string; alto?: number }) {
  const p = Math.max(0, Math.min(1, valor)) * 100;
  return (
    <div
      className="w-full rounded-full bg-[#e3ebf6] overflow-hidden"
      style={{ height: alto }}
      role="progressbar"
      aria-valuenow={Math.round(p)}
      aria-valuemin={0}
      aria-valuemax={100}
    >
      <div className="h-full rounded-full" style={{ width: `${p}%`, background: cor }} />
    </div>
  );
}

/** Anel de progresso (Protection Score, aderência). */
export function Anel({
  valor,
  tamanho = 120,
  espessura = 12,
  rotulo,
  sub,
}: {
  valor: number; // 0..1
  tamanho?: number;
  espessura?: number;
  rotulo: string;
  sub?: string;
}) {
  const r = (tamanho - espessura) / 2;
  const c = 2 * Math.PI * r;
  return (
    <div className="relative shrink-0" style={{ width: tamanho, height: tamanho }}>
      <svg width={tamanho} height={tamanho} viewBox={`0 0 ${tamanho} ${tamanho}`} className="-rotate-90" aria-hidden>
        <circle cx={tamanho / 2} cy={tamanho / 2} r={r} fill="none" stroke="#dbe9f3" strokeWidth={espessura} />
        <circle
          cx={tamanho / 2}
          cy={tamanho / 2}
          r={r}
          fill="none"
          stroke="var(--teal)"
          strokeWidth={espessura}
          strokeLinecap="round"
          strokeDasharray={c}
          strokeDashoffset={c * (1 - Math.max(0, Math.min(1, valor)))}
        />
      </svg>
      <div className="absolute inset-0 grid place-items-center text-center">
        <div>
          <div className="font-extrabold text-ink leading-none" style={{ fontSize: tamanho * 0.27 }}>
            {rotulo}
          </div>
          {sub && <div className="text-muted font-semibold" style={{ fontSize: tamanho * 0.11 }}>{sub}</div>}
        </div>
      </div>
    </div>
  );
}

export function Selo({
  children,
  tom = "teal",
}: {
  children: ReactNode;
  tom?: "teal" | "blue" | "amber" | "violet" | "danger" | "cinza";
}) {
  const t = {
    teal: "bg-teal-tint text-teal",
    blue: "bg-blue-tint text-action",
    amber: "bg-amber-tint text-amber",
    violet: "bg-violet-tint text-violet",
    danger: "bg-danger-tint text-danger",
    cinza: "bg-[#eef2f8] text-muted",
  }[tom];
  return (
    <span className={`inline-flex items-center gap-1.5 rounded-full px-3 py-1 text-[12px] font-bold tracking-wide uppercase ${t}`}>
      {children}
    </span>
  );
}

export function Aviso({ children, tom = "info" }: { children: ReactNode; tom?: "info" | "alerta" | "erro" }) {
  const t = {
    info: "bg-blue-tint text-ink",
    alerta: "bg-amber-tint text-[#7a4f0e]",
    erro: "bg-danger-tint text-danger",
  }[tom];
  return (
    <div className={`rounded-2xl px-4 py-3 flex gap-3 text-[14px] ${t}`} role={tom === "erro" ? "alert" : undefined}>
      {tom === "info" ? <Info size={18} className="shrink-0 mt-0.5 text-action" aria-hidden /> : <AlertTriangle size={18} className="shrink-0 mt-0.5" aria-hidden />}
      <div>{children}</div>
    </div>
  );
}

export function Carregando({ texto = "Carregando…" }: { texto?: string }) {
  return (
    <div className="grid place-items-center py-24 text-muted font-semibold" role="status">
      <div className="w-9 h-9 rounded-full border-4 border-line border-t-action animate-spin mb-4" aria-hidden />
      {texto}
    </div>
  );
}

/** Lista de coberturas de uma opção, no formato curto dos mockups. */
export function ListaCoberturas({ itens, notas = 0 }: { itens: ItemOpcao[]; notas?: number }) {
  // `notas`: quantas observações mostrar sob cada linha. Quem lê o card lê a linha,
  // não a barra de aderência: o tipo real da cobertura tem que estar na linha.
  const porNec = new Map(itens.map((i) => [i.necessidade, i]));
  return (
    <ul className="divide-y divide-line">
      {ORDEM_NEC.filter((c) => porNec.has(c)).map((c) => {
        const i = porNec.get(c)!;
        const n = NEC[c];
        const indisponivel = !i.cobertura || i.capital_contratado <= 0;
        const obs = notas > 0 ? i.observacoes.slice(0, notas) : [];
        return (
          <li key={c} className="py-2.5">
            <div className="flex items-center gap-3">
              <n.Icon size={20} className={n.texto} aria-hidden />
              <span className="text-body flex-1">{n.rotulo}</span>
              <span className={`font-bold ${indisponivel ? "text-muted font-medium" : "text-ink"}`}>
                {indisponivel ? "indisponível" : capitalCurto(i.capital_contratado, c === "NEC_RENDA")}
              </span>
            </div>
            {obs.length > 0 && (
              <ul className="ml-8 mt-0.5 text-[12.5px] leading-snug text-muted list-disc pl-4">
                {obs.map((t) => <li key={t}>{humanizar(t)}</li>)}
              </ul>
            )}
          </li>
        );
      })}
    </ul>
  );
}

export function NomeSeguradora({ nome, grande = false }: { nome: string; grande?: boolean }) {
  return (
    <span className={`font-extrabold text-ink tracking-tight ${grande ? "text-3xl" : "text-xl"}`}>
      {nomeSeguradora(nome)}
    </span>
  );
}
