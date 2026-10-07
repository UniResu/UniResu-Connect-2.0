"use client";

import { useCallback, useEffect, useRef, type ReactNode } from "react";
import styles from "./Modal.module.css";

/**
 * Caixa de diálogo acessível: fecha com Esc, com clique fora e pelo botão;
 * prende o foco dentro dela enquanto aberta e devolve o foco a quem a abriu.
 */
export default function Modal({
  aberto,
  titulo,
  onFechar,
  children,
  rotuloFechar = "Entendi",
}: {
  aberto: boolean;
  titulo: string;
  onFechar: () => void;
  children: ReactNode;
  rotuloFechar?: string;
}) {
  const caixaRef = useRef<HTMLDivElement>(null);

  const focaveis = useCallback(() => {
    const seletor = 'button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])';
    return Array.from(caixaRef.current?.querySelectorAll<HTMLElement>(seletor) ?? []).filter(
      (el) => !el.hasAttribute("disabled")
    );
  }, []);

  useEffect(() => {
    if (!aberto) return;
    const anterior = document.activeElement as HTMLElement | null;
    focaveis()[0]?.focus();

    function aoTeclar(e: KeyboardEvent) {
      if (e.key === "Escape") {
        e.preventDefault();
        onFechar();
        return;
      }
      if (e.key !== "Tab") return;
      const lista = focaveis();
      if (lista.length === 0) return;
      const indice = lista.indexOf(document.activeElement as HTMLElement);
      if (e.shiftKey && indice <= 0) {
        e.preventDefault();
        lista[lista.length - 1].focus();
      } else if (!e.shiftKey && indice === lista.length - 1) {
        e.preventDefault();
        lista[0].focus();
      }
    }

    document.addEventListener("keydown", aoTeclar);
    const overflowAnterior = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    return () => {
      document.removeEventListener("keydown", aoTeclar);
      document.body.style.overflow = overflowAnterior;
      anterior?.focus();
    };
  }, [aberto, onFechar, focaveis]);

  if (!aberto) return null;

  return (
    <div
      className={styles.fundo}
      onMouseDown={(e) => {
        if (e.target === e.currentTarget) onFechar();
      }}
    >
      <div className={styles.caixa} role="dialog" aria-modal="true" aria-labelledby="modal-titulo" ref={caixaRef}>
        <h2 id="modal-titulo" className={styles.titulo}>{titulo}</h2>
        <div className={styles.conteudo}>{children}</div>
        <button type="button" className={styles.fechar} onClick={onFechar}>
          {rotuloFechar}
        </button>
      </div>
    </div>
  );
}
