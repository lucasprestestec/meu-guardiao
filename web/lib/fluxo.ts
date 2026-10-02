"use client";

import { useCallback, useEffect, useState } from "react";
import type { Comparacao } from "./api";

// Estado da jornada do cliente. Vive no sessionStorage: sobrevive a recarregar
// a página, some ao fechar a aba. Nada sensível é guardado aqui (sem CPF).
export type Perfil = { idade: number; sexo: "M" | "F"; fumante: boolean };

export type Fluxo = {
  perfil?: Perfil;
  necessidadeId?: string;
  capitais?: Record<string, number>;
  comparacao?: Comparacao;
  escolhida?: string; // produto_versao_id
  selecionadas?: string[]; // para comparar lado a lado
  recado?: string; // recado livre para o especialista (tela de personalização)
  /** Contato capturado antes do Mapa. Pré-preenche o pedido ao especialista e o checkout. */
  contato?: { nome: string; email: string; celular: string; leadId?: string };
};

/** Identifica a sessão do navegador no funil (sem dado pessoal). */
export function sessaoDoFunil(): string {
  try {
    let s = sessionStorage.getItem("dor.sessao");
    if (!s) {
      s = crypto.randomUUID();
      sessionStorage.setItem("dor.sessao", s);
    }
    return s;
  } catch {
    return "sem-storage-" + Math.random().toString(36).slice(2, 10);
  }
}

/** Evento do funil: dispara e esquece. Falha de rede nunca atrapalha o cliente. */
export function registrarEvento(etapa: string) {
  fetch("/api/v1/eventos", {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify({ etapa, sessao: sessaoDoFunil() }),
    keepalive: true,
  }).catch(() => {});
}

const CHAVE = "dor.fluxo";

export function lerFluxo(): Fluxo {
  try {
    return JSON.parse(sessionStorage.getItem(CHAVE) ?? "{}");
  } catch {
    return {};
  }
}

export function gravarFluxo(parcial: Fluxo) {
  try {
    sessionStorage.setItem(CHAVE, JSON.stringify({ ...lerFluxo(), ...parcial }));
  } catch {
    /* navegação privada sem storage: a jornada segue sem persistência */
  }
}

export function limparFluxo() {
  try {
    sessionStorage.removeItem(CHAVE);
  } catch {
    /* ignore */
  }
}

/** `pronto` é false até o storage ser lido no cliente (evita piscar "vazio"). */
export function useFluxo() {
  const [fluxo, setFluxo] = useState<Fluxo>({});
  const [pronto, setPronto] = useState(false);
  useEffect(() => {
    setFluxo(lerFluxo());
    setPronto(true);
  }, []);
  const atualizar = useCallback((parcial: Fluxo) => {
    gravarFluxo(parcial);
    setFluxo((f) => ({ ...f, ...parcial }));
  }, []);
  return { fluxo, pronto, atualizar };
}
