"use client";

import { memo, type ReactNode } from "react";
import Link from "next/link";
import {
  formatarSituacao,
  moduloDoProjeto,
  tomDaSituacao,
  type Projeto,
} from "@/types/projeto";
import {
  IconeBalanca,
  IconeBroto,
  IconeCalendario,
  IconeCoracao,
  IconeEngrenagem,
  IconeFolha,
  IconeFrasco,
  IconeGlobo,
  IconeGrade,
  IconeLivro,
  IconePaleta,
  IconePin,
  IconePredio,
} from "@/components/ui/Icones";
import styles from "./ProjetoCard.module.css";

/**
 * Grande área do CNPq: cada uma com um tom e um ícone próprios, para a tag
 * ser reconhecida de relance. Instituição, campus e unidade ficam neutros de
 * propósito: são muitos valores, e cor neles viraria ruído.
 */
const AREAS: Record<string, { classe: string; icone: ReactNode }> = {
  "Ciências Exatas e da Terra": { classe: "ui-chip-indigo", icone: <IconeFrasco /> },
  "Ciências Biológicas": { classe: "ui-chip-green", icone: <IconeFolha /> },
  Engenharias: { classe: "ui-chip-orange", icone: <IconeEngrenagem /> },
  "Ciências da Saúde": { classe: "ui-chip-rose", icone: <IconeCoracao /> },
  "Ciências Agrárias": { classe: "ui-chip-amber", icone: <IconeBroto /> },
  "Ciências Sociais Aplicadas": { classe: "ui-chip-sky", icone: <IconeBalanca /> },
  "Ciências Humanas": { classe: "ui-chip-violet", icone: <IconeLivro /> },
  "Linguística, Letras e Artes": { classe: "ui-chip-teal", icone: <IconePaleta /> },
  Multidisciplinar: { classe: "ui-chip-slate", icone: <IconeGrade /> },
};

export function estiloDaArea(area?: string) {
  return (area && AREAS[area]) || { classe: "ui-chip-primary", icone: null };
}

/**
 * Card de projeto, o mesmo na busca e na página inicial.
 *
 * Hierarquia: tipo e situação no topo, título, quem coordena, resumo em
 * duas linhas e, no rodapé, as tags do mais geral ao mais específico
 * (área, instituição, campus, unidade, ano, remoto). Clica-se no card
 * inteiro: `onClick` abre o modal na busca; `href` leva a outra página.
 */
function ProjetoCardBase({
  projeto,
  onClick,
  href,
  compacto = false,
}: {
  projeto: Projeto;
  onClick?: (projeto: Projeto) => void;
  href?: string;
  /** Na página inicial: menos tags e sem o resumo completo. */
  compacto?: boolean;
}) {
  const modulo = moduloDoProjeto(projeto);
  const tom = tomDaSituacao(projeto.situacao);
  const situacao = formatarSituacao(projeto.situacao);
  const area = estiloDaArea(projeto.area_conhecimento);

  const conteudo = (
    <>
      <div className={styles.topo}>
        {projeto.tipo && (
          <span
            className={`${styles.tipo} ${
              modulo === "pesquisa" ? styles.tipoPesquisa : modulo === "extensao" ? styles.tipoExtensao : ""
            }`}
          >
            {projeto.tipo}
          </span>
        )}
        {situacao ? (
          <span className={`${styles.situacao} ${styles[`tom_${tom}`]}`}>
            <span className={styles.ponto} aria-hidden="true" />
            {situacao}
          </span>
        ) : projeto.dataPublicacao ? (
          <span className={styles.data}>{projeto.dataPublicacao}</span>
        ) : null}
      </div>

      <h3 className={styles.titulo}>{projeto.titulo}</h3>

      {projeto.nome_professor && (
        <p className={styles.coordenacao}>
          <span className={styles.coordenacaoRotulo}>Coordenação</span>
          {projeto.nome_professor}
        </p>
      )}

      {projeto.descricao && !compacto && <p className={styles.resumo}>{projeto.descricao}</p>}

      <div className={styles.tags}>
        {projeto.area_conhecimento && (
          <span className={`ui-chip ${area.classe}`} title="Área do conhecimento (grande área do CNPq)">
            {area.icone}
            {projeto.area_conhecimento}
          </span>
        )}
        {projeto.instituicao && (
          <span
            className={`ui-chip ${projeto.origem ? "ui-chip-outline" : `ui-chip-truncate ${styles.tagLonga}`}`}
            title={projeto.instituicao}
          >
            {projeto.instituicao}
          </span>
        )}
        {projeto.campus && !compacto && (
          <span className={`ui-chip ${styles.tagLonga}`} title={`Campus ${projeto.campus}`}>
            <IconePin />
            <span className={styles.tagTexto}>{projeto.campus}</span>
          </span>
        )}
        {projeto.unidade && !compacto && (
          <span className={`ui-chip ${styles.tagLonga}`} title={projeto.unidade}>
            <IconePredio />
            <span className={styles.tagTexto}>{projeto.unidade}</span>
          </span>
        )}
        {projeto.ano && (
          <span className="ui-chip">
            <IconeCalendario />
            {projeto.ano}
          </span>
        )}
        {projeto.e_remoto && (
          <span className="ui-chip ui-chip-success">
            <IconeGlobo />
            Remoto
          </span>
        )}
      </div>
    </>
  );

  if (href) {
    return (
      <Link href={href} className={`${styles.card} ${styles.clicavel}`} aria-label={projeto.titulo}>
        {conteudo}
      </Link>
    );
  }

  if (onClick) {
    return (
      <article className={`${styles.card} ${styles.clicavel}`}>
        <button
          type="button"
          className={styles.botao}
          onClick={() => onClick(projeto)}
          aria-label={`Abrir detalhes de ${projeto.titulo}`}
        >
          {conteudo}
        </button>
      </article>
    );
  }

  return <article className={styles.card}>{conteudo}</article>;
}

const ProjetoCard = memo(ProjetoCardBase);
export default ProjetoCard;
