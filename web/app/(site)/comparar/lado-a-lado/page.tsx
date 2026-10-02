"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { ArrowLeft, ArrowRight } from "lucide-react";
import { Selos, SemComparacao } from "@/components/opcao";
import { Barra, Carregando, Etapas, NEC, NomeSeguradora, ORDEM_NEC } from "@/components/ui";
import { humanizar, nomeCobertura } from "@/lib/coberturas";
import { brl, capitalCurto, pct } from "@/lib/format";
import { useFluxo } from "@/lib/fluxo";
import { RECURSOS } from "@/lib/recursos";

export default function LadoALado() {
  const router = useRouter();
  const { fluxo, pronto, atualizar } = useFluxo();
  const c = fluxo.comparacao;
  if (!pronto) return <Carregando />;
  if (!c) return <SemComparacao />;

  const escolhidas = c.opcoes.filter((o) => (fluxo.selecionadas ?? []).includes(o.produto_versao_id));
  if (escolhidas.length < 2)
    return (
      <div className="mx-auto max-w-[640px] px-5 py-20 text-center space-y-5">
        <h1 className="titulo text-4xl">Escolha <em>pelo menos 2 opções</em></h1>
        <Link href="/comparar" className="btn btn-primary">Voltar às opções</Link>
      </div>
    );

  const escolher = (id: string) => {
    atualizar({ escolhida: id });
    router.push("/contratar");
  };
  const grade = { gridTemplateColumns: `170px repeat(${escolhidas.length}, minmax(220px, 1fr))` };

  return (
    <>
      <div className="mx-auto max-w-[1180px] px-5 py-8">
        <div className="flex flex-wrap items-center gap-6 mb-8">
          <Link href="/comparar" className="flex items-center gap-2 font-semibold text-action">
            <ArrowLeft size={18} aria-hidden /> Voltar
          </Link>
          <Etapas atual={3} />
        </div>
        <h1 className="titulo text-[clamp(2.2rem,4.5vw,3.4rem)]">
          Compare lado a lado <em>as melhores opções.</em>
        </h1>

        <div className="mt-8 card overflow-x-auto">
          <div className="grid min-w-max sm:min-w-0" style={grade} role="table" aria-label="Comparação das opções">
            {/* cabeçalho */}
            <div role="row" className="contents">
              <div role="columnheader" className="p-5" />
              {escolhidas.map((o) => (
                <div role="columnheader" key={o.produto_versao_id} className="p-5 border-l border-line">
                  {RECURSOS.destaques && <div className="min-h-[30px] mb-2"><Selos id={o.produto_versao_id} destaques={c.destaques} /></div>}
                  <div><NomeSeguradora nome={o.produto.seguradora} /></div>
                  <div className="text-[13px] text-muted">{o.produto.nome}</div>
                  <div className="mt-3 text-4xl font-extrabold text-ink tracking-tight">
                    R$ {Math.round(o.premio_mensal).toLocaleString("pt-BR")}<span className="text-base font-semibold text-muted">/mês</span>
                  </div>
                  {RECURSOS.aderencia && (
                    <>
                      <div className="mt-1 text-[15px]"><b className="text-teal">{pct(o.aderencia_total)}</b> de aderência</div>
                      <div className="mt-2"><Barra valor={o.aderencia_total} /></div>
                    </>
                  )}
                </div>
              ))}
            </div>

            {ORDEM_NEC.filter((cod) => escolhidas.some((o) => o.itens.some((i) => i.necessidade === cod))).map((cod) => {
              const meta = NEC[cod];
              return (
                <div role="row" key={cod} className="contents">
                  <div role="rowheader" className="p-4 border-t border-line flex items-center gap-2 font-semibold text-ink">
                    <meta.Icon size={18} className={meta.texto} aria-hidden /> {meta.rotulo}
                  </div>
                  {escolhidas.map((o) => {
                    const i = o.itens.find((x) => x.necessidade === cod);
                    const ok = i && i.cobertura && i.capital_contratado > 0;
                    return (
                      <div role="cell" key={o.produto_versao_id} className="p-4 border-t border-l border-line">
                        {ok ? (
                          <>
                            <div className="font-extrabold text-ink text-lg">{capitalCurto(i.capital_contratado, cod === "NEC_RENDA")}</div>
                            <div className="text-[13px] text-body">{nomeCobertura(i.cobertura)}</div>
                            {RECURSOS.aderencia && <div className="text-[12px] text-muted">Aderência: {pct(i.aderencia)}</div>}
                            {i.observacoes.length > 0 && (
                              <ul className="mt-2 text-[13px] text-body space-y-1 list-disc pl-4">
                                {i.observacoes.map((t) => <li key={t}>{humanizar(t)}</li>)}
                              </ul>
                            )}
                          </>
                        ) : (
                          <>
                            <span className="text-muted">{i && i.cobertura ? "não incluída" : "não oferece"}</span>
                            {i && i.observacoes.length > 0 && (
                              <ul className="mt-2 text-[13px] text-body space-y-1 list-disc pl-4">
                                {i.observacoes.map((t) => <li key={t}>{humanizar(t)}</li>)}
                              </ul>
                            )}
                          </>
                        )}
                      </div>
                    );
                  })}
                </div>
              );
            })}

            {escolhidas.some((o) => o.projecao_premio) && (
              <div role="row" className="contents">
                <div role="rowheader" className="p-4 border-t border-line font-semibold text-ink">Prêmio no futuro</div>
                {escolhidas.map((o) => (
                  <div role="cell" key={o.produto_versao_id} className="p-4 border-t border-l border-line text-[14px]">
                    {o.projecao_premio ? (
                      <ul className="space-y-0.5">
                        <li>Em 10 anos: <b className="text-ink">{brl(o.projecao_premio.ano_10)}/mês</b></li>
                        <li>Em 20 anos: <b className="text-ink">{brl(o.projecao_premio.ano_20)}/mês</b></li>
                        <li>Em 30 anos: <b className="text-ink">{brl(o.projecao_premio.ano_30)}/mês</b></li>
                      </ul>
                    ) : (
                      <span className="text-body">Prêmio fixo ao longo do contrato</span>
                    )}
                  </div>
                ))}
              </div>
            )}

            <div role="row" className="contents">
              <div className="p-4 border-t border-line" />
              {escolhidas.map((o) => (
                <div role="cell" key={o.produto_versao_id} className="p-4 border-t border-l border-line">
                  <button type="button" className="btn btn-primary w-full" onClick={() => escolher(o.produto_versao_id)}>
                    Escolher esta opção <ArrowRight size={16} aria-hidden />
                  </button>
                </div>
              ))}
            </div>
          </div>
        </div>
        <p className="mt-4 text-[13px] text-muted">Valores sujeitos à análise e às regras das seguradoras. Projeções usam a tabela de hoje e capital constante.</p>
      </div>
    </>
  );
}
