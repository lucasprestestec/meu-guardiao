import Link from "next/link";
import { BannerAmbiente } from "@/components/banner-ambiente";
import { Logo } from "@/components/ui";
import { Especialista } from "@/components/especialista";
import { EMPRESA, ou } from "@/lib/empresa";
import { MARCA } from "@/lib/marca";

export default function SiteLayout({ children }: LayoutProps<"/">) {
  return (
    <>
      <header className="bg-white border-b border-line">
        <div className="mx-auto max-w-[1180px] px-5 h-[72px] flex items-center justify-between gap-4">
          <Link href="/" aria-label={`${MARCA} — início`} className="flex items-center gap-4">
            <Logo />
            <span className="hidden md:block text-[13px] leading-tight text-muted border-l border-line pl-4">
              Mais proteção
              <br />
              para o que realmente importa.
            </span>
          </Link>
          <nav className="flex items-center gap-2 sm:gap-6 font-semibold text-ink">
            <Link href="/#como-funciona" className="hidden sm:block hover:text-action">
              Como funciona
            </Link>
            <Link href="/diagnostico" className="btn btn-primary !py-2.5 !px-4 sm:!px-5 whitespace-nowrap">
              Começar agora
            </Link>
          </nav>
        </div>
      </header>
      <BannerAmbiente />
      <main className="flex-1">{children}</main>
      <Especialista />
      <footer className="bg-white border-t border-line">
        <div className="mx-auto max-w-[1180px] px-5 py-5 flex flex-col sm:flex-row gap-2 sm:items-center sm:justify-between text-[13px] text-muted">
          <span className="flex items-center gap-3">
            <Logo small /> Marketplace digital de seguros de vida
          </span>
          <span>Comparações e valores sujeitos à análise e regras das seguradoras.</span>
        </div>
        <div className="mx-auto max-w-[1180px] px-5 pb-5 flex flex-wrap gap-x-5 gap-y-1 text-[12px] text-muted">
          <span>CNPJ: {ou(EMPRESA.cnpj)}</span>
          <span>Registro SUSEP: {ou(EMPRESA.registroSusep)}</span>
          <Link href="/quem-somos" className="underline hover:text-ink">Quem somos</Link>
          <Link href="/privacidade" className="underline hover:text-ink">Política de Privacidade</Link>
          <Link href="/termos" className="underline hover:text-ink">Termos</Link>
        </div>
      </footer>
    </>
  );
}
