"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { ArrowLeft, ArrowRight, Pencil } from "lucide-react";
import { Dinheiro, Selecao, Texto } from "@/components/campos";
import { AvisoPreco, Selos, SemComparacao } from "@/components/opcao";
import {
  EXTRA_VAZIO, SecaoBeneficiarios, SecaoSeguradora, errosExtra, faixaDeRenda, mascaraCep, montarProposta,
  type Extra,
} from "@/components/proposta-form";
import { Aviso, Barra, Carregando, Etapas, ListaCoberturas, NomeSeguradora } from "@/components/ui";
import { FormDps, errosDps, respostasParaApi, textoResposta, visiveis, type Respostas } from "@/components/dps-form";
import { api, ErroApi, type CamposProposta, type QuestionarioDps } from "@/lib/api";
import {
  cpfValido, dataParaIso, idadeDe, mascaraCelular, mascaraCpf, mascaraData, mascararCpf, mascararEmail, pct, soDigitos,
} from "@/lib/format";
import { useFluxo } from "@/lib/fluxo";
import { RECURSOS } from "@/lib/recursos";

const UFS = ["AC","AL","AP","AM","BA","CE","DF","ES","GO","MA","MT","MS","MG","PA","PB","PR","PE","PI","RJ","RN","RS","RO","RR","SC","SP","SE","TO"];
const CIVIL = ["Solteiro(a)", "Casado(a) / união estável", "Divorciado(a)", "Viúvo(a)"];

// Mesmos textos que a API grava na trilha de consentimento (api/solicitacoes.py).
const CONSENTIMENTOS: { tipo: string; texto: string }[] = [
  { tipo: "VERACIDADE", texto: "Confirmo que as informações prestadas são verdadeiras." },
  { tipo: "TRATAMENTO_DADOS", texto: "Autorizo o tratamento dos meus dados para fins de cotação e contratação." },
  { tipo: "TERMOS", texto: "Li e concordo com os termos e condições." },
  { tipo: "VALORES_SUJEITOS_ANALISE", texto: "Entendo que os valores dependem da análise da seguradora." },
];

// Só exigido quando o cliente responde a DPS; mesmo texto que a API grava (api/solicitacoes.py).
const CONSENTIMENTO_DPS = {
  tipo: "DPS_CONFERENCIA",
  texto: "Conferi as minhas respostas de saúde e confirmo que estão corretas e completas. Entendo que omissão ou falsidade pode anular a proposta e a cobertura.",
};

type Dados = {
  nome: string; cpf: string; nascimento: string; email: string; celular: string;
  profissao: string; civil: string; cidade: string; uf: string;
};
const VAZIO: Dados = { nome: "", cpf: "", nascimento: "", email: "", celular: "", profissao: "", civil: "", cidade: "", uf: "" };

export default function Contratar() {
  const router = useRouter();
  const { fluxo, pronto } = useFluxo();
  const [d, setD] = useState<Dados>(VAZIO);
  const [x, setX] = useState<Extra>(EXTRA_VAZIO);
  const setExtra = (p: Partial<Extra>) => setX((v) => ({ ...v, ...p }));
  const [campos, setCampos] = useState<CamposProposta | null>(null);
  const [fase, setFase] = useState<"dados" | "saude" | "revisao">("dados");
  const [quest, setQuest] = useState<QuestionarioDps | null>(null);
  const [rDps, setRDps] = useState<Respostas>({});
  const [tentouSaude, setTentouSaude] = useState(false);
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

  // O que pedir depende da seguradora escolhida. Se a API não responder, o formulário segue sem
  // os campos extras (a API também aceita a solicitação sem eles enquanto não for obrigatório).
  const opSel = fluxo.comparacao?.opcoes.find((op) => op.produto_versao_id === fluxo.escolhida);
  const seguradora = opSel?.produto.seguradora;
  const demo = opSel?.produto.fonte_tarifa !== "SEGURADORA";
  useEffect(() => {
    if (!seguradora) return;
    let vivo = true;
    api<CamposProposta>(`/v1/proposta/campos?seguradora=${encodeURIComponent(seguradora)}`)
      .then((r) => vivo && setCampos(r))
      .catch(() => vivo && setCampos(null));
    // Perguntas de saúde da seguradora, com a redação dela. Sem resposta da API, segue sem DPS.
    api<QuestionarioDps>(`/v1/dps/questionario?seguradora=${encodeURIComponent(seguradora)}&demonstracao=${demo}`)
      .then((r) => vivo && setQuest(r))
      .catch(() => vivo && setQuest(null));
    return () => { vivo = false; };
  }, [seguradora, demo]);

  const c = fluxo.comparacao;
  const o = c?.opcoes.find((op) => op.produto_versao_id === fluxo.escolhida);
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
  const regras = { campos, sexo: fluxo.perfil?.sexo, fumante: fluxo.perfil?.fumante };
  const extras = errosExtra(x, d, regras);
  const temErro = Object.keys(erros).length > 0 || Object.keys(extras).length > 0;
  const e = (k: keyof Dados) => (tentou ? erros[k] : undefined);
  const ee = (k: string) => (tentou ? extras[k] : undefined);
  const perguntasDps = quest?.existe ? quest.perguntas ?? [] : [];
  const temDps = perguntasDps.length > 0;
  const errosS = temDps ? errosDps(perguntasDps, rDps) : {};
  const consentimentos = temDps ? [...CONSENTIMENTOS, CONSENTIMENTO_DPS] : CONSENTIMENTOS;

  function continuar() {
    setTentou(true);
    if (temErro) return;
    setErro(null);
    setFase(temDps ? "saude" : "revisao");
    window.scrollTo({ top: 0 });
  }

  function continuarSaude() {
    setTentouSaude(true);
    if (Object.keys(errosS).length > 0) return;
    setFase("revisao");
    window.scrollTo({ top: 0 });
  }

  const todosAceites = consentimentos.every((x) => aceites[x.tipo]);

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
            celular: soDigitos(d.celular), profissao: d.profissao.trim() || null,
            faixa_renda: x.renda > 0 ? faixaDeRenda(x.renda) : null,
            estado_civil: d.civil || null, cidade: d.cidade.trim() || null, uf: d.uf || null,
          },
          proposta: campos ? montarProposta(x, regras, new Set(campos.exigidos)) : undefined,
          dps: temDps ? respostasParaApi(perguntasDps, rDps) : undefined,
          consentimentos: consentimentos.map((x) => x.tipo),
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
                    <Texto rotulo="Nome social (opcional)" valor={x.nomeSocial} onChange={(v) => setExtra({ nomeSocial: v })} />
                  </div>
                  {fluxo.perfil && (
                    <p className="text-[13px] text-muted">Sexo: <b>{fluxo.perfil.sexo === "M" ? "masculino" : "feminino"}</b>, como você informou na comparação. O preço depende dele.</p>
                  )}
                </section>

                <section className="card p-6 mt-5 space-y-4">
                  <h2 className="text-xl font-extrabold">Profissão, renda e saúde básica</h2>
                  <div className="grid sm:grid-cols-2 gap-4">
                    <Texto rotulo="Profissão" valor={d.profissao} onChange={set("profissao")} placeholder="Ex.: Analista de marketing" erro={tentou ? extras.profissao : undefined} />
                    <Dinheiro rotulo="Renda mensal" valor={x.renda} onChange={(v) => setExtra({ renda: v })} ajuda={ee("renda")} />
                    <Selecao rotulo="Estado civil" valor={d.civil} onChange={set("civil")} opcoes={CIVIL} erro={tentou ? extras.civil : undefined} />
                    <div className="grid grid-cols-2 gap-3">
                      <Texto rotulo="Peso (kg)" valor={x.peso} onChange={(v) => setExtra({ peso: v.replace(/[^\d.,]/g, "").slice(0, 5) })} inputMode="numeric" placeholder="Ex.: 72,5" erro={ee("peso")} />
                      <Texto rotulo="Altura (cm)" valor={x.altura} onChange={(v) => setExtra({ altura: soDigitos(v).slice(0, 3) })} inputMode="numeric" placeholder="Ex.: 175" erro={ee("altura")} />
                    </div>
                  </div>
                  <p className="text-[13px] text-muted">Renda, profissão, peso e altura são usados pela seguradora para aceitar o risco e fixar o prêmio. Informe valores verdadeiros: omissão ou erro pode reduzir ou anular a cobertura.</p>
                </section>

                <section className="card p-6 mt-5 space-y-4">
                  <h2 className="text-xl font-extrabold">Endereço</h2>
                  <div className="grid sm:grid-cols-[170px_1fr] gap-4">
                    <Texto rotulo="CEP" valor={x.cep} onChange={(v) => setExtra({ cep: mascaraCep(v) })} placeholder="00000-000" inputMode="numeric" autoComplete="postal-code" erro={ee("cep")} />
                    <Texto rotulo="Logradouro" valor={x.logradouro} onChange={(v) => setExtra({ logradouro: v })} placeholder="Rua, avenida…" autoComplete="address-line1" erro={ee("logradouro")} />
                  </div>
                  <div className="grid sm:grid-cols-3 gap-4">
                    <div>
                      <Texto rotulo="Número" valor={x.semNumero ? "S/N" : x.numero} onChange={(v) => setExtra({ numero: v.slice(0, 20) })} erro={ee("numero")} />
                      <label className="flex items-center gap-2 mt-2 text-[14px] text-body cursor-pointer">
                        <input type="checkbox" className="w-4 h-4 accent-[var(--action)]" checked={x.semNumero} onChange={(ev) => setExtra({ semNumero: ev.target.checked })} /> Sem número
                      </label>
                    </div>
                    <Texto rotulo="Complemento (opcional)" valor={x.complemento} onChange={(v) => setExtra({ complemento: v })} />
                    <Texto rotulo="Bairro" valor={x.bairro} onChange={(v) => setExtra({ bairro: v })} erro={ee("bairro")} />
                  </div>
                  <div className="grid grid-cols-[1fr_110px] gap-3 sm:max-w-[520px]">
                    <Texto rotulo="Cidade" valor={d.cidade} onChange={set("cidade")} placeholder="Sua cidade" autoComplete="address-level2" erro={tentou ? extras.cidade : undefined} />
                    <Selecao rotulo="UF" valor={d.uf} onChange={set("uf")} opcoes={UFS} placeholder="UF" erro={tentou ? extras.uf : undefined} />
                  </div>
                </section>

                <SecaoSeguradora x={x} set={setExtra} campos={campos} erros={extras} mostrar={tentou} fumante={fluxo.perfil?.fumante} />
                <SecaoBeneficiarios x={x} set={setExtra} campos={campos} erros={extras} mostrar={tentou} />
              </>
            ) : fase === "saude" ? (
              <>
                <h1 className="titulo text-[clamp(2.2rem,4.5vw,3.4rem)]">Suas <em>perguntas de saúde.</em></h1>
                <p className="text-lg text-body mt-3">São as perguntas da {seguradora}. Responda com sinceridade: as respostas seguem para a seguradora exatamente como você marcar.</p>
                {quest && quest.confirmado === false && (
                  <div className="mt-4"><Aviso>Demonstração: a redação destas perguntas ainda está em conferência com a seguradora.</Aviso></div>
                )}
                <div className="mt-6">
                  <FormDps perguntas={perguntasDps} r={rDps} onChange={setRDps} erros={errosS} mostrar={tentouSaude} />
                </div>
                <div className="mt-5"><Aviso>Omissão ou informação falsa pode anular a proposta e a cobertura.</Aviso></div>
                <button type="button" onClick={() => { setFase("dados"); window.scrollTo({ top: 0 }); }} className="mt-5 flex items-center gap-1.5 font-semibold text-action">
                  <ArrowLeft size={16} aria-hidden /> Voltar aos dados
                </button>
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
                      ["Renda mensal", x.renda > 0 ? `R$ ${x.renda.toLocaleString("pt-BR")}` : "—"],
                      ["Peso e altura", x.peso && x.altura ? `${x.peso} kg · ${x.altura} cm` : "—"],
                      ["Endereço", [x.logradouro, x.semNumero ? "s/n" : x.numero, x.bairro, d.cidade && `${d.cidade}/${d.uf}`].filter(Boolean).join(", ") || "—"],
                      ["Beneficiários", x.legais ? "Beneficiários legais" : `${x.beneficiarios.length} indicado(s)`],
                    ].map(([k, v]) => (
                      <div key={k} className="flex justify-between gap-4 py-2.5 border-b border-line">
                        <dt className="text-muted">{k}</dt>
                        <dd className="font-semibold text-ink text-right break-all">{v}</dd>
                      </div>
                    ))}
                  </dl>
                </section>

                {temDps && (
                  <section className="card p-6 mt-5">
                    <div className="flex items-center justify-between">
                      <h2 className="text-xl font-extrabold">Suas respostas de saúde</h2>
                      <button type="button" onClick={() => setFase("saude")} className="flex items-center gap-1.5 font-semibold text-action">
                        <Pencil size={15} aria-hidden /> Editar respostas
                      </button>
                    </div>
                    <p className="text-[14px] text-body mt-1">Confira: é assim que elas serão informadas à seguradora.</p>
                    <ol className="mt-3 text-[14px]">
                      {visiveis(perguntasDps, rDps).map((q) => (
                        <li key={q.id} className="py-2.5 border-b border-line last:border-0">
                          <div className="text-muted">{q.texto}</div>
                          <div className="font-semibold text-ink">{textoResposta(q, rDps[q.id])}</div>
                        </li>
                      ))}
                    </ol>
                  </section>
                )}

                <section className="card p-6 mt-5">
                  <h2 className="text-xl font-extrabold">Declarações e consentimentos</h2>
                  <p className="text-body text-[15px]">Para seguir, leia e confirme os itens abaixo.</p>
                  <ul className="mt-4 space-y-3">
                    {consentimentos.map((x) => (
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
              <AvisoPreco className="mt-1" />
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
            ) : fase === "saude" ? (
              <button type="button" className="btn btn-primary w-full" onClick={continuarSaude}>
                Revisar solicitação <ArrowRight size={18} aria-hidden />
              </button>
            ) : (
              <button type="button" className="btn btn-primary w-full" disabled={!todosAceites || enviando} onClick={enviar}>
                {enviando ? "Enviando…" : "Solicitar contratação"} {!enviando && <ArrowRight size={18} aria-hidden />}
              </button>
            )}
            <Link href="/comparar" className="btn btn-secondary w-full">Voltar para comparação</Link>
            {tentou && temErro && fase === "dados" && <Aviso tom="erro">Corrija os campos destacados para continuar.</Aviso>}
            {tentouSaude && fase === "saude" && Object.keys(errosS).length > 0 && <Aviso tom="erro">Responda todas as perguntas para continuar.</Aviso>}
          </aside>
        </div>
      </div>
    </>
  );
}
