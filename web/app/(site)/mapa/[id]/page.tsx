"use client";

import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { ArrowRight, AlertCircle } from "lucide-react";
import { Anel, Aviso, Carregando, IconeNec, NEC, ORDEM_NEC } from "@/components/ui";
import { RECURSOS } from "@/lib/recursos";
import { lerFluxo } from "@/lib/fluxo";
import { api, ErroApi, type Mapa } from "@/lib/api";
import { brl, capitalCurto } from "@/lib/format";

function faixaScore(s: number) {
  if (s < 40) return { titulo: "Sua proteção está baixa", texto: "Há pontos importantes para reforçar. Vale agir agora." };
  if (s < 70) return { titulo: "Bom começo!", texto: "Você já tem uma base de proteção, mas ainda existem pontos importantes para fortalecer." };
  return { titulo: "Você está bem protegido", texto: "Sua proteção atual cobre boa parte do que sua família precisaria." };
}

export default function MapaPagina() {
  const { id } = useParams<{ id: string }>();
  const [mapa, setMapa] = useState<Mapa | null>(null);
  const [erro, setErro] = useState<string | null>(null);
  const router = useRouter();

  useEffect(() => {
    // O contato vem antes do Mapa. Quem chegou por link direto passa pela captura uma vez.
    if (RECURSOS.capturaDeContato && !lerFluxo().contato) router.replace(`/contato?n=${id}`);
  }, [id, router]);

  useEffect(() => {
    api<Mapa>(`/v1/necessidades/${id}`)
      .then(setMapa)
      .catch((e) => setErro(e instanceof ErroApi && e.status === 404 ? "Não encontramos este diagnóstico." : (e as Error).message));
  }, [id]);

  if (erro)
    return (
      <div className="mx-auto max-w-[720px] px-5 py-16 space-y-5">
        <Aviso tom="erro">{erro}</Aviso>
        <Link href="/diagnostico" className="btn btn-primary w-fit">Fazer um novo diagnóstico</Link>
      </div>
    );
  if (!mapa) return <Carregando texto="Carregando seu Mapa de Proteção…" />;

  const faixa = faixaScore(mapa.protection_score);
  const porCodigo = new Map(mapa.necessidades.map((n) => [n.codigo, n]));
  const vulner = mapa.vulnerabilidade_principal ? NEC[mapa.vulnerabilidade_principal]?.rotulo.toLowerCase() : null;

  return (
    <div className="mx-auto max-w-[1180px] px-5 py-10">
      <p className="text-[12px] font-bold tracking-[0.14em] uppercase text-action mb-3">Seu diagnóstico personalizado</p>
      <h1 className="titulo text-[clamp(2.6rem,5.5vw,4.2rem)]">
        Seu Mapa de <em>Proteção</em>
      </h1>
      <p className="text-lg text-body mt-3 max-w-[50ch]">Com base nas suas respostas, estimamos a proteção adequada para sua realidade.</p>

      <div className={`mt-8 grid gap-5 ${RECURSOS.protectionScore ? "lg:grid-cols-[340px_1fr]" : ""}`}>
        {/* Desligado por configuração (lib/recursos.ts): a regra será revista. */}
        {RECURSOS.protectionScore && (
        <section className="rounded-3xl bg-teal-tint p-7" aria-label="Protection Score">
          <h2 className="text-xl font-extrabold">Seu Protection Score</h2>
          <p className="text-body mt-1 text-[15px]">Indica o quanto você está protegido com base nas suas necessidades.</p>
          <div className="my-6 grid place-items-center">
            <Anel valor={mapa.protection_score / 100} tamanho={200} espessura={18} rotulo={String(mapa.protection_score)} sub="/ 100" />
          </div>
          <h3 className="text-2xl font-extrabold text-teal">{faixa.titulo}</h3>
          <p className="text-body mt-1">{faixa.texto}</p>
        </section>
        )}

        <div className="grid sm:grid-cols-2 gap-5 content-start">
          {ORDEM_NEC.filter((c) => porCodigo.has(c)).map((c) => {
            const n = porCodigo.get(c)!;
            const meta = NEC[c];
            const diaria = n.unidade === "DIARIA";
            return (
              <article key={c} className="card p-5 flex flex-col">
                <div className="flex items-start gap-3">
                  <IconeNec codigo={c} />
                  <div className="flex-1">
                    <h3 className="font-bold text-ink">{meta.rotulo}</h3>
                    <div className="text-[26px] font-extrabold text-ink leading-tight">
                      {diaria ? `${brl(n.valor_necessario)}/dia` : brl(n.valor_necessario)}
                    </div>
                  </div>
                </div>
                <p className="text-[14px] text-body mt-3 flex-1">{meta.descricao}</p>
                <dl className="mt-3 text-[14px] divide-y divide-line border-t border-line">
                  <div className="flex justify-between py-1.5">
                    <dt className="text-muted">O que você já tem</dt>
                    <dd className="font-bold text-ink">{n.valor_existente > 0 ? capitalCurto(n.valor_existente, diaria) : "Nada"}</dd>
                  </div>
                  <div className="flex justify-between py-1.5">
                    <dt className="text-muted">O que falta</dt>
                    <dd className={`font-bold ${n.gap > 0 ? meta.texto : "text-ink"}`}>{n.gap > 0 ? capitalCurto(n.gap, diaria) : "Nada"}</dd>
                  </div>
                </dl>
                <details className="mt-3 text-[14px] group">
                  <summary className="cursor-pointer font-semibold text-action list-none">Como chegamos a esse valor</summary>
                  <p className="mt-2 text-body leading-relaxed">{n.justificativa}</p>
                </details>
              </article>
            );
          })}
        </div>
      </div>

      {vulner && (
        <div className="mt-5 rounded-3xl bg-amber-tint p-6 flex gap-4 items-start">
          <AlertCircle className="text-amber shrink-0 mt-0.5" size={28} aria-hidden />
          <div>
            <h2 className="font-extrabold text-ink text-lg">Sua principal vulnerabilidade está em: {vulner}.</h2>
            <p className="text-body mt-1">É onde a distância entre o que você tem e o que a sua família precisaria é maior. Comece por aqui.</p>
          </div>
        </div>
      )}

      {mapa.alertas.length > 0 && (
        <div className="mt-4 space-y-3">
          {mapa.alertas.map((a) => (
            <Aviso key={a} tom="alerta">{a}</Aviso>
          ))}
        </div>
      )}

      <div className="mt-8 flex flex-wrap items-center gap-4">
        <Link href={`/personalizar?n=${mapa.necessidade_id}`} className="btn btn-primary text-lg !px-8 !py-4">
          Ajustar valores e comparar opções <ArrowRight size={20} aria-hidden />
        </Link>
        <span className="text-[13px] text-muted max-w-[46ch]">
          Estimativa educativa, calculada pelo Motor DOR$ v{mapa.versao_motor} a partir das suas respostas.
        </span>
      </div>
    </div>
  );
}
