"use client";

import { useCallback, useSyncExternalStore } from "react";

/**
 * Lê uma media query do CSS como estado do React.
 *
 * No servidor, e também durante a hidratação, o hook devolve `valorServidor`,
 * para que a árvore gerada pelo servidor seja igual à primeira renderização
 * do cliente. Logo depois da hidratação o React consulta o `matchMedia` e,
 * se o valor for outro, renderiza de novo, sem erro de hidratação. Mudanças
 * posteriores (girar o celular, redimensionar a janela) chegam pelo evento
 * `change` da própria media query.
 */
export function useMediaQuery(query: string, valorServidor = false): boolean {
  const subscribe = useCallback(
    (aoMudar: () => void) => {
      const lista = window.matchMedia(query);
      lista.addEventListener("change", aoMudar);
      return () => lista.removeEventListener("change", aoMudar);
    },
    [query]
  );
  const getSnapshot = useCallback(() => window.matchMedia(query).matches, [query]);
  const getServerSnapshot = useCallback(() => valorServidor, [valorServidor]);

  return useSyncExternalStore(subscribe, getSnapshot, getServerSnapshot);
}
