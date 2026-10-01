"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import { AlertTriangle, Clock, LogOut, Mail, MessageCircle, Search, X } from "lucide-react";
import { Aviso, Logo, Selo } from "@/components/ui";
import { api, ErroApi, type Ficha, type LinhaFila } from "@/lib/api";
import { useAmbiente } from "@/lib/ambiente";
import { nomeCobertura } from "@/lib/coberturas";
import { brl, capitalCurto, dataHora, haQuanto, nomeSeguradora } from "@/lib/format";

const CHAVE = "dor.bo.chave";

const STATUS: Record<string, { texto: string; tom: "blue" | "amber" | "teal" | "violet" | "danger" | "cinza" }> = {
  RECEBIDA: { texto: "Recebida", tom: "blue" },
  EM_PREPARACAO: { texto: "Em preparação", tom: "blue" },
  ENVIADA: { texto: "Enviada", tom: "violet" },
  EM_ANALISE: { texto: "Em análise", tom: "amber" },
  PENDENCIA: { texto: "Pendência", tom: "danger" },
  APROVADA: { texto: "Aprovada", tom: "teal" },
  EMITIDA: { texto: "Emitida", tom: "teal" },
  RECUSADA: { texto: "Recusada", tom: "cinza" },
  CANCELADA: { texto: "Cancelada", tom: "cinza" },
};
const VEZ: Record<string, string> = { NOS: "Nossa equipe", CLIENTE: "Cliente", SEGURADORA: "Seguradora", FIM: "—" };
const AVANCAR: Record<string, string> = {
  RECEBIDA: "EM_PREPARACAO", EM_PREPARACAO: "ENVIADA", ENVIADA: "EM_ANALISE",
  EM_ANALISE: "APROVADA", PENDENCIA: "EM_ANALISE", APROVADA: "EMITIDA",
};

type Resumo = { hoje: number; em_analise: number; pendencias: number; emitidas_30d: number; para_nos: number };
type Filtro = { tipo: "todos" | "nos" | "pendencia" | "seguradora" | "emitida" };

export default function Backoffice() {
  const [chave, setChave] = useState<string | null>(null);
  const [lido, setLido] = useState(false);
  useEffect(() => {
    try {
      setChave(sessionStorage.getItem(CHAVE));
    } catch { /* sem storage */ }
    setLido(true);
  }, []);
  if (!lido) return null;
  if (!chave)
    return <Entrada onEntrar={(k) => { try { sessionStorage.setItem(CHAVE, k); } catch { /* ok */ } setChave(k); }} />;
  return <Painel chave={chave} onSair={() => { try { sessionStorage.removeItem(CHAVE); } catch { /* ok */ } setChave(null); }} />;
}

function Entrada({ onEntrar }: { onEntrar: (k: string) => void }) {
  const [k, setK] = useState("");
  const [erro, setErro] = useState<string | null>(null);
  const [testando, setTestando] = useState(false);
  async function entrar(ev: React.FormEvent) {
    ev.preventDefault();
    setTestando(true);
    setErro(null);
    try {
      await api("/v1/backoffice/resumo", { headers: { "x-backoffice-key": k } });
      onEntrar(k);
    } catch (e) {
      setErro(e instanceof ErroApi && e.status === 401 ? "Chave incorreta." : (e as Error).message);
      setTestando(false);
    }
  }
  return (
    <div className="min-h-screen grid place-items-center px-5">
      <form onSubmit={entrar} className="card p-8 w-full max-w-[420px] space-y-5">
        <div><Logo /> <span className="text-muted font-semibold ml-2">Backoffice</span></div>
        <div>
          <label htmlFor="k" className="block font-bold text-ink mb-1.5">Chave de acesso</label>
          <input id="k" type="password" className="field" value={k} onChange={(e) => setK(e.target.value)} autoFocus />
        </div>
        {erro && <Aviso tom="erro">{erro}</Aviso>}
        <button className="btn btn-primary w-full" disabled={!k || testando}>{testando ? "Verificando…" : "Entrar"}</button>
      </form>
    </div>
  );
}

function Painel({ chave, onSair }: { chave: string; onSair: () => void }) {
  const H = useMemo(() => ({ "x-backoffice-key": chave }), [chave]);
  const [resumo, setResumo] = useState<Resumo | null>(null);
  const [linhas, setLinhas] = useState<LinhaFila[]>([]);
  const [seguradoras, setSeguradoras] = useState<string[]>([]);
  const [erro, setErro] = useState<string | null>(null);
  const [busca, setBusca] = useState("");
  const [seg, setSeg] = useState("");
  const [status, setStatus] = useState("");
  const [filtro, setFiltro] = useState<Filtro>({ tipo: "todos" });
  const [aberta, setAberta] = useState<string | null>(null);
  const [aviso, setAviso] = useState<string | null>(null);

  const carregar = useCallback(async () => {
    try {
      const [r, f] = await Promise.all([
        api<Resumo>("/v1/backoffice/resumo", { headers: H }),
        api<{ solicitacoes: LinhaFila[]; seguradoras: string[] }>("/v1/backoffice/solicitacoes?dias=90", { headers: H }),
      ]);
      setResumo(r);
      setLinhas(f.solicitacoes);
      setSeguradoras(f.seguradoras);
      setErro(null);
    } catch (e) {
      if (e instanceof ErroApi && e.status === 401) onSair();
      else setErro((e as Error).message);
    }
  }, [H, onSair]);

  useEffect(() => {
    carregar();
    const t = setInterval(carregar, 15000);
    return () => clearInterval(t);
  }, [carregar]);

  const visiveis = linhas.filter((l) => {
    if (busca && !l.nome.toLowerCase().includes(busca.toLowerCase())) return false;
    if (seg && l.seguradora !== seg) return false;
    if (status && l.status !== status) return false;
    if (filtro.tipo === "nos") return l.com_quem === "NOS";
    if (filtro.tipo === "pendencia") return l.status === "PENDENCIA";
    if (filtro.tipo === "seguradora") return l.com_quem === "SEGURADORA";
    if (filtro.tipo === "emitida") return l.status === "EMITIDA";
    return true;
  });

  const kpis: { chave: Filtro["tipo"]; rotulo: string; valor: number | undefined; destaque?: boolean }[] = [
    { chave: "nos", rotulo: "Aguardando nossa equipe", valor: resumo?.para_nos, destaque: true },
    { chave: "pendencia", rotulo: "Pendências", valor: resumo?.pendencias },
    { chave: "seguradora", rotulo: "Com a seguradora", valor: resumo?.em_analise },
    { chave: "emitida", rotulo: "Emitidas (30 dias)", valor: resumo?.emitidas_30d },
  ];

  return (
    <div className="min-h-screen flex flex-col">
      <header className="bg-white border-b border-line">
        <div className="px-6 h-16 flex items-center justify-between">
          <div className="flex items-center gap-3"><Logo /><span className="text-muted font-semibold border-l border-line pl-3">Backoffice</span></div>
          <button onClick={onSair} className="flex items-center gap-2 text-muted font-semibold hover:text-ink"><LogOut size={17} aria-hidden /> Sair</button>
        </div>
      </header>

      <main className="flex-1 px-6 py-6">
        <div className="flex items-end justify-between gap-4 mb-5">
          <h1 className="text-3xl font-extrabold text-ink tracking-tight">Solicitações</h1>
          {aviso && <span role="status" className="text-teal font-semibold text-sm">{aviso}</span>}
        </div>
        {erro && <div className="mb-4"><Aviso tom="erro">{erro}</Aviso></div>}

        <div className="grid grid-cols-2 lg:grid-cols-4 gap-3 mb-5">
          {kpis.map((k) => {
            const ativo = filtro.tipo === k.chave;
            return (
              <button
                key={k.chave}
                onClick={() => setFiltro(ativo ? { tipo: "todos" } : { tipo: k.chave })}
                aria-pressed={ativo}
                className={`text-left rounded-2xl border px-5 py-4 transition-colors ${ativo ? "border-action bg-blue-tint" : "border-line bg-white hover:border-[#c5d8f3]"}`}
              >
                <div className={`text-3xl font-extrabold ${k.destaque && (k.valor ?? 0) > 0 ? "text-action" : "text-ink"}`}>{k.valor ?? "–"}</div>
                <div className="text-[13px] font-semibold text-muted">{k.rotulo}</div>
              </button>
            );
          })}
        </div>

        <div className="flex flex-wrap gap-3 mb-4">
          <div className="relative flex-1 min-w-[220px]">
            <Search size={17} className="absolute left-3.5 top-1/2 -translate-y-1/2 text-muted" aria-hidden />
            <input className="field !pl-10" placeholder="Buscar por nome do cliente" value={busca} onChange={(e) => setBusca(e.target.value)} aria-label="Buscar por nome do cliente" />
          </div>
          <select className="field !w-auto" value={seg} onChange={(e) => setSeg(e.target.value)} aria-label="Seguradora">
            <option value="">Todas as seguradoras</option>
            {seguradoras.map((s) => <option key={s} value={s}>{nomeSeguradora(s)}</option>)}
          </select>
          <select className="field !w-auto" value={status} onChange={(e) => setStatus(e.target.value)} aria-label="Status">
            <option value="">Todos os status</option>
            {Object.entries(STATUS).map(([k, v]) => <option key={k} value={k}>{v.texto}</option>)}
          </select>
        </div>

        <div className="card overflow-x-auto">
          <table className="w-full text-[15px] min-w-[860px]">
            <thead>
              <tr className="text-left text-[13px] text-muted border-b border-line">
                {["Cliente", "Status", "Vez de", "Parado há", "Seguradora / produto", "Prêmio"].map((h) => <th key={h} className="px-4 py-3 font-semibold">{h}</th>)}
              </tr>
            </thead>
            <tbody>
              {visiveis.length === 0 && (
                <tr><td colSpan={6} className="px-4 py-12 text-center text-muted">Nenhuma solicitação com esses filtros.</td></tr>
              )}
              {visiveis.map((l) => {
                const parado = haQuanto(l.status_desde);
                const atrasada = l.com_quem !== "FIM" && parado.horas >= 24;
                return (
                  <tr
                    key={l.id}
                    onClick={() => setAberta(l.id)}
                    tabIndex={0}
                    onKeyDown={(e) => e.key === "Enter" && setAberta(l.id)}
                    className={`border-b border-line last:border-0 cursor-pointer hover:bg-canvas focus:bg-canvas focus:outline-none ${aberta === l.id ? "bg-blue-tint" : ""}`}
                  >
                    <td className="px-4 py-3.5 font-bold text-ink">{l.nome}</td>
                    <td className="px-4 py-3.5">
                      <Selo tom={STATUS[l.status].tom}>{STATUS[l.status].texto}</Selo>
                      {l.pendencia && <span className="block text-[13px] text-danger mt-1 max-w-[220px]">{l.pendencia}</span>}
                    </td>
                    <td className="px-4 py-3.5 text-body">{VEZ[l.com_quem]}</td>
                    <td className={`px-4 py-3.5 ${atrasada ? "text-danger font-bold" : "text-body"}`}>
                      {l.com_quem === "FIM" ? "—" : <span className="flex items-center gap-1.5">{atrasada && <AlertTriangle size={15} aria-hidden />}{parado.texto}</span>}
                    </td>
                    <td className="px-4 py-3.5"><span className="font-semibold text-ink">{nomeSeguradora(l.seguradora)}</span><span className="block text-[13px] text-muted">{l.produto}</span></td>
                    <td className="px-4 py-3.5">{brl(l.premio_mensal)}</td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
        <p className="text-[13px] text-muted mt-3">Ordenado por quem precisa agir: nossa equipe primeiro, do mais antigo para o mais novo. Últimos 90 dias.</p>
      </main>

      {aberta && (
        <Gaveta
          id={aberta}
          H={H}
          onFechar={() => setAberta(null)}
          onMudou={(msg) => {
            setAviso(msg);
            setTimeout(() => setAviso(null), 3500);
            carregar();
          }}
        />
      )}
    </div>
  );
}

function Gaveta({ id, H, onFechar, onMudou }: { id: string; H: Record<string, string>; onFechar: () => void; onMudou: (m: string) => void }) {
  const [f, setF] = useState<Ficha | null>(null);
  const [erro, setErro] = useState<string | null>(null);
  const [modo, setModo] = useState<null | "pendencia" | "emitir" | "cancelar">(null);
  const [texto, setTexto] = useState("");
  const [enviando, setEnviando] = useState(false);
  const amb = useAmbiente();

  const buscar = useCallback(
    () => api<Ficha>(`/v1/backoffice/solicitacoes/${id}`, { headers: H }).then((r) => { setF(r); setErro(null); }).catch((e) => setErro((e as Error).message)),
    [id, H],
  );
  useEffect(() => {
    setF(null);
    setModo(null);
    setTexto("");
    buscar();
  }, [buscar]);

  async function mudar(status: string, extra: Record<string, string> = {}) {
    setEnviando(true);
    setErro(null);
    try {
      await api(`/v1/backoffice/solicitacoes/${id}/status`, { headers: H, corpo: { status, por: "backoffice", ...extra } });
      setModo(null);
      setTexto("");
      await buscar();
      onMudou(`Status atualizado para ${STATUS[status].texto}. Mensagens registradas para o cliente.`);
    } catch (e) {
      setErro((e as Error).message);
    } finally {
      setEnviando(false);
    }
  }

  const proximo = f ? AVANCAR[f.status] : undefined;
  const ultimaMsg = f?.notificacoes.find((n) => n.canal === "WHATSAPP")?.mensagem;
  const wa = f && ultimaMsg ? `https://wa.me/55${f.cliente.celular}?text=${encodeURIComponent(ultimaMsg)}` : null;
  const ultimoEmail = f?.notificacoes.find((n) => n.canal === "EMAIL")?.mensagem;
  const mail = f && ultimoEmail
    ? `mailto:${f.cliente.email}?subject=${encodeURIComponent("Atualização da sua solicitação de seguro")}&body=${encodeURIComponent(ultimoEmail)}`
    : null;

  return (
    <aside className="fixed inset-y-0 right-0 w-full sm:w-[440px] bg-white border-l border-line shadow-[-12px_0_40px_rgba(10,31,92,0.10)] overflow-y-auto z-20" aria-label="Detalhes da solicitação">
      <div className="p-6 space-y-6">
        <div className="flex items-start justify-between gap-3">
          <div>
            <h2 className="text-2xl font-extrabold text-ink leading-tight">{f?.cliente.nome ?? "Carregando…"}</h2>
            {f && <div className="mt-1.5 flex items-center gap-2"><Selo tom={STATUS[f.status].tom}>{STATUS[f.status].texto}</Selo><span className="text-[13px] text-muted flex items-center gap-1"><Clock size={13} aria-hidden /> desde {dataHora(f.status_desde)}</span></div>}
          </div>
          <button onClick={onFechar} aria-label="Fechar" className="p-1 text-muted hover:text-ink"><X size={22} /></button>
        </div>

        {erro && <Aviso tom="erro">{erro}</Aviso>}

        {f && (
          <>
            {f.demonstracao && <p className="text-[12px] font-bold text-amber bg-amber-tint rounded-lg px-3 py-1.5">Demonstração: produto fictício</p>}
            {f.pendencia && <Aviso tom="alerta"><b>Pendência:</b> {f.pendencia}</Aviso>}

            {f.proximos_status.length > 0 && (
              <section aria-label="Ações" className="space-y-3">
                {proximo && modo !== "emitir" && (
                  <button
                    className="btn btn-primary w-full"
                    disabled={enviando}
                    onClick={() => (proximo === "EMITIDA" ? setModo("emitir") : mudar(proximo))}
                  >
                    Avançar para {STATUS[proximo].texto}
                  </button>
                )}
                {modo === "emitir" && (
                  <div className="rounded-2xl bg-teal-tint p-4 space-y-3">
                    <label htmlFor="ap" className="font-bold text-ink block">Número da apólice</label>
                    <input id="ap" className="field" value={texto} onChange={(e) => setTexto(e.target.value)} placeholder="Ex.: 1234567" autoFocus />
                    <div className="flex gap-2">
                      <button className="btn btn-primary flex-1" disabled={enviando || !texto.trim()} onClick={() => mudar("EMITIDA", { numero_apolice: texto.trim() })}>Confirmar emissão</button>
                      <button className="btn btn-soft" onClick={() => setModo(null)}>Voltar</button>
                    </div>
                  </div>
                )}
                {modo === "pendencia" && (
                  <div className="rounded-2xl bg-amber-tint p-4 space-y-3">
                    <label htmlFor="pd" className="font-bold text-ink block">O que falta? (o cliente recebe este texto)</label>
                    <textarea id="pd" className="field" rows={3} value={texto} onChange={(e) => setTexto(e.target.value)} placeholder="Ex.: Enviar exame complementar" autoFocus />
                    <div className="flex gap-2">
                      <button className="btn btn-primary flex-1" disabled={enviando || !texto.trim()} onClick={() => mudar("PENDENCIA", { pendencia: texto.trim() })}>Registrar pendência</button>
                      <button className="btn btn-soft" onClick={() => setModo(null)}>Voltar</button>
                    </div>
                  </div>
                )}
                {modo === "cancelar" && (
                  <div className="rounded-2xl bg-danger-tint p-4 space-y-3">
                    <p className="font-bold text-danger">Cancelar esta solicitação? Não dá para desfazer.</p>
                    <div className="flex gap-2">
                      <button className="btn flex-1 bg-danger text-white" disabled={enviando} onClick={() => mudar("CANCELADA")}>Sim, cancelar</button>
                      <button className="btn btn-soft" onClick={() => setModo(null)}>Voltar</button>
                    </div>
                  </div>
                )}
                {!modo && (
                  <div className="flex flex-wrap gap-2 text-[14px]">
                    {f.proximos_status.includes("PENDENCIA") && <button className="btn btn-soft !py-2 !px-4" onClick={() => setModo("pendencia")}>Registrar pendência</button>}
                    {f.proximos_status.includes("RECUSADA") && <button className="btn btn-soft !py-2 !px-4" disabled={enviando} onClick={() => mudar("RECUSADA")}>Recusada pela seguradora</button>}
                    {f.proximos_status.includes("CANCELADA") && <button className="btn !py-2 !px-4 text-danger hover:bg-danger-tint" onClick={() => setModo("cancelar")}>Cancelar</button>}
                  </div>
                )}
              </section>
            )}

            {!f.condicoes_gerais.url && f.status !== "CANCELADA" && (
              <Aviso tom="alerta">
                <b>Condições gerais não cadastradas.</b> Envie hoje ao cliente, manualmente, as condições gerais do produto e da seguradora.
              </Aviso>
            )}

            {mail && (
              <a href={mail} className="btn btn-secondary w-full">
                <Mail size={18} aria-hidden /> Abrir e-mail com a mensagem pronta
              </a>
            )}

            {wa && (
              <div>
                <a href={wa} target="_blank" rel="noreferrer" className={`btn w-full ${amb?.notificacoes_ativas ? "btn-secondary" : "btn-primary"}`}>
                  <MessageCircle size={18} aria-hidden /> Abrir WhatsApp com a mensagem pronta
                </a>
                {!amb?.notificacoes_ativas && (
                  <p className="text-[12px] text-muted mt-1.5">O envio automático ainda não está ativo: por enquanto a equipe envia a mensagem por aqui.</p>
                )}
              </div>
            )}

            <section>
              <h3 className="font-extrabold text-ink mb-2">Cliente</h3>
              <dl className="text-[15px] divide-y divide-line">
                {[
                  ["Celular", f.cliente.celular.replace(/^(\d{2})(\d{4,5})(\d{4})$/, "($1) $2-$3")],
                  ["E-mail", f.cliente.email],
                  ["CPF", `final ${f.cliente.cpf_final}`],
                  ["Cidade", [f.cliente.cidade, f.cliente.uf].filter(Boolean).join(" / ") || "—"],
                  ["Profissão", f.cliente.profissao || "—"],
                ].map(([k, v]) => (
                  <div key={k} className="flex justify-between gap-4 py-2"><dt className="text-muted">{k}</dt><dd className="font-semibold text-ink text-right break-all">{v}</dd></div>
                ))}
              </dl>
            </section>

            <section>
              <h3 className="font-extrabold text-ink mb-2">Proposta</h3>
              <div className="flex justify-between"><span className="font-semibold text-ink">{nomeSeguradora(f.plano.seguradora)} · {f.plano.produto}</span><span className="font-extrabold">{brl(f.plano.premio_mensal)}/mês</span></div>
              <ul className="mt-2 text-[15px] divide-y divide-line">
                {f.plano.itens.filter((i) => i.cobertura).map((i) => (
                  <li key={i.necessidade} className="flex justify-between py-1.5"><span className="text-body">{nomeCobertura(i.cobertura)}</span><span className="font-semibold">{capitalCurto(i.capital_contratado, i.necessidade === "NEC_RENDA")}</span></li>
                ))}
              </ul>
            </section>

            <section>
              <h3 className="font-extrabold text-ink mb-2">Histórico</h3>
              <ol className="space-y-2.5 text-[14px]">
                {[...f.historico].reverse().map((h, i) => (
                  <li key={i} className="border-l-2 border-line pl-3">
                    <b className="text-ink">{STATUS[h.status].texto}</b> <span className="text-muted">· {dataHora(h.em)} · {h.por}</span>
                    {h.nota && <div className="text-body">{h.nota}</div>}
                  </li>
                ))}
              </ol>
            </section>
          </>
        )}
      </div>
    </aside>
  );
}
