"use client";

import { useCallback, useEffect, useState } from "react";
import { Clock, X } from "lucide-react";
import { Aviso, Selo } from "@/components/ui";
import { api } from "@/lib/api";
import { brl, capitalCurto, dataHora } from "@/lib/format";

type Linha = {
  id: string; nome: string; celular: string; email: string; motivos: string[]; mensagem: string | null;
  status: "NOVO" | "EM_CONTATO" | "CONCLUIDO"; criado_em: string; tem_diagnostico: boolean;
};
type Fila = { pedidos: Linha[]; funil_30_dias: Record<string, number> };
type Necessidade = { codigo: string; rotulo: string; unidade: string; valor_necessario: number; valor_existente: number; gap: number; justificativa: string };
type FichaPedido = {
  id: string; status: Linha["status"]; criado_em: string;
  contato: { nome: string; email: string; celular: string };
  motivos: string[]; mensagem: string | null;
  diagnostico: { entradas: Record<string, unknown>; calculado_em: string; mapa: { necessidades: Necessidade[]; alertas: string[] } } | null;
  cotacao: { capitais_escolhidos: Record<string, number> | null; recado: string | null; idade: number; sexo: string; fumante: boolean } | null;
  consentimentos: { tipo: string; aceito: boolean; texto_versao: string; aceito_em: string; ip: string | null; revogado_em: string | null }[];
};

const STATUS: Record<Linha["status"], { texto: string; tom: "blue" | "amber" | "teal" }> = {
  NOVO: { texto: "Novo", tom: "blue" },
  EM_CONTATO: { texto: "Em contato", tom: "amber" },
  CONCLUIDO: { texto: "Concluído", tom: "teal" },
};

const ROTULO: Record<string, string> = {
  idade: "Idade", renda_mensal_liquida: "Renda mensal líquida", custo_familiar_mensal: "Custo familiar mensal",
  situacao_profissional: "Situação profissional", fase_de_vida: "Fase de vida", dependentes: "Dependentes",
  horizonte_protecao_anos: "Horizonte de proteção (anos)", dividas: "Dívidas", projetos: "Projetos",
  patrimonio_liquido: "Patrimônio líquido", patrimonio_inventariavel: "Patrimônio inventariável",
  meses_de_reserva: "Meses de reserva", seguro_atual: "Seguro atual",
  imobiliaria: "Imobiliária", empresarial: "Empresarial", veiculos: "Veículos", outras: "Outras",
  imobiliaria_tem_prestamista: "Imobiliária tem prestamista", educacao_filhos: "Educação dos filhos",
  quitacao_imovel: "Quitação do imóvel", outros: "Outros", morte: "Morte", invalidez: "Invalidez",
  doenca_grave: "Doenças graves", dit_diaria: "Diária", financeiramente_dependente: "Financeiramente dependente",
};

function valorLegivel(v: unknown): string {
  if (typeof v === "number") return Number.isInteger(v) && v < 200 ? String(v) : brl(v);
  if (typeof v === "boolean") return v ? "Sim" : "Não";
  if (v === null || v === undefined || v === "") return "—";
  return String(v);
}

/** Entradas do diagnóstico, uma linha por informação; objetos aninhados viram sub-listas. */
function Entradas({ dados }: { dados: Record<string, unknown> }) {
  const linhas = Object.entries(dados).filter(([k]) => k !== "cliente_id");
  return (
    <dl className="text-[14px] divide-y divide-line">
      {linhas.map(([k, v]) => {
        if (Array.isArray(v))
          return (
            <div key={k} className="py-1.5">
              <dt className="text-muted">{ROTULO[k] ?? k}</dt>
              <dd className="font-semibold text-ink">
                {v.length === 0 ? "Nenhum" : v.map((d, i) => <div key={i}>{Object.entries(d as Record<string, unknown>).map(([a, b]) => `${ROTULO[a] ?? a}: ${valorLegivel(b)}`).join(" · ")}</div>)}
              </dd>
            </div>
          );
        if (v && typeof v === "object")
          return (
            <div key={k} className="py-1.5">
              <dt className="text-muted">{ROTULO[k] ?? k}</dt>
              <dd className="pl-3"><Entradas dados={v as Record<string, unknown>} /></dd>
            </div>
          );
        return (
          <div key={k} className="flex justify-between gap-4 py-1.5">
            <dt className="text-muted">{ROTULO[k] ?? k}</dt>
            <dd className="font-semibold text-ink text-right">{valorLegivel(v)}</dd>
          </div>
        );
      })}
    </dl>
  );
}

export function PedidosEspecialista({ H }: { H: Record<string, string> }) {
  const [fila, setFila] = useState<Fila | null>(null);
  const [erro, setErro] = useState<string | null>(null);
  const [aberto, setAberto] = useState<string | null>(null);

  const carregar = useCallback(
    () => api<Fila>("/v1/backoffice/pedidos-especialista", { headers: H }).then((r) => { setFila(r); setErro(null); }).catch((e) => setErro((e as Error).message)),
    [H],
  );
  useEffect(() => {
    carregar();
    const t = setInterval(carregar, 15000);
    return () => clearInterval(t);
  }, [carregar]);

  const f = fila?.funil_30_dias;
  const abandono = f && f.contato_visto > 0 ? Math.round((1 - f.contato_enviado / f.contato_visto) * 100) : null;

  return (
    <>
      <h1 className="text-3xl font-extrabold text-ink tracking-tight mb-5">Pedidos de especialista</h1>
      {erro && <div className="mb-4"><Aviso tom="erro">{erro}</Aviso></div>}

      {f && (
        <p className="text-[14px] text-body mb-4">
          <b className="text-ink">Tela de contato, últimos 30 dias:</b> {f.contato_visto} viram, {f.contato_enviado} continuaram
          {abandono !== null && <> · abandono de <b className="text-ink">{abandono}%</b></>}.
        </p>
      )}

      <div className="card overflow-x-auto">
        <table className="w-full text-[15px] min-w-[820px]">
          <thead>
            <tr className="text-left text-[13px] text-muted border-b border-line">
              {["Cliente", "Motivos", "Status", "Recebido", "Diagnóstico"].map((h) => <th key={h} className="px-4 py-3 font-semibold">{h}</th>)}
            </tr>
          </thead>
          <tbody>
            {fila && fila.pedidos.length === 0 && (
              <tr><td colSpan={5} className="px-4 py-12 text-center text-muted">Nenhum pedido ainda.</td></tr>
            )}
            {fila?.pedidos.map((p) => (
              <tr key={p.id} tabIndex={0} onClick={() => setAberto(p.id)} onKeyDown={(e) => e.key === "Enter" && setAberto(p.id)}
                className={`border-b border-line last:border-0 cursor-pointer hover:bg-canvas focus:bg-canvas focus:outline-none ${aberto === p.id ? "bg-blue-tint" : ""}`}>
                <td className="px-4 py-3.5"><span className="font-bold text-ink">{p.nome}</span><span className="block text-[13px] text-muted">{p.email}</span></td>
                <td className="px-4 py-3.5 text-body max-w-[320px]">{p.motivos.join("; ") || "—"}</td>
                <td className="px-4 py-3.5"><Selo tom={STATUS[p.status].tom}>{STATUS[p.status].texto}</Selo></td>
                <td className="px-4 py-3.5 text-body">{dataHora(p.criado_em)}</td>
                <td className="px-4 py-3.5 text-body">{p.tem_diagnostico ? "Sim" : "Não"}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <p className="text-[13px] text-muted mt-3">Quem chegou pelo botão &ldquo;Falar com um especialista&rdquo;. Não há agenda: o time entra em contato para combinar.</p>

      {aberto && <Gaveta id={aberto} H={H} onFechar={() => setAberto(null)} onMudou={carregar} />}
    </>
  );
}

function Gaveta({ id, H, onFechar, onMudou }: { id: string; H: Record<string, string>; onFechar: () => void; onMudou: () => void }) {
  const [f, setF] = useState<FichaPedido | null>(null);
  const [erro, setErro] = useState<string | null>(null);

  const buscar = useCallback(
    () => api<FichaPedido>(`/v1/backoffice/pedidos-especialista/${id}`, { headers: H }).then((r) => { setF(r); setErro(null); }).catch((e) => setErro((e as Error).message)),
    [id, H],
  );
  useEffect(() => { setF(null); buscar(); }, [buscar]);

  async function status(s: Linha["status"]) {
    try {
      await api(`/v1/backoffice/pedidos-especialista/${id}/status`, { headers: H, corpo: { status: s } });
      await buscar();
      onMudou();
    } catch (e) {
      setErro((e as Error).message);
    }
  }

  const digitos = f?.contato.celular ?? "";
  const tel = digitos.replace(/^(\d{2})(\d{4,5})(\d{4})$/, "($1) $2-$3");

  return (
    <aside className="fixed inset-y-0 right-0 w-full sm:w-[520px] bg-white border-l border-line shadow-[-12px_0_40px_rgba(10,31,92,0.10)] overflow-y-auto z-20" aria-label="Detalhes do pedido">
      <div className="p-6 space-y-6">
        <div className="flex items-start justify-between gap-3">
          <div>
            <h2 className="text-2xl font-extrabold text-ink leading-tight">{f?.contato.nome ?? "Carregando…"}</h2>
            {f && <div className="mt-1.5 flex items-center gap-2"><Selo tom={STATUS[f.status].tom}>{STATUS[f.status].texto}</Selo><span className="text-[13px] text-muted flex items-center gap-1"><Clock size={13} aria-hidden /> {dataHora(f.criado_em)}</span></div>}
          </div>
          <button onClick={onFechar} aria-label="Fechar" className="p-1 text-muted hover:text-ink"><X size={22} /></button>
        </div>
        {erro && <Aviso tom="erro">{erro}</Aviso>}

        {f && (
          <>
            <div className="flex flex-wrap gap-2">
              {f.status === "NOVO" && <button className="btn btn-primary !py-2.5" onClick={() => status("EM_CONTATO")}>Marcar em contato</button>}
              {f.status !== "CONCLUIDO" && <button className="btn btn-secondary !py-2.5" onClick={() => status("CONCLUIDO")}>Concluir</button>}
              <a className="btn btn-secondary !py-2.5" target="_blank" rel="noreferrer" href={`https://wa.me/55${digitos}`}>Abrir WhatsApp</a>
            </div>

            <section>
              <h3 className="font-extrabold text-ink mb-2">Contato</h3>
              <dl className="text-[15px] divide-y divide-line">
                <div className="flex justify-between py-2"><dt className="text-muted">Telefone</dt><dd className="font-semibold">{tel}</dd></div>
                <div className="flex justify-between py-2"><dt className="text-muted">E-mail</dt><dd className="font-semibold break-all">{f.contato.email}</dd></div>
              </dl>
            </section>

            <section>
              <h3 className="font-extrabold text-ink mb-2">O que o cliente pediu</h3>
              <ul className="list-disc pl-5 text-body">{f.motivos.map((m) => <li key={m}>{m}</li>)}{f.motivos.length === 0 && <li>Nenhum motivo marcado</li>}</ul>
              {f.mensagem && <p className="mt-3 rounded-2xl bg-canvas px-4 py-3 text-ink whitespace-pre-wrap">{f.mensagem}</p>}
              {f.cotacao?.recado && (
                <p className="mt-3 rounded-2xl bg-amber-tint px-4 py-3 text-ink whitespace-pre-wrap"><b>Recado na personalização:</b> {f.cotacao.recado}</p>
              )}
            </section>

            {f.diagnostico ? (
              <>
                <section>
                  <h3 className="font-extrabold text-ink mb-2">Mapa de Proteção</h3>
                  <ul className="space-y-3">
                    {f.diagnostico.mapa.necessidades.map((n) => {
                      const diaria = n.unidade === "DIARIA";
                      return (
                        <li key={n.codigo} className="rounded-2xl border border-line p-4">
                          <div className="flex justify-between gap-3"><b className="text-ink">{n.rotulo}</b><b className="text-ink">{capitalCurto(n.valor_necessario, diaria)}</b></div>
                          <div className="text-[13px] text-muted mt-0.5">Já tem {n.valor_existente > 0 ? capitalCurto(n.valor_existente, diaria) : "nada"} · falta {n.gap > 0 ? capitalCurto(n.gap, diaria) : "nada"}</div>
                          <details className="text-[13px] mt-1"><summary className="cursor-pointer text-action font-semibold">Como o valor foi calculado</summary><p className="mt-1 text-body">{n.justificativa}</p></details>
                        </li>
                      );
                    })}
                  </ul>
                  {f.cotacao?.capitais_escolhidos && (
                    <p className="text-[13px] text-body mt-3"><b>Valores escolhidos pelo cliente:</b>{" "}
                      {Object.entries(f.cotacao.capitais_escolhidos).map(([k, v]) => `${k.replace("NEC_", "").toLowerCase()}: ${v > 0 ? brl(v) : "não incluída"}`).join(" · ")}
                    </p>
                  )}
                </section>
                <section>
                  <h3 className="font-extrabold text-ink mb-2">Respostas do diagnóstico</h3>
                  <Entradas dados={f.diagnostico.entradas} />
                </section>
              </>
            ) : (
              <p className="text-[14px] text-muted">Este pedido não veio de um diagnóstico.</p>
            )}

            {f.consentimentos.length > 0 && (
              <section>
                <h3 className="font-extrabold text-ink mb-2">Consentimentos registrados</h3>
                <ul className="text-[13px] text-body space-y-1">
                  {f.consentimentos.map((c) => (
                    <li key={c.tipo}>
                      <b>{c.tipo === "ATENDIMENTO" ? "Cálculo e contato" : "Marketing"}:</b> {c.aceito ? "aceito" : "não aceito"} · {dataHora(c.aceito_em)} · IP {c.ip ?? "—"} · texto {c.texto_versao}
                      {c.revogado_em && <span className="text-danger"> · revogado em {dataHora(c.revogado_em)}</span>}
                    </li>
                  ))}
                </ul>
              </section>
            )}
          </>
        )}
      </div>
    </aside>
  );
}
