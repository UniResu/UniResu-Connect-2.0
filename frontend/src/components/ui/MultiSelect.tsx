"use client";

import { useEffect, useId, useRef, useState } from "react";
import styles from "./MultiSelect.module.css";

export interface OpcaoMulti {
  valor: string;
  rotulo: string;
  total?: number;
}

/**
 * Seleção múltipla com cara de select: um botão (com a mesma altura e borda
 * dos campos `ui-field`) que abre um popover de checkboxes.
 *
 * - `rotuloTodos` acrescenta a primeira opção "Todos os campi" (ou o texto
 *   dado), que marca tudo; se tudo já está marcado, desmarca tudo.
 * - "Limpar seleção" aparece sempre que há algo marcado.
 * - Fecha com Esc (o foco volta ao botão), com clique fora e ao sair com Tab.
 * - O botão resume a escolha: o nome, quando é um só; "Campus: 3
 *   selecionados" a partir de dois.
 */
export default function MultiSelect({
  rotulo,
  placeholder,
  opcoes,
  selecionados,
  onChange,
  disabled = false,
  className = "",
  rotuloTodos,
}: {
  rotulo: string;
  placeholder: string;
  opcoes: OpcaoMulti[];
  selecionados: string[];
  onChange: (valores: string[]) => void;
  disabled?: boolean;
  className?: string;
  /** Texto da opção que seleciona tudo (ex.: "Todos os campi"). Sem ele, a opção não aparece. */
  rotuloTodos?: string;
}) {
  const [aberto, setAberto] = useState(false);
  const raiz = useRef<HTMLDivElement>(null);
  const botaoRef = useRef<HTMLButtonElement>(null);
  const todosRef = useRef<HTMLInputElement>(null);
  // Clique com o mouse dentro do componente: o Safari não leva o foco a
  // botões e checkboxes, então o blur resultante não deve fechar a lista.
  const cliqueDentro = useRef(false);
  const idLista = useId();

  const todosMarcados = opcoes.length > 0 && opcoes.every((o) => selecionados.includes(o.valor));
  const algumMarcado = selecionados.length > 0;

  useEffect(() => {
    if (!aberto) return;
    function aoClicarFora(e: MouseEvent) {
      if (raiz.current && !raiz.current.contains(e.target as Node)) setAberto(false);
    }
    function aoTeclar(e: KeyboardEvent) {
      if (e.key !== "Escape") return;
      setAberto(false);
      botaoRef.current?.focus();
    }
    document.addEventListener("mousedown", aoClicarFora);
    document.addEventListener("keydown", aoTeclar);
    return () => {
      document.removeEventListener("mousedown", aoClicarFora);
      document.removeEventListener("keydown", aoTeclar);
    };
  }, [aberto]);

  // O estado "parcialmente marcado" do checkbox "Todos" só existe pelo DOM.
  useEffect(() => {
    if (todosRef.current) todosRef.current.indeterminate = algumMarcado && !todosMarcados;
  }, [aberto, algumMarcado, todosMarcados]);

  function alternar(valor: string) {
    onChange(selecionados.includes(valor) ? selecionados.filter((v) => v !== valor) : [...selecionados, valor]);
  }

  function alternarTodos() {
    onChange(todosMarcados ? [] : opcoes.map((o) => o.valor));
  }

  const resumo =
    selecionados.length === 0
      ? placeholder
      : selecionados.length === 1
        ? (opcoes.find((o) => o.valor === selecionados[0])?.rotulo ?? selecionados[0])
        : `${rotulo}: ${selecionados.length} selecionados`;
  const nomeAcessivel = selecionados.length > 1 ? resumo : `${rotulo}: ${resumo}`;

  return (
    <div
      className={`${styles.raiz} ${className}`}
      ref={raiz}
      onMouseDown={() => {
        cliqueDentro.current = true;
      }}
      onMouseUp={() => {
        cliqueDentro.current = false;
      }}
      onBlur={(e) => {
        // Saiu do componente com Tab: fecha sem roubar o foco.
        if (cliqueDentro.current || !aberto) return;
        if (!raiz.current?.contains(e.relatedTarget as Node | null)) setAberto(false);
      }}
    >
      <button
        ref={botaoRef}
        type="button"
        className={`ui-field ${styles.botao} ${algumMarcado ? styles.botaoAtivo : ""}`}
        onClick={() => setAberto((v) => !v)}
        disabled={disabled}
        aria-expanded={aberto}
        aria-controls={aberto ? idLista : undefined}
        aria-label={nomeAcessivel}
        title={selecionados.length > 1 ? selecionados.join(", ") : undefined}
      >
        <span className={styles.resumo}>{resumo}</span>
        <svg
          className={`${styles.seta} ${aberto ? styles.setaAberta : ""}`}
          width="16"
          height="16"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          strokeWidth="2"
          strokeLinecap="round"
          strokeLinejoin="round"
          aria-hidden="true"
        >
          <path d="m6 9 6 6 6-6" />
        </svg>
      </button>

      {aberto && !disabled && (
        <div className={styles.lista} id={idLista} role="group" aria-label={rotulo}>
          {opcoes.length > 0 && (rotuloTodos || algumMarcado) && (
            <div className={styles.cabecalhoLista}>
              {rotuloTodos ? (
                <label className={`${styles.opcao} ${styles.opcaoTodos}`}>
                  <input ref={todosRef} type="checkbox" checked={todosMarcados} onChange={alternarTodos} />
                  <span className={styles.opcaoRotulo}>{rotuloTodos}</span>
                  <span className={styles.total}>{opcoes.length}</span>
                </label>
              ) : (
                <span className={styles.cabecalhoVazio} />
              )}
              {algumMarcado && (
                <button type="button" className="ui-btn ui-btn-ghost ui-btn-sm" onClick={() => onChange([])}>
                  Limpar seleção
                </button>
              )}
            </div>
          )}
          {opcoes.map((o) => {
            const marcado = selecionados.includes(o.valor);
            return (
              <label key={o.valor} className={styles.opcao}>
                <input type="checkbox" checked={marcado} onChange={() => alternar(o.valor)} />
                <span className={styles.opcaoRotulo} title={o.rotulo}>
                  {o.rotulo}
                </span>
                {o.total !== undefined && <span className={styles.total}>{o.total}</span>}
              </label>
            );
          })}
          {opcoes.length === 0 && <p className={styles.vazio}>Nenhuma opção no recorte atual.</p>}
        </div>
      )}
    </div>
  );
}
