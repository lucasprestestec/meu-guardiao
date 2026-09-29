"use client";

import { useEffect, useState } from "react";

export type Ambiente = { modo_demonstracao: boolean; notificacoes_ativas: boolean };

let cache: Ambiente | null = null;

/** O que este ambiente realmente faz (demo? WhatsApp/e-mail ligados?). Vem da API. */
export function useAmbiente(): Ambiente | null {
  const [amb, setAmb] = useState<Ambiente | null>(cache);
  useEffect(() => {
    if (cache) return;
    fetch("/api/v1/saude")
      .then((r) => r.json())
      .then((d: Ambiente) => {
        cache = { modo_demonstracao: !!d.modo_demonstracao, notificacoes_ativas: !!d.notificacoes_ativas };
        setAmb(cache);
      })
      .catch(() => {
        /* sem API o resto da tela mostra o erro; o aviso simplesmente não aparece */
      });
  }, []);
  return amb;
}
