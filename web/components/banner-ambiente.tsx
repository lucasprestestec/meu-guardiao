"use client";

import { AlertTriangle } from "lucide-react";
import { useAmbiente } from "@/lib/ambiente";

/** Aparece em todas as telas do cliente quando o ambiente é de demonstração. */
export function BannerAmbiente() {
  const amb = useAmbiente();
  if (!amb?.modo_demonstracao) return null;
  return (
    <div role="note" className="bg-amber-tint text-amber border-b border-[#f3dfb5]">
      <div className="mx-auto max-w-[1180px] px-5 py-2 flex items-start gap-2 text-[13px] font-semibold">
        <AlertTriangle size={16} className="shrink-0 mt-0.5" aria-hidden />
        <span>
          Demonstração: seguradoras e preços fictícios, sem valor comercial. Nada aqui gera uma apólice real
          {amb.notificacoes_ativas ? "." : ", e as mensagens de WhatsApp e e-mail ainda não são enviadas automaticamente."}
        </span>
      </div>
    </div>
  );
}
