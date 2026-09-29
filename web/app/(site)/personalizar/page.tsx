"use client";

import { useSearchParams } from "next/navigation";
import { Suspense } from "react";
import { Personalizar } from "@/components/personalizar";
import { Carregando } from "@/components/ui";

function Conteudo() {
  const n = useSearchParams().get("n") ?? undefined;
  return <Personalizar necessidadeId={n} />;
}

export default function Pagina() {
  return (
    <Suspense fallback={<Carregando />}>
      <Conteudo />
    </Suspense>
  );
}
