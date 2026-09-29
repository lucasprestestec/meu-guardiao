"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useMemo, useRef, useState } from "react";
import { ArrowLeft, ArrowRight } from "lucide-react";
import { Opcoes, Texto } from "@/components/campos";
import { Anel, Aviso, Carregando, Etapas, IconeNec, NEC, ORDEM_NEC } from "@/components/ui";
import { api, ErroApi, type Comparacao, type Mapa } from "@/lib/api";
import { brl, capitalCurto } from "@/lib/format";
import { gravarFluxo, lerFluxo, type Perfil } from "@/lib/fluxo";

// Limites dos sliders (mockup de personalização).
const FAIXAS: Record<string, { min: number; max: number; passo: number; padrao: number }> = {
  NEC_MORTE: { min: 100_000, max: 5_000_000, passo: 50_000, padrao: 1_000_000 },
  NEC_INVALIDEZ: { min: 100_000, max: 5_000_000, passo: 50_000, padrao: 1_000_000 },
  NEC_DOENCA_GRAVE: { min: 50_000, max: 2_000_000, passo: 25_000, padrao: 300_000 },
  NEC_RENDA: { min: 100, max: 1_500, passo: 50, padrao: 300 },
};

const limitar = (v: number, cod: string) => {
  const f = FAIXAS[cod];
  return Math.min(f.max, Math.max(f.min, Math.ceil(v / f.passo) * f.passo)) // arredonda para cima: nunca abaixo da necessidade;
};

export function Personalizar({ necessidadeId }: { necessidadeId?: string }) {
  const router = useRouter();
  const [mapa, setMapa] = useState<Mapa | null>(null);
  const [pronto, setPronto] = useState(false);
  const [erro, setErro] = useState<string | null>(null);
  const [perfil, setPerfil] = useState<{ idade: string; sexo?: "M" | "F"; fumante?: boolean }>({ idade: "" });
  const [valores, setValores] = useState<Record<string, number>>({});
  const [ativos, setAtivos] = useState<Record<string, boolean>>({});
  const [sim, setSim] = useState<Comparacao | null>(null);
  const [simulando, setSimulando] = useState(false);
  const [enviando, setEnviando] = useState(false);
  const seq = useRef(0);

  // Carrega diagnóstico (jornada A) e perfil salvo; define valores iniciais.
  useEffect(() => {
    const f = lerFluxo();
    if (f.perfil) setPerfil({ idade: String(f.perfil.idade), sexo: f.perfil.sexo, fumante: f.perfil.fumante });
    // Valores guardados só valem para a mesma jornada: os de um diagnóstico não vazam para "Montar".
    const salvos = necessidadeId || !f.necessidadeId ? f.capitais : undefined;
    const inicial = (m: Mapa | null) => {
      const v: Record<string, number> = {};
      const a: Record<string, boolean> = {};
      for (const cod of ORDEM_NEC) {
        const n = m?.necessidades.find((x) => x.codigo === cod);
        const salvo = salvos?.[cod];
        const base = salvo ?? (n ? (n.gap > 0 ? n.gap : n.valor_necessario) : FAIXAS[cod].padrao);
        v[cod] = limitar(base, cod);
        a[cod] = salvo === undefined ? true : salvo > 0;
      }
      setValores(v);
      setAtivos(a);
      setPronto(true);
    };
    if (!necessidadeId) return inicial(null);
    api<Mapa>(`/v1/necessidades/${necessidadeId}`)
      .then((m) => {
        setMapa(m);
        inicial(m);
      })
      .catch((e) => setErro(e instanceof ErroApi && e.status === 404 ? "Não encontramos este diagnóstico." : (e as Error).message));
  }, [necessidadeId]);

  const idadeNum = Number(perfil.idade);
  const perfilOk = idadeNum >= 18 && idadeNum <= 80 && !!perfil.sexo && perfil.fumante !== undefined;
  const escolhidos = useMemo(() => {
    const c: Record<string, number> = {};
    for (const cod of ORDEM_NEC) c[cod] = ativos[cod] ? valores[cod] ?? 0 : 0;
    return c;
  }, [valores, ativos]);
  const algum = Object.values(escolhidos).some((v) => v > 0);

  // Simulação ao vivo: recalcula (sem gravar) ~0,4 s depois do último ajuste.
  useEffect(() => {
    if (!pronto || !perfilOk || !algum) {
      setSim(null);
      return;
    }
    const minha = ++seq.current;
    const ctl = new AbortController();
    setSimulando(true);
    const t = setTimeout(() => {
      api<Comparacao>("/v1/comparar", {
        corpo: corpo(false),
        signal: ctl.signal,
      })
        .then((r) => {
          if (minha === seq.current) {
            setSim(r);
            setErro(null);
          }
        })
        .catch((e) => {
          if ((e as Error).name !== "AbortError" && minha === seq.current) setErro((e as Error).message);
        })
        .finally(() => minha === seq.current && setSimulando(false));
    }, 400);
    return () => {
      clearTimeout(t);
      ctl.abort();
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [pronto, perfilOk, algum, escolhidos, perfil.sexo, perfil.fumante, perfil.idade]);

  function corpo(persistir: boolean) {
    return {
      necessidade_id: necessidadeId ?? null,
      idade: idadeNum,
      sexo: perfil.sexo,
      fumante: perfil.fumante,
      capitais_escolhidos: escolhidos,
      persistir,
    };
  }

  async function comparar() {
    setEnviando(true);
    setErro(null);
    try {
      const r = await api<Comparacao>("/v1/comparar", { corpo: corpo(true) });
      const p: Perfil = { idade: idadeNum, sexo: perfil.sexo!, fumante: perfil.fumante! };
      gravarFluxo({
        perfil: p, necessidadeId, capitais: escolhidos, comparacao: r, escolhida: undefined, selecionadas: [],
      });
      router.push("/comparar");
    } catch (e) {
      setErro((e as Error).message);
      setEnviando(false);
    }
  }

  if (erro && !pronto) return <div className="mx-auto max-w-[720px] px-5 py-16 space-y-5"><Aviso tom="erro">{erro}</Aviso><Link href="/diagnostico" className="btn btn-primary w-fit">Fazer diagnóstico</Link></div>;
  if (!pronto) return <Carregando />;

  const recomendada = sim?.opcoes.find((o) => o.produto_versao_id === sim.destaques.recomendado) ?? null;
  const modoDireto = !necessidadeId;

  return (
    <>
      <div className="mx-auto max-w-[1180px] px-5 py-8">
        <div className="flex flex-wrap items-center gap-6 mb-8">
          <Link href={necessidadeId ? `/mapa/${necessidadeId}` : "/"} className="flex items-center gap-2 font-semibold text-action">
            <ArrowLeft size={18} aria-hidden /> Voltar
          </Link>
          <Etapas atual={2} />
        </div>

        <div className="grid lg:grid-cols-[1fr_380px] gap-8 items-start">
          <div>
            <h1 className="titulo text-[clamp(2.4rem,5vw,3.8rem)]">
              {modoDireto ? <>Monte <em>sua proteção.</em></> : <>Personalize <em>sua proteção.</em></>}
            </h1>
            <p className="text-lg text-body mt-3">
              {modoDireto
                ? "Escolha quanto quer proteger em cada cobertura. Sem diagnóstico, comparamos exatamente o que você escolher."
                : "Começamos pelo valor que calculamos para você. Ajuste como quiser antes de comparar."}
            </p>

            {modoDireto || !perfil.idade || !perfil.sexo ? (
              <section className="card p-5 mt-6" aria-label="Seu perfil">
                <h2 className="font-extrabold text-ink mb-3">Sobre você <span className="text-muted font-medium text-sm">(o preço depende disso)</span></h2>
                <div className="grid sm:grid-cols-[120px_1fr_1fr] gap-4 items-end">
                  <Texto rotulo="Idade" valor={perfil.idade} inputMode="numeric" maxLength={2} placeholder="Ex.: 38" onChange={(v) => setPerfil((p) => ({ ...p, idade: v.replace(/\D/g, "") }))} />
                  <Opcoes compacto rotulo="Sexo" valor={perfil.sexo} onChange={(v) => setPerfil((p) => ({ ...p, sexo: v }))} opcoes={[{ valor: "F" as const, texto: "Feminino" }, { valor: "M" as const, texto: "Masculino" }]} />
                  <Opcoes compacto rotulo="Fuma?" valor={perfil.fumante} onChange={(v) => setPerfil((p) => ({ ...p, fumante: v }))} opcoes={[{ valor: false, texto: "Não" }, { valor: true, texto: "Sim" }]} />
                </div>
              </section>
            ) : null}

            <section className="card mt-6 divide-y divide-line" aria-label="Coberturas">
              {ORDEM_NEC.map((cod) => {
                const f = FAIXAS[cod];
                const meta = NEC[cod];
                const diaria = cod === "NEC_RENDA";
                const ativo = ativos[cod];
                const v = valores[cod];
                const calc = mapa?.necessidades.find((n) => n.codigo === cod);
                const pctSlider = ((v - f.min) / (f.max - f.min)) * 100;
                return (
                  <div key={cod} className="p-5 sm:p-6 grid sm:grid-cols-[230px_1fr] gap-4 sm:gap-8 items-center">
                    <div className="flex items-center gap-3">
                      <IconeNec codigo={cod} size={52} />
                      <div>
                        <h2 className="font-extrabold text-ink text-lg leading-tight">{meta.rotulo}</h2>
                        <p className="text-[13px] text-body leading-snug">{meta.descricao.replace(/\.$/, "")}</p>
                      </div>
                    </div>
                    <div className={ativo ? "" : "opacity-45"}>
                      <div className="flex justify-between items-baseline mb-2">
                        <label htmlFor={`s-${cod}`} className="sr-only">{meta.rotulo}</label>
                        <span className="font-extrabold text-xl" style={{ color: meta.cor }}>
                          {ativo ? capitalCurto(v, diaria).replace("R$ ", "R$ ") : "Não incluir"}
                        </span>
                        <label className="text-[13px] text-muted flex items-center gap-2 cursor-pointer">
                          <input type="checkbox" checked={ativo} onChange={(e) => setAtivos((a) => ({ ...a, [cod]: e.target.checked }))} className="accent-[var(--action)] w-4 h-4" />
                          Incluir
                        </label>
                      </div>
                      <input
                        id={`s-${cod}`}
                        type="range"
                        className="slider"
                        min={f.min}
                        max={f.max}
                        step={f.passo}
                        value={v}
                        disabled={!ativo}
                        style={{ ["--cor" as string]: meta.cor, ["--pct" as string]: `${pctSlider}%` }}
                        onChange={(e) => setValores((x) => ({ ...x, [cod]: Number(e.target.value) }))}
                        aria-valuetext={capitalCurto(v, diaria)}
                      />
                      <div className="flex justify-between text-[12px] text-muted mt-1.5">
                        <span>{capitalCurto(f.min, diaria)}</span>
                        {calc && (
                          <button
                            type="button"
                            className="font-semibold text-action hover:underline"
                            onClick={() => { setValores((x) => ({ ...x, [cod]: limitar(calc.gap > 0 ? calc.gap : calc.valor_necessario, cod) })); setAtivos((a) => ({ ...a, [cod]: true })); }}
                          >
                            Sugerido: {diaria ? `${brl(calc.gap || calc.valor_necessario)}/dia` : brl(calc.gap || calc.valor_necessario)}
                          </button>
                        )}
                        <span>{capitalCurto(f.max, diaria)}</span>
                      </div>
                    </div>
                  </div>
                );
              })}
            </section>
          </div>

          <aside className="rounded-3xl bg-teal-tint p-6 lg:sticky lg:top-6" aria-label="Resumo" aria-live="polite">
            <h2 className="font-extrabold text-ink text-lg">
              {modoDireto ? "Qualidade das coberturas" : "Aderência à necessidade"}
            </h2>
            {!perfilOk ? (
              <p className="text-body mt-4">Informe sua idade, sexo e se fuma para ver a estimativa.</p>
            ) : !algum ? (
              <p className="text-body mt-4">Inclua ao menos uma cobertura.</p>
            ) : !recomendada ? (
              <div className="mt-4">
                {simulando ? <p className="text-muted">Calculando…</p> : <Aviso tom="alerta">{sim?.alertas_gerais.at(-1) ?? "Nenhuma opção disponível para este perfil."}</Aviso>}
              </div>
            ) : (
              <div className={simulando ? "opacity-60 transition-opacity" : "transition-opacity"}>
                <div className="flex items-center gap-5 mt-4">
                  <Anel valor={recomendada.aderencia_total} tamanho={110} espessura={11} rotulo={`${Math.round(recomendada.aderencia_total * 100)}%`} />
                  <p className="text-[14px] text-body">
                    {modoDireto
                      ? "O quanto a melhor opção entrega do que você escolheu, considerando as regras de cada seguro."
                      : "O quanto a melhor opção cobre da sua necessidade calculada."}
                  </p>
                </div>
                <div className="border-t border-[#c7e6df] mt-5 pt-5">
                  <div className="text-[13px] font-semibold text-muted">Opção recomendada</div>
                  <div className="flex items-baseline gap-1">
                    <span className="text-muted">R$</span>
                    <span className="text-5xl font-extrabold text-action tracking-tight">{Math.round(recomendada.premio_mensal).toLocaleString("pt-BR")}</span>
                    <span className="text-lg font-semibold text-muted">/mês</span>
                  </div>
                  <p className="text-[13px] text-muted mt-1">Os valores finais dependem da análise da seguradora.</p>
                </div>
              </div>
            )}
            {erro && <div className="mt-4"><Aviso tom="erro">{erro}</Aviso></div>}
            <button type="button" onClick={comparar} disabled={!recomendada || enviando || simulando} className="btn btn-primary w-full mt-6">
              {enviando ? "Comparando…" : "Comparar opções"} {!enviando && <ArrowRight size={18} aria-hidden />}
            </button>
            {necessidadeId && (
              <Link href={`/mapa/${necessidadeId}`} className="btn btn-secondary w-full mt-3">Voltar ao diagnóstico</Link>
            )}
          </aside>
        </div>
      </div>

      {/* Celular: o resumo fica no fim da página, então o preço e o botão acompanham a rolagem. */}
      <div className="lg:hidden fixed bottom-0 inset-x-0 z-10 bg-white border-t border-line px-4 py-3 flex items-center gap-3">
        <div className="flex-1 min-w-0">
          {recomendada ? (
            <>
              <div className="font-extrabold text-ink text-xl leading-none">
                R$ {Math.round(recomendada.premio_mensal).toLocaleString("pt-BR")}<span className="text-sm text-muted font-semibold">/mês</span>
              </div>
              <div className="text-[12px] text-teal font-bold">{Math.round(recomendada.aderencia_total * 100)}% de aderência</div>
            </>
          ) : (
            <div className="text-[13px] text-muted">{simulando ? "Calculando…" : "Preencha seu perfil"}</div>
          )}
        </div>
        <button type="button" onClick={comparar} disabled={!recomendada || enviando || simulando} className="btn btn-primary !py-3 !px-5 whitespace-nowrap">
          {enviando ? "Comparando…" : "Comparar"} <ArrowRight size={16} aria-hidden />
        </button>
      </div>
      <div className="lg:hidden h-20" aria-hidden />
    </>
  );
}
