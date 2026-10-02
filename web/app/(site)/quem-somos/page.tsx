import Link from "next/link";
import { EMPRESA, ou } from "@/lib/empresa";
import { MARCA } from "@/lib/marca";

export const metadata = { title: `Quem somos — ${MARCA}` };

// Registro SUSEP e CNPJ ficam em branco, prontos para preencher em lib/empresa.ts: a empresa
// ainda não existe. O texto institucional (experiência, por que o negócio existe) vem do cliente.
export default function QuemSomos() {
  return (
    <div className="mx-auto max-w-[720px] px-5 py-16 space-y-6">
      <h1 className="titulo text-4xl">
        Quem <em>somos</em>
      </h1>
      <dl className="card divide-y divide-line text-[15px]">
        {[
          ["Razão social", EMPRESA.razaoSocial],
          ["CNPJ", EMPRESA.cnpj],
          ["Registro SUSEP", EMPRESA.registroSusep],
        ].map(([k, v]) => (
          <div key={k} className="flex justify-between gap-4 px-5 py-3">
            <dt className="text-muted">{k}</dt>
            <dd className="font-semibold text-ink">{ou(v)}</dd>
          </div>
        ))}
      </dl>
      <div className="rounded-2xl bg-amber-tint text-[#6b470d] p-5">
        <b>Texto institucional em elaboração.</b> Aqui entram a experiência da equipe e a razão de existir do negócio.
      </div>
      <Link href="/" className="btn btn-secondary w-fit">Voltar ao início</Link>
    </div>
  );
}
