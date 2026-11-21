"use client";

import { useId, useState, type ReactNode } from "react";
import { IconeAjuda, IconeCapelo, IconeCheck } from "@/components/ui/Icones";
import { PREFIXO_FAP, ROTULOS_FINANCIAMENTO, rotuloFinanciamento } from "@/types/projeto";
import styles from "../projetos.module.css";

export interface OpcaoFinanciamento {
  valor: string;
  total: number;
}

/** Contagens de /api/projetos/filtros para o recorte atual. */
export interface FinanciamentoFiltro {
  categorias: OpcaoFinanciamento[];
  faps: OpcaoFinanciamento[];
  total_bolsas: number;
}

// A FAP fica por último: as FAPs pelo nome aparecem logo abaixo dela.
const QUEM_FINANCIA = ["capes", "cnpq", "instituicao", "fap"];

/**
 * O que vai para a API: com FAPs escolhidas pelo nome, elas entram no lugar
 * de "fap" (que vale para todas).
 */
export function valoresFinanciamento(selecionados: string[]) {
  return selecionados.some((v) => v.startsWith(PREFIXO_FAP)) ? selecionados.filter((v) => v !== "fap") : selecionados;
}

/** Texto da etiqueta de filtro em uso, acima da lista de resultados. */
export function rotuloEtiquetaFinanciamento(valor: string) {
  if (valor === "bolsa") return ROTULOS_FINANCIAMENTO.bolsa;
  if (valor === "instituicao") return "Financiamento: própria universidade";
  return `Financiamento: ${rotuloFinanciamento(valor)}`;
}

/**
 * Filtro "Projetos financiados": etiquetas que se marcam e desmarcam, várias
 * de uma vez (vale qualquer uma). "Bolsa para alunos" é a única que confirma
 * bolsa; as outras dizem quem financia o projeto. Marcar "FAP" abre a escolha
 * da fundação estadual, pelo nome. O ponto de interrogação explica a diferença.
 */
export default function FiltroFinanciados({
  opcoes,
  selecionados,
  onChange,
}: {
  opcoes: FinanciamentoFiltro | null;
  selecionados: string[];
  onChange: (valores: string[]) => void;
}) {
  const [ajudaAberta, setAjudaAberta] = useState(false);
  const idTitulo = useId();
  const idAjuda = useId();

  const totalDe = (valor: string) => opcoes?.categorias.find((c) => c.valor === valor)?.total;
  const fapsEscolhidas = selecionados.filter((v) => v.startsWith(PREFIXO_FAP));
  // FAPs do recorte, mais as escolhidas que saíram dele (para poder desmarcá-las).
  const faps = [...(opcoes?.faps ?? [])];
  for (const valor of fapsEscolhidas) {
    if (!faps.some((f) => f.valor === valor)) faps.push({ valor, total: 0 });
  }
  const totalBolsa = totalDe("bolsa") ?? 0;
  const semNenhum =
    opcoes !== null && selecionados.length === 0 && opcoes.categorias.every((c) => c.total === 0);

  function alternar(valor: string) {
    if (!selecionados.includes(valor)) {
      onChange([...selecionados, valor]);
      return;
    }
    // Desmarcar "FAP" leva junto as FAPs escolhidas pelo nome.
    onChange(selecionados.filter((v) => v !== valor && !(valor === "fap" && v.startsWith(PREFIXO_FAP))));
  }

  function etiqueta(valor: string, rotulo: string, total: number | undefined, icone?: ReactNode) {
    const marcada = selecionados.includes(valor);
    return (
      <button
        key={valor}
        type="button"
        className={styles.tag}
        aria-pressed={marcada}
        disabled={total === 0 && !marcada}
        onClick={() => alternar(valor)}
      >
        {marcada ? <IconeCheck tamanho={14} /> : icone}
        <span>{rotulo}</span>
        {total !== undefined && <span className={styles.tagTotal}>{total}</span>}
      </button>
    );
  }

  return (
    <div className={styles.campoFiltro}>
      <div className={styles.rotuloLinha}>
        <span id={idTitulo} className={styles.rotuloFiltro}>
          Projetos financiados
        </span>
        <button
          type="button"
          className={styles.ajuda}
          onClick={() => setAjudaAberta((aberta) => !aberta)}
          aria-expanded={ajudaAberta}
          aria-controls={ajudaAberta ? idAjuda : undefined}
          aria-label="Como ler o filtro Projetos financiados"
          title="Como ler este filtro"
        >
          <IconeAjuda tamanho={16} />
        </button>
      </div>
      {ajudaAberta && (
        <p id={idAjuda} className={styles.ajudaTexto}>
          Só a opção <strong>Bolsa para alunos</strong> confirma bolsa: são ações de extensão em que a universidade
          informa as bolsas concedidas. As demais mostram quem financia o projeto (FAP é a fundação de amparo à
          pesquisa do estado), o que não garante bolsa a quem entra.
        </p>
      )}

      <div className={styles.financiados} role="group" aria-labelledby={idTitulo}>
        <div className={styles.tags}>
          {etiqueta("bolsa", ROTULOS_FINANCIAMENTO.bolsa, totalDe("bolsa"), <IconeCapelo tamanho={14} />)}
        </div>
        {totalBolsa > 0 && opcoes && opcoes.total_bolsas > 0 && (
          <p className={styles.notaBolsas}>
            {opcoes.total_bolsas === 1 ? "1 bolsa concedida" : `${opcoes.total_bolsas} bolsas concedidas`}{" "}
            {totalBolsa === 1 ? "em 1 projeto" : `em ${totalBolsa} projetos`}
          </p>
        )}

        <span className={styles.subRotulo}>Quem financia</span>
        <div className={styles.tags}>
          {QUEM_FINANCIA.map((valor) => etiqueta(valor, ROTULOS_FINANCIAMENTO[valor], totalDe(valor)))}
        </div>

        {selecionados.includes("fap") && faps.length > 0 && (
          <div className={styles.subTags} role="group" aria-label="Qual FAP">
            <button
              type="button"
              className={styles.tag}
              aria-pressed={fapsEscolhidas.length === 0}
              onClick={() => onChange(selecionados.filter((v) => !v.startsWith(PREFIXO_FAP)))}
            >
              {fapsEscolhidas.length === 0 && <IconeCheck tamanho={14} />}
              <span>Todas as FAPs</span>
            </button>
            {faps.map((f) => etiqueta(f.valor, rotuloFinanciamento(f.valor), f.total))}
          </div>
        )}

        {semNenhum && <p className={styles.notaBolsas}>Nenhum projeto financiado no recorte atual.</p>}
      </div>
    </div>
  );
}
