"use client";

import { useEffect, useRef, useState } from "react";
import { MessageCircle, X } from "lucide-react";
import { Aviso } from "@/components/ui";
import { api } from "@/lib/api";
import { lerFluxo, registrarEvento } from "@/lib/fluxo";

const EVENTO = "abrir-especialista";

const MOTIVOS: { id: string; texto: string }[] = [
  { id: "CAPITAL_MAIOR", texto: "Quero capital maior do que o site permite" },
  { id: "DUVIDAS_COBERTURAS", texto: "Tenho dúvidas sobre as coberturas" },
  { id: "REVISAR_SEGURO", texto: "Quero revisar o seguro que já tenho" },
];

/** Abre o formulário de qualquer tela. `motivo` já vem marcado (ex.: aviso de teto da régua). */
export function abrirEspecialista(motivo?: string) {
  window.dispatchEvent(new CustomEvent(EVENTO, { detail: { motivo } }));
}

/** Botão fixo nas telas da jornada + o formulário. Não é agenda: o time entra em contato. */
export function Especialista() {
  const [aberto, setAberto] = useState(false);
  const [enviado, setEnviado] = useState(false);
  const [enviando, setEnviando] = useState(false);
  const [erro, setErro] = useState<string | null>(null);
  const [nome, setNome] = useState("");
  const [email, setEmail] = useState("");
  const [celular, setCelular] = useState("");
  const [motivos, setMotivos] = useState<string[]>([]);
  const [mensagem, setMensagem] = useState("");
  const foco = useRef<HTMLButtonElement>(null);

  useEffect(() => {
    const abrir = (e: Event) => {
      const f = lerFluxo();
      // Pré-preenchido com o que o cliente já informou na captura de contato, e editável.
      setNome(f.contato?.nome ?? "");
      setEmail(f.contato?.email ?? "");
      setCelular(f.contato?.celular ?? "");
      const m = (e as CustomEvent<{ motivo?: string }>).detail?.motivo;
      setMotivos(m ? [m] : []);
      setMensagem(f.recado ?? "");
      setEnviado(false);
      setErro(null);
      setAberto(true);
      registrarEvento("especialista_aberto");
    };
    window.addEventListener(EVENTO, abrir);
    return () => window.removeEventListener(EVENTO, abrir);
  }, []);

  useEffect(() => {
    if (!aberto) return;
    const esc = (e: KeyboardEvent) => e.key === "Escape" && setAberto(false);
    window.addEventListener("keydown", esc);
    return () => window.removeEventListener("keydown", esc);
  }, [aberto]);

  const alternar = (id: string) => setMotivos((m) => (m.includes(id) ? m.filter((x) => x !== id) : [...m, id]));
  const podeEnviar = nome.trim().length >= 2 && email.includes("@") && celular.replace(/\D/g, "").length >= 10 && (motivos.length > 0 || mensagem.trim().length > 0);

  async function enviar(ev: React.FormEvent) {
    ev.preventDefault();
    setEnviando(true);
    setErro(null);
    const f = lerFluxo();
    try {
      await api("/v1/pedidos-especialista", {
        corpo: {
          nome: nome.trim(), email: email.trim(), celular, motivos, mensagem: mensagem.trim() || undefined,
          lead_id: f.contato?.leadId, necessidade_id: f.necessidadeId, cotacao_id: f.comparacao?.cotacao_id ?? undefined,
        },
      });
      registrarEvento("especialista_enviado");
      setEnviado(true);
    } catch (e) {
      setErro((e as Error).message);
    } finally {
      setEnviando(false);
    }
  }

  return (
    <>
      <button
        type="button"
        onClick={() => abrirEspecialista()}
        className="fixed right-4 bottom-24 lg:bottom-6 z-20 btn btn-secondary shadow-[0_8px_30px_rgba(10,31,92,0.18)] !py-3 !px-4"
      >
        <MessageCircle size={18} aria-hidden /> Falar com um especialista
      </button>

      {aberto && (
        <div className="fixed inset-0 z-40 grid place-items-end sm:place-items-center bg-[rgba(10,31,92,0.45)] p-0 sm:p-5" role="dialog" aria-modal="true" aria-labelledby="esp-titulo">
          <div className="bg-white w-full sm:max-w-[560px] max-h-[92vh] overflow-y-auto rounded-t-3xl sm:rounded-3xl p-6 sm:p-8">
            <div className="flex items-start justify-between gap-4">
              <h2 id="esp-titulo" className="text-2xl font-extrabold text-ink leading-tight">Falar com um especialista</h2>
              <button ref={foco} type="button" onClick={() => setAberto(false)} aria-label="Fechar" className="p-1 text-muted hover:text-ink"><X size={22} /></button>
            </div>

            {enviado ? (
              <div className="mt-5 space-y-4">
                <Aviso>Recebemos o seu pedido. Alguém do nosso time vai entrar em contato com você para combinar a conversa.</Aviso>
                <button type="button" className="btn btn-primary" onClick={() => setAberto(false)}>Voltar para a jornada</button>
              </div>
            ) : (
              <form onSubmit={enviar} className="mt-4 space-y-4">
                <p className="text-body text-[15px]">Deixe o seu pedido e alguém do time entra em contato para combinar a conversa. Você segue a jornada normalmente enquanto isso.</p>
                <div>
                  <label htmlFor="esp-nome" className="block font-bold text-ink mb-1.5">Nome</label>
                  <input id="esp-nome" className="field" value={nome} onChange={(e) => setNome(e.target.value)} autoComplete="name" />
                </div>
                <div className="grid sm:grid-cols-2 gap-4">
                  <div>
                    <label htmlFor="esp-email" className="block font-bold text-ink mb-1.5">E-mail</label>
                    <input id="esp-email" type="email" className="field" value={email} onChange={(e) => setEmail(e.target.value)} autoComplete="email" />
                  </div>
                  <div>
                    <label htmlFor="esp-cel" className="block font-bold text-ink mb-1.5">Telefone</label>
                    <input id="esp-cel" inputMode="tel" className="field" value={celular} onChange={(e) => setCelular(e.target.value)} placeholder="(11) 90000-0000" autoComplete="tel" />
                  </div>
                </div>
                <fieldset>
                  <legend className="font-bold text-ink mb-1.5">Motivo do contato <span className="font-medium text-muted text-sm">(pode marcar mais de um)</span></legend>
                  <div className="space-y-2">
                    {MOTIVOS.map((m) => (
                      <label key={m.id} className="flex items-center gap-3 cursor-pointer text-body">
                        <input type="checkbox" className="w-4 h-4 accent-[var(--action)]" checked={motivos.includes(m.id)} onChange={() => alternar(m.id)} />
                        {m.texto}
                      </label>
                    ))}
                  </div>
                </fieldset>
                <div>
                  <label htmlFor="esp-msg" className="block font-bold text-ink mb-1.5">Quer escrever mais alguma coisa?</label>
                  <textarea id="esp-msg" className="field" rows={3} maxLength={2000} value={mensagem} onChange={(e) => setMensagem(e.target.value)} />
                </div>
                {erro && <Aviso tom="erro">{erro}</Aviso>}
                <button className="btn btn-primary w-full" disabled={!podeEnviar || enviando}>{enviando ? "Enviando…" : "Enviar pedido"}</button>
              </form>
            )}
          </div>
        </div>
      )}
    </>
  );
}
