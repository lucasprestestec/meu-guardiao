"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { ArrowLeft, ArrowRight, BarChart3, CreditCard, Lightbulb, Shield, User, Users } from "lucide-react";
import { Dinheiro, Opcoes, Selecao, Texto } from "@/components/campos";
import { Escudo } from "@/components/escudo";
import { Aviso } from "@/components/ui";
import { api, ErroApi, type Mapa } from "@/lib/api";
import { gravarFluxo } from "@/lib/fluxo";

type Respostas = {
  temDependentes?: boolean;
  qtdDependentes: number;
  idadesDependentes: string[];
  idade: string;
  sexo?: "M" | "F";
  fumante?: boolean;
  profissao: string;
  renda: number;
  custo: number;
  imobiliaria: number;
  prestamista?: boolean;
  empresarial: number;
  veiculos: number;
  outras: number;
  educacao: number;
  quitacaoImovel: number;
  outrosProjetos: number;
  patrimonioLiquido: number;
  patrimonioInventariavel: number;
  reserva: string;
  seguroMorte: number;
  seguroInvalidez: number;
  seguroDg: number;
  seguroDiaria: number;
};

const INICIAL: Respostas = {
  qtdDependentes: 1, idadesDependentes: [""], idade: "", profissao: "", renda: 0, custo: 0,
  imobiliaria: 0, empresarial: 0, veiculos: 0, outras: 0, educacao: 0, quitacaoImovel: 0,
  outrosProjetos: 0, patrimonioLiquido: 0, patrimonioInventariavel: 0, reserva: "",
  seguroMorte: 0, seguroInvalidez: 0, seguroDg: 0, seguroDiaria: 0,
};

const PROFISSOES: Record<string, string> = {
  "CLT (empregado)": "CLT",
  "Autônomo / profissional liberal": "AUTONOMO",
  "Empresário": "EMPRESARIO",
  "Depende das mãos ou de habilidade técnica (ex.: dentista, cirurgião, músico)": "MANUAL_ESPECIALIZADO",
  "Outra situação": "OUTRO",
};
const RESERVAS: Record<string, number> = {
  "Nenhuma": 0, "Até 1 mês": 1, "Cerca de 3 meses": 3, "Cerca de 6 meses": 6, "12 meses ou mais": 12,
};

const TOTAL = 6;
const CHAVE_RASCUNHO = "dor.diag";

export default function Diagnostico() {
  const router = useRouter();
  const [etapa, setEtapa] = useState(1);
  const [r, setR] = useState<Respostas>(INICIAL);
  const [enviando, setEnviando] = useState(false);
  const [erro, setErro] = useState<string | null>(null);
  const [tentou, setTentou] = useState(false);

  // Recupera o rascunho se a pessoa recarregar a página.
  useEffect(() => {
    try {
      const salvo = JSON.parse(sessionStorage.getItem(CHAVE_RASCUNHO) ?? "null");
      if (salvo) {
        setR({ ...INICIAL, ...salvo.r });
        setEtapa(salvo.etapa ?? 1);
      }
    } catch {
      /* sem rascunho */
    }
  }, []);
  useEffect(() => {
    try {
      sessionStorage.setItem(CHAVE_RASCUNHO, JSON.stringify({ r, etapa }));
    } catch {
      /* ignore */
    }
  }, [r, etapa]);

  const set = <K extends keyof Respostas>(k: K, v: Respostas[K]) => setR((x) => ({ ...x, [k]: v }));

  // /diagnostico?demo=1 mostra um atalho para apresentar o produto sem digitar tudo.
  const [demo, setDemo] = useState(false);
  useEffect(() => setDemo(new URLSearchParams(window.location.search).has("demo")), []);
  function preencherExemplo() {
    setR({
      ...INICIAL, temDependentes: true, qtdDependentes: 1, idadesDependentes: ["5"], idade: "34", sexo: "M",
      fumante: false, profissao: "CLT (empregado)", renda: 15000, custo: 10000, imobiliaria: 300000,
      prestamista: true, reserva: "Cerca de 3 meses", seguroMorte: 1_350_000, seguroInvalidez: 1_500_000,
      seguroDg: 180_000, seguroDiaria: 190,
    });
    setEtapa(6);
  }

  function definirQtd(n: number) {
    setR((x) => ({
      ...x,
      qtdDependentes: n,
      idadesDependentes: Array.from({ length: n }, (_, i) => x.idadesDependentes[i] ?? ""),
    }));
  }

  // Cada etapa devolve a lista de pendências; vazia = pode avançar.
  function pendencias(e: number): string[] {
    const p: string[] = [];
    if (e === 2) {
      if (r.temDependentes === undefined) p.push("Escolha Sim ou Não.");
      if (r.temDependentes && r.idadesDependentes.some((i) => i === "" || Number(i) < 0 || Number(i) > 99))
        p.push("Informe a idade de cada pessoa que depende de você.");
    }
    if (e === 3) {
      const idade = Number(r.idade);
      if (!(idade >= 18 && idade <= 80)) p.push("Informe sua idade (de 18 a 80 anos).");
      if (!r.sexo) p.push("Informe seu sexo.");
      if (r.fumante === undefined) p.push("Informe se você fuma.");
      if (!r.profissao) p.push("Escolha sua situação profissional.");
      if (r.renda <= 0) p.push("Informe sua renda mensal líquida.");
      if (r.custo <= 0) p.push("Informe o custo mensal da sua família.");
      if (r.renda > 0 && r.custo > r.renda * 3)
        p.push("O custo da família está mais de 3 vezes acima da renda. Confira os valores.");
    }
    if (e === 4 && r.imobiliaria > 0 && r.prestamista === undefined)
      p.push("Informe se o financiamento imobiliário tem seguro prestamista.");
    if (e === 5 && r.reserva === "") p.push("Informe quantos meses de reserva você tem.");
    return p;
  }

  const faltas = pendencias(etapa);

  function avancar() {
    setTentou(true);
    if (faltas.length) return;
    setTentou(false);
    setErro(null);
    setEtapa((e) => e + 1);
    window.scrollTo({ top: 0 });
  }

  function voltar() {
    setTentou(false);
    setErro(null);
    setEtapa((e) => Math.max(1, e - 1));
  }

  async function enviar() {
    setEnviando(true);
    setErro(null);
    const idade = Number(r.idade);
    const corpo = {
      idade,
      renda_mensal_liquida: r.renda,
      custo_familiar_mensal: r.custo,
      situacao_profissional: PROFISSOES[r.profissao],
      dependentes: r.temDependentes
        ? r.idadesDependentes.map((i) => ({ idade: Number(i), financeiramente_dependente: true }))
        : [],
      dividas: {
        imobiliaria: r.imobiliaria,
        imobiliaria_tem_prestamista: r.prestamista ?? false,
        empresarial: r.empresarial,
        veiculos: r.veiculos,
        outras: r.outras,
      },
      projetos: { educacao_filhos: r.educacao, quitacao_imovel: r.quitacaoImovel, outros: r.outrosProjetos },
      patrimonio_liquido: r.patrimonioLiquido,
      patrimonio_inventariavel: r.patrimonioInventariavel,
      meses_de_reserva: RESERVAS[r.reserva],
      seguro_atual: {
        morte: r.seguroMorte,
        invalidez: r.seguroInvalidez,
        doenca_grave: r.seguroDg,
        dit_diaria: r.seguroDiaria,
      },
    };
    try {
      const mapa = await api<Mapa>("/v1/diagnostico", { corpo });
      gravarFluxo({
        perfil: { idade, sexo: r.sexo!, fumante: r.fumante! },
        necessidadeId: mapa.necessidade_id,
        capitais: undefined,
        comparacao: undefined,
        escolhida: undefined,
        selecionadas: undefined,
      });
      sessionStorage.removeItem(CHAVE_RASCUNHO);
      router.push(`/mapa/${mapa.necessidade_id}`);
    } catch (e) {
      setErro(e instanceof ErroApi ? e.message : "Erro inesperado. Tente novamente.");
      setEnviando(false);
    }
  }

  const progresso = Math.round((etapa / TOTAL) * 100);

  return (
    <div className="mx-auto max-w-[1180px] px-5 py-8">
      <div className="flex items-center gap-4 mb-8">
        <Link href="/" aria-label="Voltar ao início" className="text-ink hover:text-action">
          <ArrowLeft size={22} />
        </Link>
        <span className="font-bold text-ink hidden sm:block">Diagnóstico da sua proteção</span>
        <div className="flex-1 flex items-center gap-3 max-w-[560px] sm:ml-auto">
          <span className="text-sm font-semibold text-ink whitespace-nowrap">
            Etapa {etapa} de {TOTAL}
          </span>
          <div
            className="flex-1 h-2.5 rounded-full bg-[#dbe7f3] overflow-hidden"
            role="progressbar"
            aria-valuenow={progresso}
            aria-valuemin={0}
            aria-valuemax={100}
          >
            <div className="h-full bg-teal rounded-full transition-all" style={{ width: `${progresso}%` }} />
          </div>
          <span className="text-sm font-semibold text-ink w-10 text-right">{progresso}%</span>
        </div>
      </div>

      <div className="grid lg:grid-cols-[1fr_360px] gap-10">
        <div>
          {etapa === 1 && <Intro />}
          {etapa === 2 && (
            <Passo
              titulo={
                <>
                  Alguém depende <em>financeiramente de você?</em>
                </>
              }
              sub="Considere filhos, cônjuge, pais ou qualquer outra pessoa que dependa da sua renda."
            >
              <Opcoes
                valor={r.temDependentes}
                onChange={(v) => set("temDependentes", v)}
                opcoes={[
                  { valor: true, texto: "Sim", ajuda: "Tenho pessoas que dependem da minha renda.", icone: <Users className="text-teal" /> },
                  { valor: false, texto: "Não", ajuda: "Não tenho dependentes financeiros.", icone: <User className="text-action" /> },
                ]}
              />
              {r.temDependentes && (
                <div className="card p-6 space-y-5">
                  <Opcoes
                    compacto
                    rotulo="Quantas pessoas dependem de você?"
                    valor={r.qtdDependentes}
                    onChange={definirQtd}
                    opcoes={[1, 2, 3, 4].map((n) => ({ valor: n, texto: n === 4 ? "4+" : String(n) }))}
                  />
                  <div className="grid sm:grid-cols-2 gap-4">
                    {r.idadesDependentes.map((v, i) => (
                      <Texto
                        key={i}
                        rotulo={`Idade da pessoa ${i + 1}`}
                        valor={v}
                        inputMode="numeric"
                        maxLength={2}
                        placeholder="Ex.: 8"
                        onChange={(x) => set("idadesDependentes", r.idadesDependentes.map((y, j) => (j === i ? x.replace(/\D/g, "") : y)))}
                      />
                    ))}
                  </div>
                </div>
              )}
            </Passo>
          )}
          {etapa === 3 && (
            <Passo
              titulo={
                <>
                  Você e <em>sua renda</em>
                </>
              }
              sub="Com isso calculamos quanto a sua família precisaria para manter o padrão de vida."
            >
              <div className="grid sm:grid-cols-3 gap-4">
                <Texto rotulo="Sua idade" valor={r.idade} inputMode="numeric" maxLength={2} placeholder="Ex.: 38" onChange={(v) => set("idade", v.replace(/\D/g, ""))} />
                <div className="sm:col-span-2">
                  <Opcoes compacto rotulo="Sexo" valor={r.sexo} onChange={(v) => set("sexo", v)} opcoes={[{ valor: "F" as const, texto: "Feminino" }, { valor: "M" as const, texto: "Masculino" }].map((o) => o)} />
                </div>
              </div>
              <Opcoes compacto rotulo="Você fuma?" valor={r.fumante} onChange={(v) => set("fumante", v)} opcoes={[{ valor: false, texto: "Não" }, { valor: true, texto: "Sim" }]} />
              <Selecao rotulo="Situação profissional" valor={r.profissao} onChange={(v) => set("profissao", v)} opcoes={Object.keys(PROFISSOES)} />
              <div className="grid sm:grid-cols-2 gap-4">
                <Dinheiro rotulo="Renda mensal líquida" ajuda="O que entra na sua conta por mês, já descontados os impostos." valor={r.renda} onChange={(v) => set("renda", v)} />
                <Dinheiro rotulo="Custo mensal da família" ajuda="Gastos da casa e de quem depende de você." valor={r.custo} onChange={(v) => set("custo", v)} />
              </div>
            </Passo>
          )}
          {etapa === 4 && (
            <Passo
              titulo={
                <>
                  Suas dívidas e <em>planos</em>
                </>
              }
              sub="Deixe em branco o que não se aplica."
            >
              <div className="card p-6 space-y-5">
                <h3 className="font-extrabold text-ink flex items-center gap-2"><CreditCard size={20} className="text-amber" /> Dívidas em aberto</h3>
                <div className="grid sm:grid-cols-2 gap-4">
                  <Dinheiro rotulo="Financiamento imobiliário" valor={r.imobiliaria} onChange={(v) => set("imobiliaria", v)} />
                  <Dinheiro rotulo="Dívidas da empresa" valor={r.empresarial} onChange={(v) => set("empresarial", v)} />
                  <Dinheiro rotulo="Financiamento de veículos" valor={r.veiculos} onChange={(v) => set("veiculos", v)} />
                  <Dinheiro rotulo="Outras dívidas" valor={r.outras} onChange={(v) => set("outras", v)} />
                </div>
                {r.imobiliaria > 0 && (
                  <Opcoes compacto rotulo="O financiamento imobiliário tem seguro prestamista?" valor={r.prestamista} onChange={(v) => set("prestamista", v)} opcoes={[{ valor: true, texto: "Sim" }, { valor: false, texto: "Não" }, ]} />
                )}
              </div>
              <div className="card p-6 space-y-5">
                <h3 className="font-extrabold text-ink flex items-center gap-2"><BarChart3 size={20} className="text-teal" /> Planos que você quer garantir</h3>
                <div className="grid sm:grid-cols-2 gap-4">
                  <Dinheiro rotulo="Educação dos filhos" valor={r.educacao} onChange={(v) => set("educacao", v)} />
                  <Dinheiro rotulo="Quitar um imóvel" valor={r.quitacaoImovel} onChange={(v) => set("quitacaoImovel", v)} />
                  <Dinheiro rotulo="Outros projetos" valor={r.outrosProjetos} onChange={(v) => set("outrosProjetos", v)} />
                </div>
              </div>
            </Passo>
          )}
          {etapa === 5 && (
            <Passo
              titulo={
                <>
                  O que você já <em>tem guardado</em>
                </>
              }
              sub="Ajuda a saber se sua família teria caixa para atravessar um momento difícil."
            >
              <div className="grid sm:grid-cols-2 gap-4">
                <Dinheiro rotulo="Dinheiro e investimentos" ajuda="O que pode ser usado rapidamente." valor={r.patrimonioLiquido} onChange={(v) => set("patrimonioLiquido", v)} />
                <Dinheiro rotulo="Bens em seu nome" ajuda="Imóveis, veículos e outros bens que entrariam num inventário." valor={r.patrimonioInventariavel} onChange={(v) => set("patrimonioInventariavel", v)} />
              </div>
              <Selecao rotulo="Reserva de emergência" valor={r.reserva} onChange={(v) => set("reserva", v)} opcoes={Object.keys(RESERVAS)} placeholder="Quantos meses de gastos você cobre?" />
            </Passo>
          )}
          {etapa === 6 && (
            <Passo
              titulo={
                <>
                  Sua <em>proteção atual</em>
                </>
              }
              sub="Some tudo o que você já tem em seguros de vida, inclusive o do trabalho. Deixe em branco o que não tiver."
            >
              <div className="grid sm:grid-cols-2 gap-4">
                <Dinheiro rotulo="Morte" valor={r.seguroMorte} onChange={(v) => set("seguroMorte", v)} />
                <Dinheiro rotulo="Invalidez" valor={r.seguroInvalidez} onChange={(v) => set("seguroInvalidez", v)} />
                <Dinheiro rotulo="Doenças graves" valor={r.seguroDg} onChange={(v) => set("seguroDg", v)} />
                <Dinheiro rotulo="Diária por internação" valor={r.seguroDiaria} sufixo="por dia" onChange={(v) => set("seguroDiaria", v)} />
              </div>
            </Passo>
          )}

          {tentou && faltas.length > 0 && (
            <div className="mt-6">
              <Aviso tom="erro">
                <ul className="list-disc pl-4">{faltas.map((f) => <li key={f}>{f}</li>)}</ul>
              </Aviso>
            </div>
          )}
          {erro && <div className="mt-6"><Aviso tom="erro">{erro}</Aviso></div>}

          <div className="mt-8 flex items-center justify-between gap-4">
            {etapa > 1 ? (
              <button type="button" onClick={voltar} className="btn btn-soft">
                <ArrowLeft size={18} aria-hidden /> Voltar
              </button>
            ) : <span />}
            {etapa < TOTAL ? (
              <button type="button" onClick={avancar} className="btn btn-primary min-w-[200px]">
                {etapa === 1 ? "Começar diagnóstico" : "Continuar"} <ArrowRight size={18} aria-hidden />
              </button>
            ) : (
              <button type="button" onClick={enviar} disabled={enviando} className="btn btn-primary min-w-[200px]">
                {enviando ? "Calculando…" : "Ver meu Mapa de Proteção"} {!enviando && <ArrowRight size={18} aria-hidden />}
              </button>
            )}
          </div>
          {etapa === 1 && (
            <p className="text-center mt-5">
              <Link href="/montar" className="text-action font-semibold underline">Prefiro montar minha proteção direto</Link>
            </p>
          )}
          {etapa === 1 && demo && (
            <p className="text-center mt-3">
              <button type="button" onClick={preencherExemplo} className="text-muted text-sm underline">
                Demonstração: preencher com um exemplo
              </button>
            </p>
          )}
        </div>

        <aside className="hidden lg:block space-y-5" aria-label="Apoio">
          <div className="card !bg-blue-tint !border-transparent p-6 flex gap-4">
            <span className="grid place-items-center w-11 h-11 rounded-full bg-white text-action shrink-0"><Lightbulb size={22} aria-hidden /></span>
            <p className="text-ink font-medium">
              {etapa === 1
                ? "Esta análise é educativa e baseada nas informações que você fornecer. Você poderá ajustar os valores antes de comparar."
                : "Essas informações nos ajudam a estimar o tamanho da proteção necessária para sua família."}
            </p>
          </div>
          <div className="rounded-3xl bg-gradient-to-br from-[#e3efff] to-[#e6f6f3] p-6">
            <Escudo className="w-full" />
          </div>
        </aside>
      </div>
    </div>
  );
}

function Passo({ titulo, sub, children }: { titulo: React.ReactNode; sub: string; children: React.ReactNode }) {
  return (
    <section className="space-y-6">
      <div>
        <h1 className="titulo text-[clamp(2.2rem,4.5vw,3.4rem)]">{titulo}</h1>
        <p className="text-lg text-body mt-3 max-w-[52ch]">{sub}</p>
      </div>
      {children}
    </section>
  );
}

function Intro() {
  const itens = [
    { Icon: Users, t: "Sua família", d: "Quantas pessoas dependem de você.", cor: "bg-blue-tint text-action" },
    { Icon: BarChart3, t: "Sua renda", d: "Sua renda atual e o custo da família.", cor: "bg-teal-tint text-teal" },
    { Icon: CreditCard, t: "Suas dívidas", d: "Seus compromissos financeiros em aberto.", cor: "bg-amber-tint text-amber" },
    { Icon: Shield, t: "Sua proteção atual", d: "O que você já possui, para identificar gaps.", cor: "bg-blue-tint text-action" },
  ];
  return (
    <section className="space-y-6">
      <h1 className="titulo text-[clamp(2.4rem,5vw,3.8rem)]">
        Vamos descobrir sua <em>necessidade de proteção</em>
      </h1>
      <p className="text-lg text-body max-w-[52ch]">Em poucos minutos, vamos entender sua realidade financeira e estimar quanto faz sentido proteger.</p>
      <div className="grid sm:grid-cols-2 gap-4">
        {itens.map(({ Icon, t, d, cor }) => (
          <div key={t} className="card p-5 flex gap-4 items-center">
            <span className={`grid place-items-center w-12 h-12 rounded-full shrink-0 ${cor}`}><Icon size={22} aria-hidden /></span>
            <div>
              <div className="font-extrabold text-ink">{t}</div>
              <div className="text-[14px] text-body">{d}</div>
            </div>
          </div>
        ))}
      </div>
    </section>
  );
}
