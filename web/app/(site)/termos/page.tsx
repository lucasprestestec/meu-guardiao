import { MARCA } from "@/lib/marca";
import Link from "next/link";

export const metadata = { title: `Termos e condições — ${MARCA}` };

// Marcador: o texto jurídico ainda não existe. Precisa ser substituído antes de
// qualquer uso com clientes reais.
export default function Termos() {
  return (
    <div className="mx-auto max-w-[720px] px-5 py-16 space-y-5">
      <h1 className="titulo text-4xl">
        Termos e <em>condições</em>
      </h1>
      <div className="rounded-2xl bg-amber-tint text-[#6b470d] p-5">
        <b>Documento em elaboração.</b> Esta página é um marcador da versão de demonstração. O texto definitivo dos
        termos e da política de privacidade será publicado aqui antes do uso com clientes reais.
      </div>
      <Link href="/" className="btn btn-secondary w-fit">Voltar ao início</Link>
    </div>
  );
}
