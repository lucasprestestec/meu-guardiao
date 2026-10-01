import Link from "next/link";
import { BannerAmbiente } from "@/components/banner-ambiente";
import { Logo } from "@/components/ui";
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
      <footer className="bg-white border-t border-line">
        <div className="mx-auto max-w-[1180px] px-5 py-5 flex flex-col sm:flex-row gap-2 sm:items-center sm:justify-between text-[13px] text-muted">
          <span className="flex items-center gap-3">
            <Logo small /> Marketplace digital de seguros de vida
          </span>
          <span>Comparações e valores sujeitos à análise e regras das seguradoras.</span>
        </div>
      </footer>
    </>
  );
}
