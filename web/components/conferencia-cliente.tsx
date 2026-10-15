"use client";

import { useCallback, useEffect, useState } from "react";
import { Check } from "lucide-react";
import { Aviso, Selo } from "@/components/ui";
import { api, ErroApi, type ConferenciaCliente } from "@/lib/api";
import { dataHora } from "@/lib/format";
import { ROTULO_CAMPO, valorCampo } from "@/lib/rotulos";

/** Depois que a equipe copia a proposta e a DPS para o portal da seguradora, o cliente confere o que
 *  foi informado. Só aparece quando a equipe pede a conferência. */
export function ConferenciaDoCliente({ id }: { id: string }) {
  const [c, setC] = useState<ConferenciaCliente | null>(null);
  const [apontando, setApontando] = useState(false);
  const [nota, setNota] = useState("");
  const [enviando, setEnviando] = useState(false);
  const [erro, setErro] = useState<string | null>(null);

  const buscar = useCallback(
    () => api<ConferenciaCliente>(`/v1/solicitacoes/${id}/conferencia`).then(setC).catch(() => setC(null)),
    [id],
  );
  useEffect(() => {
    buscar();
    const t = setInterval(buscar, 20000);
    return () => clearInterval(t);
  }, [buscar]);

  async function responder(acao: "confirmar" | "corrigir") {
    setEnviando(true);
    setErro(null);
    try {
      await api(`/v1/solicitacoes/${id}/conferencia`, { corpo: { acao, nota: acao === "corrigir" ? nota.trim() : undefined } });
      setApontando(false);
      setNota("");
      await buscar();
    } catch (e) {
      setErro(e instanceof ErroApi ? e.message : "Não foi possível enviar. Tente de novo.");
    } finally {
      setEnviando(false);
    }
  }

  if (!c || c.estado === "NENHUMA") return null;

  if (c.estado === "CONFIRMADA")
    return (
      <div className="rounded-3xl bg-teal-tint p-5 flex gap-3 items-center">
        <span className="grid place-items-center w-9 h-9 rounded-full bg-teal text-white shrink-0"><Check size={20} strokeWidth={3} aria-hidden /></span>
        <p className="text-ink"><b>Você confirmou</b> o que foi informado à seguradora{c.respondida_em ? ` em ${dataHora(c.respondida_em)}` : ""}.</p>
      </div>
    );

  if (c.estado === "CONTESTADA")
    return (
      <Aviso tom="alerta">
        <b>Você apontou um erro.</b> Nossa equipe vai corrigir e pedir uma nova conferência.
      </Aviso>
    );

  const campos = Object.entries(c.proposta?.campos ?? {}).filter(([, v]) => v !== null);
  return (
    <section className="rounded-3xl bg-amber-tint p-6 space-y-4" role="alert" aria-label="Conferência">
      <div>
        <Selo tom="amber">Ação necessária</Selo>
        <h2 className="text-xl font-extrabold mt-2">Confira o que informamos à {c.seguradora}</h2>
        <p className="text-[#6b470d] mt-1">Veja se está tudo certo. Se algo estiver errado, avise antes de a seguradora analisar.</p>
      </div>

      <div className="rounded-2xl bg-white p-4">
        <h3 className="font-bold text-ink">Suas respostas de saúde</h3>
        <ol className="mt-2 text-[14px]">
          {(c.dps ?? []).map((q, i) => (
            <li key={i} className="py-2 border-b border-line last:border-0">
              <div className="text-muted">{q.pergunta}</div>
              <div className="font-semibold text-ink">{q.resposta}</div>
            </li>
          ))}
        </ol>
      </div>

      <div className="rounded-2xl bg-white p-4">
        <h3 className="font-bold text-ink">Dados da proposta</h3>
        <dl className="mt-2 text-[14px]">
          {campos.map(([k, v]) => (
            <div key={k} className="flex justify-between gap-4 py-1.5 border-b border-line last:border-0">
              <dt className="text-muted">{ROTULO_CAMPO[k] ?? k}</dt>
              <dd className="font-semibold text-ink text-right">{valorCampo(k, v as string | number | boolean)}</dd>
            </div>
          ))}
        </dl>
        <h4 className="font-bold text-ink mt-3 text-[14px]">Beneficiários</h4>
        {c.proposta?.beneficiarios_legais ? (
          <p className="text-[14px] text-body">Deixou para os beneficiários legais.</p>
        ) : (
          <ul className="text-[14px] mt-1">
            {(c.proposta?.beneficiarios ?? []).map((b) => (
              <li key={b.nome} className="flex justify-between gap-3 py-1"><span>{b.nome} · {b.parentesco}</span><b>{b.percentual}%</b></li>
            ))}
          </ul>
        )}
      </div>

      {apontando ? (
        <div className="space-y-3">
          <label htmlFor="conf-nota" className="font-bold text-ink block">O que está errado?</label>
          <textarea id="conf-nota" className="field" rows={3} maxLength={1000} value={nota} onChange={(e) => setNota(e.target.value)} placeholder="Ex.: esqueci de informar um medicamento" autoFocus />
          <div className="flex gap-2">
            <button type="button" className="btn btn-primary flex-1" disabled={enviando || !nota.trim()} onClick={() => responder("corrigir")}>Enviar correção</button>
            <button type="button" className="btn btn-soft" onClick={() => setApontando(false)}>Voltar</button>
          </div>
        </div>
      ) : (
        <div className="flex flex-wrap gap-2">
          <button type="button" className="btn btn-primary" disabled={enviando} onClick={() => responder("confirmar")}>Está tudo certo</button>
          <button type="button" className="btn btn-soft" onClick={() => setApontando(true)}>Algo está errado</button>
        </div>
      )}
      {erro && <Aviso tom="erro">{erro}</Aviso>}
    </section>
  );
}
