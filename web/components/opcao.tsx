"use client";

import Link from "next/link";
import { CircleDollarSign, ShieldCheck, Star } from "lucide-react";
import { Selo } from "@/components/ui";
import type { Comparacao } from "@/lib/api";

/** Aviso junto ao preço: o valor é estimativa, já com IOF, e a seguradora pode ajustá-lo
 *  depois da avaliação de saúde (na Azos a cotação sobe quando as respostas agravam o risco). */
export function AvisoPreco({ className = "" }: { className?: string }) {
  return (
    <p className={`text-[13px] text-muted ${className}`}>
      Valor estimado, com IOF. Pode mudar depois da avaliação de saúde feita pela seguradora.
    </p>
  );
}

export function Selos({ id, destaques }: { id: string; destaques: Comparacao["destaques"] }) {
  return (
    <div className="flex flex-wrap gap-2">
      {destaques.recomendado === id && (
        <Selo tom="teal">
          <Star size={13} fill="currentColor" aria-hidden /> Recomendada
        </Selo>
      )}
      {destaques.menor_preco === id && (
        <Selo tom="blue">
          <CircleDollarSign size={13} aria-hidden /> Menor preço
        </Selo>
      )}
      {destaques.maior_protecao === id && (
        <Selo tom="amber">
          <ShieldCheck size={13} aria-hidden /> Maior proteção
        </Selo>
      )}
    </div>
  );
}

export function SemComparacao() {
  return (
    <div className="mx-auto max-w-[640px] px-5 py-20 text-center space-y-5">
      <h1 className="titulo text-4xl">
        Nenhuma comparação <em>em andamento</em>
      </h1>
      <p className="text-body text-lg">Faça o diagnóstico ou monte sua proteção para ver as opções.</p>
      <div className="flex justify-center gap-3 flex-wrap">
        <Link href="/diagnostico" className="btn btn-primary">Descobrir quanto preciso</Link>
        <Link href="/montar" className="btn btn-secondary">Montar minha proteção</Link>
      </div>
    </div>
  );
}
