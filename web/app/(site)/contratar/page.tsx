"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { ArrowLeft, ArrowRight, Pencil } from "lucide-react";
import { Selecao, Texto } from "@/components/campos";
import { Selos, SemComparacao } from "@/components/opcao";
import { Aviso, Barra, Carregando, Etapas, ListaCoberturas, NomeSeguradora } from "@/components/ui";
import { api, ErroApi } from "@/lib/api";
import {
  cpfValido, dataParaIso, idadeDe, mascaraCelular, mascaraCpf, mascaraData, mascararCpf, mascararEmail, pct, soDigitos,
} from "@/lib/format";
import { useFluxo } from "@/lib/fluxo";
import { RECURSOS } from "@/lib/recursos";

const UFS = ["AC","AL","AP","AM","BA","CE","DF","ES","GO","MA","MT","MS","MG","PA","PB","PR","PE","PI","RJ","RN","RS","RO","RR","SC","SP","SE","TO"];
const RENDAS = ["Até R$ 3.000", "R$ 3.000 a R$ 6.000", "R$ 6.000 a R$ 10.000", "R$ 10.000 a R$ 20.000", "Acima de R$ 20.000"];
const CIVIL = ["Solteiro(a)", "Casado(a) / união estável", "Divorciado(a)", "Viúvo(a)"];

// Mesmos textos que a API grava na trilha de consentimento (api/solicitacoes.py).
const CONSENTIMENTOS: { tipo: string; texto: string }[] = [
  { tipo: "VERACIDADE", texto: "Confirmo que as informações prestadas são verdadeiras." },
  { tipo: "TRATAMENTO_DADOS", texto: "Autorizo o tratamento dos meus dados para fins de cotação e contratação." },
  { tipo: "TERMOS", texto: "Li e concordo com os termos e condições." },
  { tipo: "VALORES_SUJEITOS_ANALISE", texto: "Entendo que os valores dependem da análise da seguradora." },
];

type Dados = {
  nome: string; cpf: string; nascimento: string; email: string; celular: string;
  profissao: string; renda: string; civil: string; cidade: string; uf: string;
};
const VAZIO: Dados = { nome: "", cpf: "", nascimento: "", email: "", celular: "", profissao: "", renda: "", civil: "", cidade: "", uf: "" };

export default function Contratar() {
  const router = useRouter();
  const { fluxo, pronto } = useFluxo();
  const [d, setD] = useState<Dados>(VAZIO);
  const [fase, setFase] = useState<"dados" | "revisao">("dados");
  const [tentou, setTentou] = useState(false);
  const [aceites, setAceites] = useState<Record<string, boolean>>({});
  const [enviando, setEnviando] = useState(false);
  const [erro, setErro] = useState<string | null>(null);
  const [recado, setRecado] = useState("");
  const set = (k: keyof Dados) => (v: string) => setD((x) => ({ ...x, [k]: v }));

  // Pré-preenche com o contato já informado antes do Mapa (continua editável).
  useEffect(() => {
    const ct = fluxo.contato;
    if (!pronto || !ct) return;
    setD((x) => ({ ...x, nome: x.nome || ct.nome, email: x.email || ct.email, celular: x.celular || ct.celular }));
  }, [pronto, fluxo.contato]);

  const c = fluxo.comparacao;
  const o = c?.opcoes.find((x) => x.produto_versao_id === fluxo.escolhida);
  if (!pronto) return <Carregando />;
  if (!c || !o) return <SemComparacao />;

  const iso = dataParaIso(d.nascimento);
  const idade = iso ? idadeDe(iso) : null;
  const erros: Partial<Record<keyof Dados, string>> = {};
  if (d.nome.trim().split(/\s+/).length < 2) erros.nome = "Informe nome e sobrenome.";
  if (!cpfValido(d.cpf)) erros.cpf = "CPF inválido.";
  if (!iso) erros.nascimento = "Use o formato dd/mm/aaaa.";
  else if (fluxo.perfil && idade !== fluxo.perfil.idade)
    erros.nascimento = `Esta data indica ${idade} anos, mas a comparação foi feita para ${fluxo.perfil.idade}. O preço depende da idade: refaça a comparação com a idade correta.`;
  if (!/^[^@\s]+@[^@\s]+\.[^@\s]+$/.test(d.email.trim())) erros.email = "E-mail inválido.";
  if (![10, 11].includes(soDigitos(d.celular).length)) erros.celular = "Informe DDD e número.";
  const temErro = Object.keys(erros).length > 0;
  const e = (k: keyof Dados) => (tentou ? erros[k] : undefined);

  function continuar() {
    setTentou(true);
    if (temErro) return;
    setErro(null);
    setFase("revisao");
    window.scrollTo({ top: 0 });
  }

  const todosAceites = CONSENTIMENTOS.every((x) => aceites[x.tipo]);

  async function enviar() {
    setEnviando(true);
    setErro(null);
    try {
      const r = await api<{ id: string }>("/v1/solicitacoes", {
        corpo: {
          cotacao_id: c!.cotacao_id,
          produto_versao_id: o!.produto_versao_id,
          dados: {
            nome: d.nome.trim(), cpf: soDigitos(d.cpf), data_nascimento: iso, email: d.email.trim(),
            celular: soDigitos(d.celular), profissao: d.profissao.trim() || null, faixa_renda: d.renda || null,
            estado_civil: d.civil || null, cidade: d.cidade.trim() || null, uf: d.uf || null,
          },
          consentimentos: CONSENTIMENTOS.map((x) => x.tipo),
          recado: recado.trim() || undefined,
        },
      });
      router.push(`/acompanhar/${r.id}`);
    } catch (x) {
      setErro(x instanceof ErroApi ? x.message : "Erro inesperado. Tente novamente.");
      setEnviando(false);
    }
  }

  return (
    <>
      <div className="mx-auto max-w-[1180px] px-5 py-8">
        <div className="flex flex-wrap items-center gap-6 mb-8">
          <Link href="/comparar" className="flex items-center gap-2 font-semibold text-action">
            <ArrowLeft size={18} aria-hidden /> Voltar
          </Link>
          <Etapas atual={4} />
        </div>

        <div className="grid lg:grid-cols-[1fr_380px] gap-8 items-start">
          <div>
            {fase === "dados" ? (
              <>
                <h1 className="titulo text-[clamp(2.2rem,4.5vw,3.4rem)]">Agora vamos preparar <em>sua solicitação.</em></h1>
                <p className="text-lg text-body mt-3">Preencha seus dados para seguirmos com a contratação.</p>

                <section className="card p-6 mt-6 space-y-4">
                  <h2 className="text-xl font-extrabold">Dados pessoais</h2>
                  <div className="grid sm:grid-cols-[1.6fr_1fr] gap-4">
                    <Texto rotulo="Nome completo" valor={d.nome} onChange={set("nome")} placeholder="Digite seu nome completo" autoComplete="name" erro={e("nome")} />
                    <Texto rotulo="CPF" valor={d.cpf} onChange={(v) => set("cpf")(mascaraCpf(v))} placeholder="000.000.000-00" inputMode="numeric" erro={e("cpf")} />
                  </div>
                  <div className="grid sm:grid-cols-2 gap-4">
                    <Texto rotulo="Data de nascimento" valor={d.nascimento} onChange={(v) => set("nascimento")(mascaraData(v))} placeholder="dd/mm/aaaa" inputMode="numeric" autoComplete="bday" erro={e("nascimento")} />
                    <Texto rotulo="E-mail" valor={d.email} onChange={set("email")} placeholder="seu@email.com" inputMode="email" autoComplete="email" erro={e("email")} />
                  </div>
                  <div className="grid sm:grid-cols-2 gap-4">
                    <Texto rotulo="Celular (WhatsApp)" valor={d.celular} onChange={(v) => set("celular")(mascaraCelular(v))} placeholder="(11) 99999-9999" inputMode="tel" autoComplete="tel" erro={e("celular")} />
                  </div>
                </section>

                <section className="card p-6 mt-5 space-y-4">
                  <h2 className="text-xl font-extrabold">Informações complementares <span className="text-sm font-medium text-muted">(opcional)</span></h2>
                  <div className="grid sm:grid-cols-2 gap-4">
                    <Texto rotulo="Profissão" valor={d.profissao} onChange={set("profissao")} placeholder="Ex.: Analista de marketing" />
                    <Selecao rotulo="Renda mensal" valor={d.renda} onChange={set("renda")} opcoes={RENDAS} placeholder="Selecione sua faixa de renda" />
                    <Selecao rotulo="Estado civil" valor={d.civil} onChange={set("civil")} opcoes={CIVIL} />
                    <div className="grid grid-cols-[1fr_110px] gap-3">
                      <Texto rotulo="Cidade" valor={d.cidade} onChange={set("cidade")} placeholder="Sua cidade" autoComplete="address-level2" />
                      <Selecao rotulo="UF" valor={d.uf} onChange={set("uf")} opcoes={UFS} placeholder="UF" />
                    </div>
                  </div>
                  <p className="text-[13px] text-muted">Usaremos essas informações apenas para sua solicitação e análise junto à seguradora.</p>
                </section>
              </>
            ) : (
              <>
                <h1 className="titulo text-[clamp(2.2rem,4.5vw,3.4rem)]">Revise sua solicitação <em>antes de enviar.</em></h1>
                <p className="text-lg text-body mt-3">Confirme os dados e aceite os termos para prosseguir.</p>

                <section className="card p-6 mt-6">
                  <div className="flex items-center justify-between">
                    <h2 className="text-xl font-extrabold">Resumo dos dados</h2>
                    <button type="button" onClick={() => setFase("dados")} className="flex items-center gap-1.5 font-semibold text-action">
                      <Pencil size={15} aria-hidden /> Editar dados
                    </button>
                  </div>
                  <dl className="mt-4 grid sm:grid-cols-2 gap-x-10 text-[15px]">
                    {[
                      ["Nome", d.nome.trim()], ["Celular", d.celular], ["CPF", mascararCpf(d.cpf)], ["Profissão", d.profissao || "—"],
                      ["E-mail", mascararEmail(d.email.trim())], ["Nascimento", d.nascimento],
                    ].map(([k, v]) => (
                      <div key={k} className="flex justify-between gap-4 py-2.5 border-b border-line">
                        <dt className="text-muted">{k}</dt>
                        <dd className="font-semibold text-ink text-right break-all">{v}</dd>
                      </div>
                    ))}
                  </dl>
                </section>

                <section className="card p-6 mt-5">
                  <h2 className="text-xl font-extrabold">Declarações e consentimentos</h2>
                  <p className="text-body text-[15px]">Para seguir, leia e confirme os itens abaixo.</p>
                  <ul className="mt-4 space-y-3">
                    {CONSENTIMENTOS.map((x) => (
                      <li key={x.tipo}>
                        <label className="flex gap-3 items-start cursor-pointer">
                          <input type="checkbox" className="w-5 h-5 mt-0.5 accent-[var(--action)] shrink-0" checked={!!aceites[x.tipo]} onChange={(ev) => setAceites((a) => ({ ...a, [x.tipo]: ev.target.checked }))} />
                          <span className="text-ink">
                            {x.tipo === "TERMOS" ? (
                              <>Li e concordo com os <Link href="/termos" target="_blank" className="text-action underline">termos e condições</Link>.</>
                            ) : x.texto}
                          </span>
                        </label>
                      </li>
                    ))}
                  </ul>
                </section>

                <section className="card p-6 mt-5">
                  <label htmlFor="recado" className="text-xl font-extrabold block">Quer deixar um recado para o especialista?</label>
                  <p className="text-body text-[15px] mt-1">Uma observação, uma dúvida ou um pedido de alteração. É opcional e chega junto com a sua solicitação.</p>
                  <textarea id="recado" className="field mt-3" rows={3} maxLength={1000} value={recado} onChange={(ev) => setRecado(ev.target.value)} placeholder="Escreva aqui o que quiser" />
                </section>

                <div className="mt-5"><Aviso>Nesta etapa não pedimos dados de cartão nem fazemos nenhuma cobrança.</Aviso></div>
                {erro && <div className="mt-4"><Aviso tom="erro">{erro}</Aviso></div>}
              </>
            )}
          </div>

          <aside className="space-y-5 lg:sticky lg:top-6">
            <section className="rounded-3xl bg-teal-tint p-6">
              <h2 className="text-xl font-extrabold">Sua opção escolhida</h2>
              <div className="mt-2 flex items-start justify-between gap-3">
                <div>
                  {RECURSOS.destaques && <div className="mb-2"><Selos id={o.produto_versao_id} destaques={c.destaques} /></div>}
                  <NomeSeguradora nome={o.produto.seguradora} />
                </div>
              </div>
              <div className="mt-2 text-4xl font-extrabold text-ink tracking-tight">R$ {Math.round(o.premio_mensal).toLocaleString("pt-BR")}<span className="text-base text-muted font-semibold">/mês</span></div>
              {RECURSOS.aderencia && (
                <>
                  <div className="text-[15px] mt-1"><b className="text-teal">{pct(o.aderencia_total)}</b> de aderência</div>
                  <div className="mt-2"><Barra valor={o.aderencia_total} /></div>
                </>
              )}
              <h3 className="font-bold text-ink mt-4 text-[15px]">Coberturas selecionadas</h3>
              <ListaCoberturas itens={o.itens} />
              <p className="text-[13px] text-muted mt-3">Coberturas e vigência passam a valer conforme a apólice emitida, após a análise da seguradora.</p>
            </section>

            {fase === "dados" ? (
              <button type="button" className="btn btn-primary w-full" onClick={continuar}>
                Continuar <ArrowRight size={18} aria-hidden />
              </button>
            ) : (
              <button type="button" className="btn btn-primary w-full" disabled={!todosAceites || enviando} onClick={enviar}>
                {enviando ? "Enviando…" : "Solicitar contratação"} {!enviando && <ArrowRight size={18} aria-hidden />}
              </button>
            )}
            <Link href="/comparar" className="btn btn-secondary w-full">Voltar para comparação</Link>
            {tentou && temErro && fase === "dados" && <Aviso tom="erro">Corrija os campos destacados para continuar.</Aviso>}
          </aside>
        </div>
      </div>
    </>
  );
}
