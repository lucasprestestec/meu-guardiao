"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useEffect, useState } from "react";
import { Check, Copy, Mail, MessageCircle, Lock } from "lucide-react";
import { Aviso, Carregando, ListaCoberturas, NomeSeguradora, Selo } from "@/components/ui";
import { useAmbiente } from "@/lib/ambiente";
import { api, ErroApi, type Acompanhamento } from "@/lib/api";
import { dataHora } from "@/lib/format";

const TITULO: Record<string, React.ReactNode> = {
  RECEBIDA: <>Recebemos sua <em>solicitação!</em></>,
  EMITIDA: <>Sua apólice <em>foi emitida!</em></>,
  RECUSADA: <>Sua solicitação <em>não foi aceita.</em></>,
  CANCELADA: <>Solicitação <em>cancelada.</em></>,
};

export default function Acompanhar() {
  const { id } = useParams<{ id: string }>();
  const [a, setA] = useState<Acompanhamento | null>(null);
  const [erro, setErro] = useState<string | null>(null);
  const [copiado, setCopiado] = useState(false);
  const amb = useAmbiente();

  useEffect(() => {
    let vivo = true;
    const buscar = () =>
      api<Acompanhamento>(`/v1/solicitacoes/${id}`)
        .then((r) => vivo && (setA(r), setErro(null)))
        .catch((e) => vivo && !a && setErro(e instanceof ErroApi && e.status === 404 ? "Não encontramos esta solicitação." : (e as Error).message));
    buscar();
    // Atualiza sozinho: quando o backoffice muda o status, a tela acompanha.
    const t = setInterval(buscar, 8000);
    return () => {
      vivo = false;
      clearInterval(t);
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [id]);

  if (erro && !a)
    return (
      <div className="mx-auto max-w-[720px] px-5 py-16 space-y-5">
        <Aviso tom="erro">{erro}</Aviso>
        <Link href="/" className="btn btn-primary w-fit">Ir para o início</Link>
      </div>
    );
  if (!a) return <Carregando texto="Carregando sua solicitação…" />;

  const avisa = !!amb?.notificacoes_ativas;
  const zap = a.notificacoes.find((n) => n.canal === "WHATSAPP");
  const email = a.notificacoes.find((n) => n.canal === "EMAIL");
  const final = ["EMITIDA", "RECUSADA", "CANCELADA"].includes(a.status);

  async function copiar() {
    try {
      await navigator.clipboard.writeText(window.location.href);
      setCopiado(true);
      setTimeout(() => setCopiado(false), 2000);
    } catch {
      /* sem permissão de área de transferência */
    }
  }

  return (
    <>
      <div className="mx-auto max-w-[1180px] px-5 py-10">
        <p className="text-[12px] font-bold tracking-[0.14em] uppercase text-action mb-3">
          {a.status === "RECEBIDA" ? "Sua solicitação foi enviada com sucesso" : "Acompanhamento da contratação"}
        </p>
        <h1 className="titulo text-[clamp(2.6rem,5.5vw,4.2rem)]">{TITULO[a.status] ?? <>Acompanhe sua <em>solicitação.</em></>}</h1>
        <p className="text-lg text-body mt-3">
          {a.status === "EMITIDA" ? "A partir de agora você está protegido(a)." : final ? "Veja abaixo o histórico." : "Já estamos trabalhando para concluir a sua contratação."}
        </p>

        <div className="mt-8 grid lg:grid-cols-[1.25fr_1fr] gap-6 items-start">
          <div className="space-y-5">
            {a.status === "PENDENCIA" && (
              <div className="rounded-3xl bg-amber-tint p-6" role="alert">
                <Selo tom="amber">Ação necessária</Selo>
                <h2 className="text-xl font-extrabold mt-2">Precisamos de uma informação</h2>
                <p className="text-[#6b470d] mt-1">{a.pendencia}</p>
                <p className="text-[14px] text-[#6b470d] mt-2">
                  {avisa
                    ? "Responda pelo WhatsApp ou e-mail cadastrados e seguimos com a análise."
                    : "Nossa equipe vai entrar em contato pelos dados que você informou."}
                </p>
              </div>
            )}
            {a.status === "RECEBIDA" && (
              <div className="rounded-3xl bg-teal-tint p-6 flex gap-4 items-center">
                <span className="grid place-items-center w-14 h-14 rounded-full bg-teal text-white shrink-0"><Check size={30} strokeWidth={3} aria-hidden /></span>
                <div>
                  <h2 className="text-xl font-extrabold">Solicitação recebida com sucesso!</h2>
                  <p className="text-body">
                    {avisa ? "Você será atualizado por WhatsApp e e-mail a cada etapa." : "Acompanhe cada etapa por esta página: ela se atualiza sozinha."}
                  </p>
                </div>
              </div>
            )}
            {a.status === "EMITIDA" && a.numero_apolice && (
              <div className="rounded-3xl bg-teal-tint p-6">
                <h2 className="text-xl font-extrabold">Apólice nº {a.numero_apolice}</h2>
              </div>
            )}
            {(a.status === "RECUSADA" || a.status === "CANCELADA") && (
              <Aviso tom="alerta">
                {a.status === "RECUSADA"
                  ? "A seguradora não aceitou a proposta desta vez. Nossa equipe vai entrar em contato para explicar e apresentar alternativas."
                  : "Esta solicitação foi cancelada. Se foi engano, comece uma nova comparação."}
              </Aviso>
            )}

            <section className="card p-6" aria-label="Andamento">
              <h2 className="text-xl font-extrabold">Acompanhe o andamento da sua contratação</h2>
              <p className="text-body text-[15px]">{avisa ? "Vamos te avisar em cada etapa." : "Esta página se atualiza sozinha a cada mudança."}</p>
              <ol className="mt-5">
                {a.regua.map((p, i) => (
                  <li key={p.codigo} className="flex gap-4" aria-current={p.estado === "EM_ANDAMENTO" ? "step" : undefined}>
                    <div className="flex flex-col items-center">
                      <span
                        className={`grid place-items-center w-9 h-9 rounded-full shrink-0 text-sm font-bold ${
                          p.estado === "CONCLUIDO" ? "bg-teal text-white" : p.estado === "EM_ANDAMENTO" ? "bg-white border-[6px] border-action" : "bg-blue-tint text-muted"
                        }`}
                      >
                        {p.estado === "CONCLUIDO" ? <Check size={18} strokeWidth={3} aria-hidden /> : p.estado === "EM_ANDAMENTO" ? "" : i + 1}
                      </span>
                      {i < a.regua.length - 1 && <span className={`w-0.5 flex-1 min-h-6 ${p.estado === "CONCLUIDO" ? "bg-teal" : "bg-line"}`} aria-hidden />}
                    </div>
                    <div className="pb-5 flex-1 flex justify-between gap-3">
                      <div>
                        <div className={`font-bold ${p.estado === "AGUARDANDO" ? "text-body" : p.estado === "CONCLUIDO" ? "text-teal" : "text-action"}`}>{p.rotulo}</div>
                        <div className="text-[14px] text-body">
                          {p.em && p.estado !== "AGUARDANDO" ? dataHora(p.em) : p.descricao}
                        </div>
                      </div>
                      <span className="self-start">
                        <Selo tom={p.estado === "CONCLUIDO" ? "teal" : p.estado === "EM_ANDAMENTO" ? "blue" : "cinza"}>
                          {p.estado === "CONCLUIDO" ? "Concluído" : p.estado === "EM_ANDAMENTO" ? (a.status === "PENDENCIA" ? "Pendência" : "Em andamento") : "Aguardando"}
                        </Selo>
                      </span>
                    </div>
                  </li>
                ))}
              </ol>
            </section>
          </div>

          <div className="space-y-5">
            <section className="card p-6">
              <h2 className="text-lg font-extrabold">{avisa ? "Última mensagem enviada a você" : "Prévia da mensagem ao cliente"}</h2>
              {!avisa && <p className="text-[13px] text-muted mt-1">Demonstração: o envio automático ainda não está ativo. Hoje a equipe envia pelo backoffice.</p>}
              <div className="mt-4 grid sm:grid-cols-2 gap-3">
                {zap && (
                  <div className="rounded-2xl border border-line p-3">
                    <div className="flex items-center gap-2 font-semibold text-ink text-sm"><MessageCircle size={18} className="text-[#25a244]" aria-hidden /> WhatsApp</div>
                    <p className="mt-2 rounded-xl bg-[#e8f5e0] p-3 text-[13px] text-ink leading-snug">{zap.mensagem}</p>
                  </div>
                )}
                {email && (
                  <div className="rounded-2xl border border-line p-3">
                    <div className="flex items-center gap-2 font-semibold text-ink text-sm"><Mail size={18} className="text-action" aria-hidden /> E-mail</div>
                    <p className="mt-2 text-[13px] text-body leading-snug"><b className="text-ink">Atualização da sua solicitação</b><br />{email.mensagem}</p>
                  </div>
                )}
              </div>
            </section>

            <section className="card p-6">
              <h2 className="text-lg font-extrabold">Seu plano selecionado</h2>
              <div className="mt-3 flex items-baseline justify-between">
                <NomeSeguradora nome={a.plano.seguradora} />
                <span className="text-2xl font-extrabold text-ink">R$ {Math.round(a.plano.premio_mensal).toLocaleString("pt-BR")}<span className="text-sm text-muted font-semibold">/mês</span></span>
              </div>
              <div className="text-[13px] text-muted">{a.plano.produto}</div>
              <div className="mt-2"><ListaCoberturas itens={a.plano.itens} /></div>
            </section>
          </div>
        </div>

        <div className="mt-8 flex flex-wrap items-center gap-4">
          <button type="button" onClick={copiar} className="btn btn-primary">
            {copiado ? <Check size={18} aria-hidden /> : <Copy size={18} aria-hidden />} {copiado ? "Link copiado" : "Copiar link de acompanhamento"}
          </button>
          <Link href="/" className="btn btn-secondary">Voltar ao início</Link>
          <span className="flex items-center gap-2 text-[13px] text-muted"><Lock size={16} aria-hidden /> Guarde este link: é por ele que você acompanha sua solicitação.</span>
        </div>
      </div>
    </>
  );
}
