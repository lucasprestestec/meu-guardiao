"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useMemo, useState } from "react";
import { ArrowLeft, ArrowRight, CircleDollarSign, ShieldCheck, Star } from "lucide-react";
import { Selos, SemComparacao } from "@/components/opcao";
import { Barra, Carregando, Etapas, ListaCoberturas, NomeSeguradora } from "@/components/ui";
import type { Opcao } from "@/lib/api";
import { pct } from "@/lib/format";
import { useFluxo } from "@/lib/fluxo";

type Aba = "recomendadas" | "preco" | "protecao";
const ABAS: { id: Aba; texto: string; Icon: typeof Star }[] = [
  { id: "recomendadas", texto: "Recomendadas", Icon: Star },
  { id: "preco", texto: "Menor preço", Icon: CircleDollarSign },
  { id: "protecao", texto: "Maior proteção", Icon: ShieldCheck },
];

export default function Comparar() {
  const router = useRouter();
  const { fluxo, pronto, atualizar } = useFluxo();
  const [aba, setAba] = useState<Aba>("recomendadas");
  const c = fluxo.comparacao;
  const sel = fluxo.selecionadas ?? [];

  const ordenadas = useMemo<Opcao[]>(() => {
    const o = [...(c?.opcoes ?? [])];
    if (aba === "preco") return o.sort((a, b) => a.premio_mensal - b.premio_mensal);
    // "recomendadas" e "maior proteção" ordenam por aderência; o preço desempata.
    return o.sort((a, b) => b.aderencia_total - a.aderencia_total || a.premio_mensal - b.premio_mensal);
  }, [c, aba]);

  if (!pronto) return <Carregando />;
  if (!c) return <SemComparacao />;

  const alternar = (id: string) =>
    atualizar({ selecionadas: sel.includes(id) ? sel.filter((x) => x !== id) : [...sel, id].slice(-3) });
  const escolher = (id: string) => {
    atualizar({ escolhida: id });
    router.push("/contratar");
  };

  return (
    <>
      <div className="mx-auto max-w-[1180px] px-5 py-8">
        <div className="flex flex-wrap items-center gap-6 mb-8">
          <Link href={fluxo.necessidadeId ? `/personalizar?n=${fluxo.necessidadeId}` : "/montar"} className="flex items-center gap-2 font-semibold text-action">
            <ArrowLeft size={18} aria-hidden /> Voltar
          </Link>
          <Etapas atual={3} />
        </div>

        <h1 className="titulo text-[clamp(2.2rem,4.5vw,3.5rem)]">
          {c.opcoes.length === 0 ? <>Nenhuma opção <em>para este perfil.</em></> : <>Encontramos {c.opcoes.length} {c.opcoes.length === 1 ? "opção" : "opções"} <em>para você.</em></>}
        </h1>
        <p className="text-lg text-body mt-3">Ordenadas pela aderência ao que você precisa, não só pelo preço.</p>

        {c.alertas_gerais.filter((a) => !a.startsWith("Nenhum")).map((a) => (
          <p key={a} className="mt-4 rounded-2xl bg-blue-tint px-4 py-3 text-[14px] text-ink">{a}</p>
        ))}

        {c.opcoes.length > 0 && (
          <>
            <div role="tablist" aria-label="Ordenar opções" className="mt-6 flex sm:inline-flex rounded-2xl bg-white border border-line p-1.5 gap-1">
              {ABAS.map(({ id, texto, Icon }) => (
                <button
                  key={id}
                  role="tab"
                  aria-selected={aba === id}
                  onClick={() => setAba(id)}
                  className={`flex-1 sm:flex-none flex items-center justify-center gap-2 rounded-xl px-2 sm:px-4 py-2.5 text-[13px] sm:text-base font-semibold ${aba === id ? "bg-blue-tint text-action" : "text-body hover:text-ink"}`}
                >
                  <Icon size={17} className="hidden sm:block" aria-hidden /> {texto}
                </button>
              ))}
            </div>

            <div className="mt-6 grid md:grid-cols-2 lg:grid-cols-3 gap-5">
              {ordenadas.map((o) => (
                <article key={o.produto_versao_id} className="card p-6 flex flex-col">
                  <div className="min-h-[30px]"><Selos id={o.produto_versao_id} destaques={c.destaques} /></div>
                  <div className="mt-3"><NomeSeguradora nome={o.produto.seguradora} /></div>
                  <div className="text-[13px] text-muted">{o.produto.nome}</div>
                  <div className="mt-4 flex items-baseline gap-1">
                    <span className="text-muted">R$</span>
                    <span className="text-5xl font-extrabold text-ink tracking-tight">{Math.round(o.premio_mensal).toLocaleString("pt-BR")}</span>
                    <span className="text-lg font-semibold text-muted">/mês</span>
                  </div>
                  <div className="mt-2 text-[15px]"><b className="text-teal">{pct(o.aderencia_total)}</b> de aderência</div>
                  <div className="mt-2 mb-4"><Barra valor={o.aderencia_total} /></div>
                  <div className="flex-1"><ListaCoberturas itens={o.itens} /></div>
                  {o.projecao_premio && (
                    <p className="text-[13px] text-amber bg-amber-tint rounded-xl px-3 py-2 mt-3">
                      O prêmio sobe com a idade. Em 20 anos: R$ {Math.round(o.projecao_premio.ano_20).toLocaleString("pt-BR")}/mês.
                    </p>
                  )}
                  <div className="mt-5 grid grid-cols-[1fr_auto] gap-3 items-center">
                    <button type="button" className="btn btn-primary" onClick={() => escolher(o.produto_versao_id)}>
                      Escolher <ArrowRight size={16} aria-hidden />
                    </button>
                    <Link href={`/opcao/${o.produto_versao_id}`} className="font-semibold text-action hover:underline px-1">Detalhes</Link>
                  </div>
                  <label className="mt-4 flex items-center gap-2 text-[14px] text-body cursor-pointer w-fit">
                    <input type="checkbox" className="w-4 h-4 accent-[var(--action)]" checked={sel.includes(o.produto_versao_id)} onChange={() => alternar(o.produto_versao_id)} />
                    Comparar lado a lado
                  </label>
                </article>
              ))}
            </div>

            <div className="mt-6 card px-6 py-4 flex flex-wrap items-center justify-between gap-4">
              <p className="text-body">
                <b className="text-ink">{sel.length}</b> {sel.length === 1 ? "opção selecionada" : "opções selecionadas"}
                <span className="text-muted"> · {sel.length < 2 ? "marque pelo menos 2 para comparar" : "máximo de 3"}</span>
              </p>
              <Link
                href="/comparar/lado-a-lado"
                aria-disabled={sel.length < 2}
                className={`btn ${sel.length < 2 ? "bg-[#e3e8f0] text-muted pointer-events-none" : "btn-primary"}`}
              >
                Comparar selecionadas <ArrowRight size={16} aria-hidden />
              </Link>
            </div>
          </>
        )}

        {c.excluidos.length > 0 && (
          <details className="mt-6 text-[14px] text-body">
            <summary className="cursor-pointer font-semibold text-ink">
              {c.excluidos.length} {c.excluidos.length === 1 ? "produto não é exibido" : "produtos não são exibidos"} para este perfil
            </summary>
            <ul className="mt-2 space-y-1 pl-4 list-disc">
              {c.excluidos.map((e) => (
                <li key={e.produto}><b>{e.produto}</b>: {e.motivo}</li>
              ))}
            </ul>
          </details>
        )}
        <p className="mt-6 text-[13px] text-muted">Valores sujeitos à análise e às regras das seguradoras.</p>
      </div>
    </>
  );
}
