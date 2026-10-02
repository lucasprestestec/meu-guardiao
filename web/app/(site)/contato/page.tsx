"use client";

import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { Suspense, useEffect, useState } from "react";
import { ArrowRight } from "lucide-react";
import { Aviso, Carregando } from "@/components/ui";
import { api, ErroApi } from "@/lib/api";
import { gravarFluxo, lerFluxo, registrarEvento } from "@/lib/fluxo";

type Textos = { versao: string; atendimento: string; marketing: string; apoio: string; politica_url: string };

// Os textos vêm da API: o que o cliente lê é exatamente o que fica registrado com a versão.
// ESTRUTURA PRONTA, TEXTO EM RASCUNHO: em revisão jurídica, não publicar como definitivo.
function Captura() {
  const router = useRouter();
  const n = useSearchParams().get("n");
  const [textos, setTextos] = useState<Textos | null>(null);
  const [nome, setNome] = useState("");
  const [email, setEmail] = useState("");
  const [celular, setCelular] = useState("");
  const [atendimento, setAtendimento] = useState(false); // nunca pré-marcadas
  const [marketing, setMarketing] = useState(false);
  const [enviando, setEnviando] = useState(false);
  const [erro, setErro] = useState<string | null>(null);

  useEffect(() => {
    const f = lerFluxo();
    if (f.contato) {
      setNome(f.contato.nome);
      setEmail(f.contato.email);
      setCelular(f.contato.celular);
    }
    registrarEvento("contato_visto");
    api<Textos>("/v1/lead/textos").then(setTextos).catch((e) => setErro((e as Error).message));
  }, []);

  const valido = nome.trim().length >= 2 && /\S+@\S+\.\S+/.test(email) && celular.replace(/\D/g, "").length >= 10;

  async function continuar(ev: React.FormEvent) {
    ev.preventDefault();
    setEnviando(true);
    setErro(null);
    try {
      const r = await api<{ id: string }>("/v1/leads", {
        corpo: {
          nome: nome.trim(), email: email.trim(), celular, necessidade_id: n ?? undefined,
          consentimento_atendimento: atendimento, consentimento_marketing: marketing,
        },
      });
      gravarFluxo({ contato: { nome: nome.trim(), email: email.trim(), celular, leadId: r.id } });
      registrarEvento("contato_enviado");
      router.push(n ? `/mapa/${n}` : "/");
    } catch (e) {
      setErro(e instanceof ErroApi ? e.message : "Não foi possível continuar. Tente novamente.");
      setEnviando(false);
    }
  }

  if (!textos && !erro) return <Carregando />;

  return (
    <div className="mx-auto max-w-[620px] px-5 py-10">
      <p className="text-[12px] font-bold tracking-[0.14em] uppercase text-action mb-3">Falta só um passo</p>
      <h1 className="titulo text-[clamp(2.2rem,5vw,3.4rem)]">
        Para onde enviamos o <em>seu resultado?</em>
      </h1>
      <p className="text-lg text-body mt-3">Informe seus dados de contato para ver o seu Mapa de Proteção. Não precisa de senha nem de conta.</p>

      <form onSubmit={continuar} className="card p-6 sm:p-8 mt-6 space-y-5">
        <div>
          <label htmlFor="c-nome" className="block font-bold text-ink mb-1.5">Nome</label>
          <input id="c-nome" className="field" value={nome} onChange={(e) => setNome(e.target.value)} autoComplete="name" />
        </div>
        <div className="grid sm:grid-cols-2 gap-4">
          <div>
            <label htmlFor="c-email" className="block font-bold text-ink mb-1.5">E-mail</label>
            <input id="c-email" type="email" className="field" value={email} onChange={(e) => setEmail(e.target.value)} autoComplete="email" />
          </div>
          <div>
            <label htmlFor="c-cel" className="block font-bold text-ink mb-1.5">Telefone (com DDD)</label>
            <input id="c-cel" inputMode="tel" className="field" value={celular} onChange={(e) => setCelular(e.target.value)} placeholder="(11) 90000-0000" autoComplete="tel" />
          </div>
        </div>

        {textos && (
          <div className="space-y-3 border-t border-line pt-5">
            <label className="flex items-start gap-3 cursor-pointer text-[14px] text-body leading-snug">
              <input type="checkbox" className="mt-0.5 w-4 h-4 shrink-0 accent-[var(--action)]" checked={atendimento} onChange={(e) => setAtendimento(e.target.checked)} />
              <span>
                {textos.atendimento.replace(" Li e concordo com a Política de Privacidade.", "")} Li e concordo com a{" "}
                <Link href={textos.politica_url} target="_blank" className="font-semibold text-action underline">Política de Privacidade</Link>.
                <span className="text-muted"> (obrigatório para continuar)</span>
              </span>
            </label>
            <label className="flex items-start gap-3 cursor-pointer text-[14px] text-body leading-snug">
              <input type="checkbox" className="mt-0.5 w-4 h-4 shrink-0 accent-[var(--action)]" checked={marketing} onChange={(e) => setMarketing(e.target.checked)} />
              <span>{textos.marketing} <span className="text-muted">(opcional)</span></span>
            </label>
            <p className="text-[13px] text-muted">{textos.apoio}</p>
          </div>
        )}

        {erro && <Aviso tom="erro">{erro}</Aviso>}
        <button className="btn btn-primary w-full" disabled={!valido || !atendimento || enviando}>
          {enviando ? "Continuando…" : "Ver meu Mapa de Proteção"} {!enviando && <ArrowRight size={18} aria-hidden />}
        </button>
      </form>
    </div>
  );
}

export default function Contato() {
  return (
    <Suspense fallback={<Carregando />}>
      <Captura />
    </Suspense>
  );
}
