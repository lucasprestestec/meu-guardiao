import Link from "next/link";
import { ArrowRight, BarChart3, FileText, ShieldCheck, SlidersHorizontal, User } from "lucide-react";
import { Escudo } from "@/components/escudo";

const PORTAS = [
  {
    href: "/montar",
    titulo: "Quero montar minha proteção",
    texto: "Escolha suas coberturas e compare opções.",
    cta: "Começar",
    Icon: ShieldCheck,
    tom: "bg-blue-tint",
    icone: "bg-[#d7e6fc] text-action",
    botao: "btn-primary",
  },
  {
    href: "/diagnostico",
    titulo: "Me ajude a descobrir quanto preciso",
    texto: "Responda algumas perguntas e veja sua necessidade estimada.",
    cta: "Fazer diagnóstico",
    Icon: BarChart3,
    tom: "bg-teal-tint",
    icone: "bg-[#cdeee8] text-teal",
    botao: "bg-teal text-white hover:brightness-95",
  },
  {
    href: null,
    titulo: "Já tenho seguro",
    texto: "Analise sua proteção atual e veja possíveis gaps.",
    cta: "Em breve",
    Icon: FileText,
    tom: "bg-amber-tint",
    icone: "bg-[#fbe6bd] text-amber",
    botao: "bg-[#e9dcc0] text-[#8a6a1f] cursor-not-allowed",
  },
];

export default function Home() {
  return (
    <div>
      <section className="mx-auto max-w-[1180px] px-5 pt-12 pb-8 grid lg:grid-cols-[1.15fr_1fr] gap-8 items-center">
        <div>
          <p className="text-[12px] font-bold tracking-[0.14em] uppercase text-action mb-5">
            Vida mais tranquila começa com escolhas mais conscientes
          </p>
          <h1 className="titulo text-[clamp(2.8rem,6vw,4.6rem)]">
            Seguro de vida
            <br />
            <em>do seu jeito.</em>
          </h1>
          <p className="mt-6 text-xl text-body max-w-[34ch]">
            Você sabe o que importa. A gente ajuda a descobrir quanto proteger e a encontrar as melhores opções.
          </p>
          <div className="mt-8 flex flex-wrap items-center gap-4">
            <Link href="/diagnostico" className="btn btn-primary text-lg !px-8 !py-4">
              Começar agora <ArrowRight size={20} aria-hidden />
            </Link>
            <Link href="#como-funciona" className="font-semibold text-action hover:underline">
              Ver como funciona
            </Link>
          </div>
          <p className="font-script text-3xl text-teal mt-8 -rotate-2 w-fit">Hoje mais proteção para muitos amanhãs.</p>
        </div>
        <div className="relative hidden lg:block">
          <div className="absolute inset-0 -z-10 rounded-[40px] bg-gradient-to-br from-[#e3efff] to-[#e6f6f3]" />
          <Escudo className="w-full max-w-[460px] mx-auto py-6" />
        </div>
      </section>

      <section className="mx-auto max-w-[1180px] px-5 grid md:grid-cols-3 gap-5" aria-label="Escolha por onde começar">
        {PORTAS.map(({ href, titulo, texto, cta, Icon, tom, icone, botao }) => {
          const conteudo = (
            <>
              <span className={`grid place-items-center w-12 h-12 rounded-xl ${icone}`}>
                <Icon size={24} aria-hidden />
              </span>
              <h2 className="text-2xl font-extrabold leading-tight mt-5 text-ink">{titulo}</h2>
              <p className="mt-2 text-body flex-1">{texto}</p>
              <span className={`btn ${botao} mt-6 w-fit`}>
                {cta} {href && <ArrowRight size={18} aria-hidden />}
              </span>
            </>
          );
          return href ? (
            <Link
              key={titulo}
              href={href}
              className={`${tom} rounded-3xl p-7 flex flex-col border border-white/60 hover:-translate-y-0.5 transition-transform`}
            >
              {conteudo}
            </Link>
          ) : (
            <div key={titulo} className={`${tom} rounded-3xl p-7 flex flex-col opacity-90`} aria-disabled>
              {conteudo}
            </div>
          );
        })}
      </section>

      <section id="como-funciona" className="mx-auto max-w-[1180px] px-5 py-14 grid md:grid-cols-3 gap-8">
        {[
          { Icon: User, t: "Diagnóstico personalizado", d: "Entenda sua necessidade com base na sua realidade." },
          { Icon: SlidersHorizontal, t: "Comparação por aderência", d: "Veja quanto cada opção realmente cobre do que você precisa, não só o preço." },
          { Icon: ShieldCheck, t: "Acompanhamento da contratação", d: "Acompanhe cada etapa, até a sua apólice." },
        ].map(({ Icon, t, d }) => (
          <div key={t} className="flex gap-4">
            <span className="grid place-items-center w-14 h-14 rounded-full bg-blue-tint text-action shrink-0">
              <Icon size={26} aria-hidden />
            </span>
            <div>
              <h3 className="font-bold text-ink text-lg">{t}</h3>
              <p className="text-body mt-1">{d}</p>
            </div>
          </div>
        ))}
      </section>
    </div>
  );
}
