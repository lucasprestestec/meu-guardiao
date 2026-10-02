import Link from "next/link";
import { MARCA } from "@/lib/marca";

export const metadata = { title: `Política de Privacidade — ${MARCA}` };

// Marcador. O texto está em revisão jurídica (docs/LGPD-RASCUNHO.md) e NÃO pode ser publicado
// antes disso. Quando a revisão terminar, o texto final substitui o aviso abaixo.
export default function Privacidade() {
  return (
    <div className="mx-auto max-w-[720px] px-5 py-16 space-y-5">
      <h1 className="titulo text-4xl">
        Política de <em>Privacidade</em>
      </h1>
      <div className="rounded-2xl bg-amber-tint text-[#6b470d] p-5">
        <b>Documento em revisão jurídica.</b> O texto definitivo da Política de Privacidade será publicado aqui antes do
        uso com clientes reais.
      </div>
      <Link href="/" className="btn btn-secondary w-fit">Voltar ao início</Link>
    </div>
  );
}
