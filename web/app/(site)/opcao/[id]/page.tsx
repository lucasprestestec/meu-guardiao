"use client";

import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import { ArrowLeft, ArrowRight, Check, TriangleAlert } from "lucide-react";
import { Selos, SemComparacao } from "@/components/opcao";
import { Barra, Carregando, Etapas, IconeNec, ListaCoberturas, NEC, NomeSeguradora, ORDEM_NEC } from "@/components/ui";
import { nomeCobertura, humanizar } from "@/lib/coberturas";
import { brl, capitalCurto, pct } from "@/lib/format";
import { useFluxo } from "@/lib/fluxo";

export default function Detalhes() {
  const { id } = useParams<{ id: string }>();
  const router = useRouter();
  const { fluxo, pronto, atualizar } = useFluxo();
  const c = fluxo.comparacao;
  if (!pronto) return <Carregando />;
  if (!c) return <SemComparacao />;
  const o = c.opcoes.find((x) => x.produto_versao_id === id);
  if (!o)
    return (
      <div className="mx-auto max-w-[640px] px-5 py-20 text-center space-y-5">
        <h1 className="titulo text-4xl">Opção <em>não encontrada</em></h1>
        <Link href="/comparar" className="btn btn-primary">Voltar às opções</Link>
      </div>
    );

  const recomendada = c.destaques.recomendado === id;
  const menorPreco = c.destaques.menor_preco === id;
  const pedidas = o.itens.length;
  const oferecidas = o.itens.filter((i) => i.cobertura && i.capital_contratado > 0).length;
  const motivos = [
    `Cobre ${pct(o.aderencia_total)} do que você precisa, considerando as regras de cada cobertura.`,
    oferecidas === pedidas
      ? `Oferece as ${pedidas} coberturas da sua proteção.`
      : `Oferece ${oferecidas} das ${pedidas} coberturas da sua proteção.`,
    ...(menorPreco ? ["É a opção de menor preço mensal entre as encontradas."] : []),
  ];
  // Regras que mudam o valor ou a proteção, agrupadas por cobertura para o leitor saber de qual se trata.
  const atencao = o.itens.flatMap((i) =>
    i.observacoes.map((t) => ({ nec: NEC[i.necessidade]?.rotulo ?? "", texto: humanizar(t) })),
  );

  return (
    <>
      <div className="mx-auto max-w-[1180px] px-5 py-8">
        <div className="flex flex-wrap items-center gap-6 mb-8">
          <Link href="/comparar" className="flex items-center gap-2 font-semibold text-action">
            <ArrowLeft size={18} aria-hidden /> Voltar
          </Link>
          <Etapas atual={3} />
        </div>

        <div className="grid lg:grid-cols-[1fr_380px] gap-8 items-start">
          <div className="space-y-6">
            <h1 className="titulo text-[clamp(2.2rem,4.5vw,3.4rem)]">
              Detalhes da opção {recomendada ? <em>recomendada.</em> : <em>escolhida.</em>}
            </h1>

            <section className="card p-6 grid sm:grid-cols-[1fr_1.2fr] gap-6 items-center">
              <div>
                <Selos id={id} destaques={c.destaques} />
                <div className="mt-3"><NomeSeguradora nome={o.produto.seguradora} grande /></div>
                <div className="text-body">{o.produto.nome}</div>
              </div>
              <div>
                <div className="text-[13px] text-muted font-semibold">Valor da proteção</div>
                <div className="text-5xl font-extrabold text-ink tracking-tight">
                  R$ {Math.round(o.premio_mensal).toLocaleString("pt-BR")}<span className="text-lg text-muted font-semibold">/mês</span>
                </div>
                <div className="mt-1"><b className="text-teal">{pct(o.aderencia_total)}</b> de aderência</div>
                <div className="mt-2"><Barra valor={o.aderencia_total} /></div>
              </div>
            </section>

            <section className="grid sm:grid-cols-2 gap-4" aria-label="Coberturas">
              {ORDEM_NEC.filter((cod) => o.itens.some((i) => i.necessidade === cod)).map((cod) => {
                const i = o.itens.find((x) => x.necessidade === cod)!;
                const ok = i.cobertura && i.capital_contratado > 0;
                return (
                  <div key={cod} className="card p-5 flex gap-4">
                    <IconeNec codigo={cod} />
                    <div className="flex-1">
                      <div className="font-bold text-ink">{NEC[cod].rotulo}</div>
                      {ok ? (
                        <>
                          <div className="text-2xl font-extrabold text-ink">{capitalCurto(i.capital_contratado, cod === "NEC_RENDA")}</div>
                          <div className="text-[13px] text-body">{nomeCobertura(i.cobertura)}</div>
                          <div className="text-[12px] text-muted">Aderência desta cobertura: {pct(i.aderencia)}</div>
                        </>
                      ) : (
                        <div className="text-muted mt-1">Este produto não oferece esta cobertura.</div>
                      )}
                    </div>
                  </div>
                );
              })}
            </section>

            <section>
              <h2 className="text-xl font-extrabold mb-3">Por que esta opção</h2>
              <ul className="grid gap-3">
                {motivos.map((m) => (
                  <li key={m} className="flex gap-3 items-start">
                    <span className="grid place-items-center w-7 h-7 rounded-full bg-teal-tint text-teal shrink-0"><Check size={16} strokeWidth={3} aria-hidden /></span>
                    <span className="text-ink">{m}</span>
                  </li>
                ))}
              </ul>
            </section>

            {atencao.length > 0 && (
              <section className="rounded-3xl bg-amber-tint p-6">
                <h2 className="text-xl font-extrabold mb-3 flex items-center gap-2"><TriangleAlert size={20} className="text-amber" aria-hidden /> O que você precisa saber</h2>
                <ul className="space-y-2 list-disc pl-5 text-[#6b470d]">
                  {atencao.map((a) => <li key={a.nec + a.texto}><b>{a.nec}:</b> {a.texto}</li>)}
                </ul>
              </section>
            )}

            <section className="card p-6">
              <h2 className="text-xl font-extrabold mb-2">Como o preço evolui</h2>
              {o.projecao_premio ? (
                <>
                  <p className="text-body mb-4">O prêmio desta opção sobe conforme você envelhece. Estimativa do valor mensal:</p>
                  <div className="grid grid-cols-4 gap-3 text-center">
                    {[["Hoje", o.premio_mensal], ["Em 10 anos", o.projecao_premio.ano_10], ["Em 20 anos", o.projecao_premio.ano_20], ["Em 30 anos", o.projecao_premio.ano_30]].map(([t, v]) => (
                      <div key={t as string} className="rounded-2xl bg-canvas p-3">
                        <div className="text-[12px] text-muted font-semibold">{t}</div>
                        <div className="font-extrabold text-ink text-lg">{brl(v as number)}</div>
                      </div>
                    ))}
                  </div>
                  <p className="text-[13px] text-muted mt-3">{o.projecao_premio.premissa}</p>
                </>
              ) : (
                <p className="text-body">Prêmio nivelado: o valor mensal não sobe por causa da idade.</p>
              )}
            </section>
            {o.alertas.filter((a) => !a.startsWith("TARIFA FICT")).map((a) => (
              <p key={a} className="text-[14px] text-danger font-semibold">{a}</p>
            ))}
          </div>

          <aside className="rounded-3xl bg-teal-tint p-6 lg:sticky lg:top-6">
            <h2 className="text-xl font-extrabold">Resumo da escolha</h2>
            <div className="mt-2"><ListaCoberturas itens={o.itens} notas={2} /></div>
            <div className="flex items-baseline justify-between border-t border-[#c7e6df] mt-3 pt-4">
              <span className="font-bold text-ink">Valor mensal</span>
              <span className="text-3xl font-extrabold text-teal">R$ {Math.round(o.premio_mensal).toLocaleString("pt-BR")}<span className="text-base">/mês</span></span>
            </div>
            <button type="button" className="btn btn-primary w-full mt-5" onClick={() => { atualizar({ escolhida: id }); router.push("/contratar"); }}>
              Escolher esta opção <ArrowRight size={18} aria-hidden />
            </button>
            <Link href="/comparar" className="btn btn-secondary w-full mt-3">Comparar novamente</Link>
          </aside>
        </div>
      </div>
    </>
  );
}
