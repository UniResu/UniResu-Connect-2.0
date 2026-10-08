"use client";

import { useCallback, useEffect, useId, useRef, type ReactNode } from "react";
import styles from "./Modal.module.css";

const SELETOR_FOCAVEIS =
  'button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])';

/**
 * Caixa de diálogo acessível: fecha com Esc, com clique fora e pelos botões
 * de fechar; prende o foco dentro dela enquanto aberta e devolve o foco a
 * quem a abriu. O cabeçalho (título e botão de fechar) fica fixo e só o
 * conteúdo rola.
 *
 * - `tamanho="largo"` serve a conteúdos de leitura (ex.: o detalhe de um
 *   projeto em duas colunas); o padrão é a caixa estreita de avisos.
 * - `botaoRodape={false}` dispensa o botão "Entendi" do rodapé quando o
 *   conteúdo já traz as próprias ações.
 */
export default function Modal({
  aberto,
  titulo,
  onFechar,
  children,
  rotuloFechar = "Entendi",
  tamanho = "padrao",
  botaoRodape = true,
}: {
  aberto: boolean;
  titulo: string;
  onFechar: () => void;
  children: ReactNode;
  rotuloFechar?: string;
  tamanho?: "padrao" | "largo";
  botaoRodape?: boolean;
}) {
  const caixaRef = useRef<HTMLDivElement>(null);
  const idTitulo = useId();

  // Guardado em ref para o efeito abaixo depender só de `aberto`: assim o
  // foco não é movido de novo a cada render de quem usa o modal (ex.: ao
  // digitar em um formulário dentro dele).
  const onFecharRef = useRef(onFechar);
  useEffect(() => {
    onFecharRef.current = onFechar;
  }, [onFechar]);

  const focaveis = useCallback(() => {
    return Array.from(caixaRef.current?.querySelectorAll<HTMLElement>(SELETOR_FOCAVEIS) ?? []).filter(
      (el) => !el.hasAttribute("disabled")
    );
  }, []);

  useEffect(() => {
    if (!aberto) return;
    const anterior = document.activeElement as HTMLElement | null;
    // O foco inicial vai para a própria caixa (tabIndex -1): o leitor de tela
    // anuncia o título e o X não abre com o anel de foco aceso.
    caixaRef.current?.focus();

    function aoTeclar(e: KeyboardEvent) {
      if (e.key === "Escape") {
        e.preventDefault();
        onFecharRef.current();
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
  }, [aberto, focaveis]);

  if (!aberto) return null;

  return (
    <div
      className={styles.fundo}
      onMouseDown={(e) => {
        if (e.target === e.currentTarget) onFechar();
      }}
    >
      <div
        className={`${styles.caixa} ${tamanho === "largo" ? styles.caixaLarga : ""} animate-fade-in`}
        role="dialog"
        aria-modal="true"
        aria-labelledby={idTitulo}
        ref={caixaRef}
        tabIndex={-1}
      >
        <header className={styles.cabecalho}>
          <h2 id={idTitulo} className={styles.titulo}>
            {titulo}
          </h2>
          <button type="button" className={styles.fecharX} onClick={onFechar} aria-label="Fechar">
            <svg
              width="20"
              height="20"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="2"
              strokeLinecap="round"
              strokeLinejoin="round"
              aria-hidden="true"
            >
              <path d="M18 6 6 18" />
              <path d="m6 6 12 12" />
            </svg>
          </button>
        </header>
        <div className={styles.conteudo}>{children}</div>
        {botaoRodape && (
          <footer className={styles.rodape}>
            <button type="button" className="ui-btn ui-btn-primary" onClick={onFechar}>
              {rotuloFechar}
            </button>
          </footer>
        )}
      </div>
    </div>
  );
}
