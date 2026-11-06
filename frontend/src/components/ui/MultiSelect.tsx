"use client";

import { useEffect, useId, useRef, useState } from "react";
import styles from "./MultiSelect.module.css";

export interface OpcaoMulti {
  valor: string;
  rotulo: string;
  total?: number;
}

/** A partir de quantas opções a lista ganha a caixa de busca (as curtas se leem de relance). */
const MIN_OPCOES_BUSCA = 8;

/** Minúsculas e sem acentos: "Saúde" e "saude" se encontram. */
function normalizar(texto: string) {
  return texto.normalize("NFD").replace(/[̀-ͯ]/g, "").toLowerCase();
}

/**
 * Seleção múltipla com cara de select: um botão (com a mesma altura e borda
 * dos campos `ui-field`) que abre um popover de checkboxes.
 *
 * - `rotuloTodos` acrescenta a primeira opção "Todos os campi" (ou o texto
 *   dado), que marca tudo; se tudo já está marcado, desmarca tudo.
 * - Listas longas (unidades de uma universidade chegam a mais de cem) têm uma
 *   caixa de busca no topo: cada palavra digitada precisa aparecer no nome,
 *   sem diferenciar acentos nem maiúsculas. Durante a busca, a opção de cima
 *   marca só os resultados.
 * - "Limpar seleção" aparece sempre que há algo marcado.
 * - Fecha com Esc (o foco volta ao botão), com clique fora e ao sair com Tab;
 *   ao fechar, a busca é apagada.
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
  const [busca, setBusca] = useState("");
  // Altura da lista medida ao abrir: o painel de filtros fica preso na tela,
  // e uma lista mais alta que o espaço abaixo do botão teria o fim inalcançável.
  const [alturaLista, setAlturaLista] = useState<number | undefined>(undefined);
  const raiz = useRef<HTMLDivElement>(null);
  const botaoRef = useRef<HTMLButtonElement>(null);
  const todosRef = useRef<HTMLInputElement>(null);
  const buscaRef = useRef<HTMLInputElement>(null);
  // Clique com o mouse dentro do componente: o Safari não leva o foco a
  // botões e checkboxes, então o blur resultante não deve fechar a lista.
  const cliqueDentro = useRef(false);
  const idLista = useId();

  const temBusca = opcoes.length > MIN_OPCOES_BUSCA;
  const termos = temBusca ? normalizar(busca).split(/\s+/).filter(Boolean) : [];
  const buscando = termos.length > 0;
  const visiveis = buscando
    ? opcoes.filter((o) => {
        const rotuloOpcao = normalizar(o.rotulo);
        return termos.every((t) => rotuloOpcao.includes(t));
      })
    : opcoes;

  const todosMarcados = opcoes.length > 0 && opcoes.every((o) => selecionados.includes(o.valor));
  const algumMarcado = selecionados.length > 0;
  // A opção de cima vale para a lista inteira ou, durante a busca, só para os resultados.
  const visiveisMarcados = visiveis.length > 0 && visiveis.every((o) => selecionados.includes(o.valor));
  const algumVisivelMarcado = visiveis.some((o) => selecionados.includes(o.valor));
  const cabecalhoMarcado = buscando ? visiveisMarcados : todosMarcados;
  const cabecalhoParcial = buscando ? algumVisivelMarcado && !visiveisMarcados : algumMarcado && !todosMarcados;

  function fechar() {
    setAberto(false);
    setBusca("");
  }

  function abrir() {
    const caixa = botaoRef.current?.getBoundingClientRect();
    if (caixa) {
      const espacoAbaixo = window.innerHeight - caixa.bottom - 16;
      setAlturaLista(Math.max(220, Math.min(temBusca ? 400 : 340, espacoAbaixo)));
    }
    setAberto(true);
  }

  useEffect(() => {
    if (!aberto) return;
    function aoClicarFora(e: MouseEvent) {
      if (raiz.current && !raiz.current.contains(e.target as Node)) {
        setAberto(false);
        setBusca("");
      }
    }
    function aoTeclar(e: KeyboardEvent) {
      if (e.key !== "Escape") return;
      setAberto(false);
      setBusca("");
      botaoRef.current?.focus();
    }
    document.addEventListener("mousedown", aoClicarFora);
    document.addEventListener("keydown", aoTeclar);
    return () => {
      document.removeEventListener("mousedown", aoClicarFora);
      document.removeEventListener("keydown", aoTeclar);
    };
  }, [aberto]);

  // Com mouse e teclado, o foco vai direto para a busca. Na tela de toque
  // não: o teclado subiria e cobriria metade da lista antes de a pessoa decidir.
  useEffect(() => {
    if (aberto && temBusca && window.matchMedia("(pointer: fine)").matches) buscaRef.current?.focus();
  }, [aberto, temBusca]);

  // O estado "parcialmente marcado" do checkbox "Todos" só existe pelo DOM.
  useEffect(() => {
    if (todosRef.current) todosRef.current.indeterminate = cabecalhoParcial;
  }, [aberto, cabecalhoParcial]);

  function alternar(valor: string) {
    onChange(selecionados.includes(valor) ? selecionados.filter((v) => v !== valor) : [...selecionados, valor]);
  }

  function alternarTodos() {
    if (buscando) {
      const doRecorte = visiveis.map((o) => o.valor);
      onChange(
        visiveisMarcados
          ? selecionados.filter((v) => !doRecorte.includes(v))
          : [...selecionados, ...doRecorte.filter((v) => !selecionados.includes(v))]
      );
      return;
    }
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
        if (!raiz.current?.contains(e.relatedTarget as Node | null)) fechar();
      }}
    >
      <button
        ref={botaoRef}
        type="button"
        className={`ui-field ${styles.botao} ${algumMarcado ? styles.botaoAtivo : ""}`}
        onClick={() => (aberto ? fechar() : abrir())}
        disabled={disabled}
        aria-expanded={aberto}
        aria-controls={aberto ? idLista : undefined}
        aria-label={nomeAcessivel}
        title={selecionados.length > 1 ? selecionados.join(", ") : algumMarcado ? resumo : undefined}
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
        <div
          className={`${styles.lista} ${temBusca ? styles.listaComBusca : ""}`}
          style={{ maxHeight: alturaLista }}
          id={idLista}
          role="group"
          aria-label={rotulo}
        >
          {temBusca && (
            <div className={styles.busca}>
              <input
                ref={buscaRef}
                type="search"
                value={busca}
                onChange={(e) => setBusca(e.target.value)}
                // Enter aqui não envia o formulário dos filtros.
                onKeyDown={(e) => {
                  if (e.key === "Enter") e.preventDefault();
                }}
                placeholder={`Buscar ${rotulo.toLowerCase()}`}
                aria-label={`Buscar em ${rotulo.toLowerCase()}`}
                className={`ui-field ${styles.campoBusca}`}
                autoComplete="off"
                spellCheck={false}
              />
            </div>
          )}
          {visiveis.length > 0 && (rotuloTodos || algumMarcado) && (
            <div className={styles.cabecalhoLista}>
              {rotuloTodos ? (
                <label className={`${styles.opcao} ${styles.opcaoTodos}`}>
                  <input ref={todosRef} type="checkbox" checked={cabecalhoMarcado} onChange={alternarTodos} />
                  <span className={styles.opcaoRotulo}>
                    {buscando ? (visiveis.length === 1 ? "O resultado" : "Todos os resultados") : rotuloTodos}
                  </span>
                  <span className={styles.total}>{visiveis.length}</span>
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
          {buscando && visiveis.length === 0 && (
            <p className={styles.vazio}>Nada encontrado para &ldquo;{busca.trim()}&rdquo;.</p>
          )}
          {visiveis.map((o) => {
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
