"use client";

import { useCallback, useSyncExternalStore } from "react";
import { aplicarTema, temaAtual, temaDoSistema, temaSalvo, type Tema } from "@/lib/tema";
import styles from "./ThemeToggle.module.css";

/** Lê o tema do atributo data-theme do <html> e acompanha as mudanças dele. */
function useTema(): Tema {
  const subscribe = useCallback((aoMudar: () => void) => {
    const observador = new MutationObserver(aoMudar);
    observador.observe(document.documentElement, { attributes: true, attributeFilter: ["data-theme"] });
    // Sem escolha salva, acompanha o sistema em tempo real.
    const lista = window.matchMedia("(prefers-color-scheme: dark)");
    function aoMudarSistema() {
      if (!temaSalvo()) aplicarTema(temaDoSistema(), false);
    }
    lista.addEventListener("change", aoMudarSistema);
    return () => {
      observador.disconnect();
      lista.removeEventListener("change", aoMudarSistema);
    };
  }, []);
  // No servidor (e na hidratação) o tema é "claro"; o valor certo chega logo
  // depois, sem diferença de HTML.
  return useSyncExternalStore(subscribe, temaAtual, () => "light");
}

/**
 * Botão de alternar tema (sol/lua). Segue o sistema até a pessoa escolher;
 * depois disso a escolha fica salva no navegador.
 */
export default function ThemeToggle({ className = "", rotulado = false }: { className?: string; rotulado?: boolean }) {
  const tema = useTema();
  const escuro = tema === "dark";
  const rotulo = escuro ? "Mudar para o tema claro" : "Mudar para o tema escuro";

  return (
    <button
      type="button"
      className={`${styles.botao} ${rotulado ? styles.rotulado : ""} ${className}`}
      onClick={() => aplicarTema(escuro ? "light" : "dark")}
      aria-label={rotulo}
      title={rotulo}
      aria-pressed={escuro}
    >
      <span className={styles.icone} aria-hidden="true">
        {escuro ? (
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <circle cx="12" cy="12" r="4" />
            <path d="M12 2v2M12 20v2M4.93 4.93l1.41 1.41M17.66 17.66l1.41 1.41M2 12h2M20 12h2M4.93 19.07l1.41-1.41M17.66 6.34l1.41-1.41" />
          </svg>
        ) : (
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z" />
          </svg>
        )}
      </span>
      {rotulado && <span>{escuro ? "Tema claro" : "Tema escuro"}</span>}
    </button>
  );
}
