"use client";

import { useEffect, useId, useRef, useState } from "react";
import styles from "./MultiSelect.module.css";

export interface OpcaoMulti {
  valor: string;
  rotulo: string;
  total?: number;
}

/**
 * Seleção múltipla com cara de select: um botão que abre uma lista de
 * checkboxes. Fecha com Esc e com clique fora; o botão resume a escolha.
 */
export default function MultiSelect({
  rotulo,
  placeholder,
  opcoes,
  selecionados,
  onChange,
  disabled = false,
  className = "",
}: {
  rotulo: string;
  placeholder: string;
  opcoes: OpcaoMulti[];
  selecionados: string[];
  onChange: (valores: string[]) => void;
  disabled?: boolean;
  className?: string;
}) {
  const [aberto, setAberto] = useState(false);
  const raiz = useRef<HTMLDivElement>(null);
  const idLista = useId();

  useEffect(() => {
    if (!aberto) return;
    function foraOuEsc(e: MouseEvent | KeyboardEvent) {
      if (e instanceof KeyboardEvent) {
        if (e.key === "Escape") setAberto(false);
        return;
      }
      if (raiz.current && !raiz.current.contains(e.target as Node)) setAberto(false);
    }
    document.addEventListener("mousedown", foraOuEsc);
    document.addEventListener("keydown", foraOuEsc);
    return () => {
      document.removeEventListener("mousedown", foraOuEsc);
      document.removeEventListener("keydown", foraOuEsc);
    };
  }, [aberto]);

  function alternar(valor: string) {
    onChange(selecionados.includes(valor) ? selecionados.filter((v) => v !== valor) : [...selecionados, valor]);
  }

  const resumo =
    selecionados.length === 0
      ? placeholder
      : selecionados.length === 1
        ? opcoes.find((o) => o.valor === selecionados[0])?.rotulo ?? selecionados[0]
        : `${rotulo}: ${selecionados.length} selecionados`;

  return (
    <div className={`${styles.raiz} ${className}`} ref={raiz}>
      <button
        type="button"
        className={`${styles.botao} ${selecionados.length ? styles.botaoAtivo : ""}`}
        onClick={() => setAberto((v) => !v)}
        disabled={disabled}
        aria-haspopup="listbox"
        aria-expanded={aberto}
        aria-controls={idLista}
        aria-label={rotulo}
        title={selecionados.length > 1 ? selecionados.join(", ") : undefined}
      >
        <span className={styles.resumo}>{resumo}</span>
        <span className={styles.seta} aria-hidden="true">▾</span>
      </button>
      {aberto && !disabled && (
        <div className={styles.lista} id={idLista} role="listbox" aria-multiselectable="true" aria-label={rotulo}>
          {selecionados.length > 0 && (
            <button type="button" className={styles.limpar} onClick={() => onChange([])}>
              Limpar seleção
            </button>
          )}
          {opcoes.map((o) => {
            const marcado = selecionados.includes(o.valor);
            return (
              <label key={o.valor} className={styles.opcao} role="option" aria-selected={marcado}>
                <input type="checkbox" checked={marcado} onChange={() => alternar(o.valor)} />
                <span className={styles.opcaoRotulo}>{o.rotulo}</span>
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
