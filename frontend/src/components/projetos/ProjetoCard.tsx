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

/** "UNIR, campus Ji-Paraná, Departamento de ..." numa linha de texto. */
function localDoProjeto(projeto: Projeto, compacto: boolean) {
  return [
    projeto.instituicao,
    projeto.campus ? `campus ${projeto.campus}` : null,
    compacto ? null : projeto.unidade,
  ]
    .filter(Boolean)
    .join(", ");
}

/**
 * Card de projeto, o mesmo na busca e na página inicial.
 *
 * Hierarquia: tipo e situação no topo, título, quem coordena, onde
 * (instituição, campus e unidade numa linha de texto), resumo em duas
 * linhas e, no rodapé, só o que ajuda a escolher de relance: a área, com
 * cor própria, e "Remoto" em verde; o ano fica discreto à direita. Clica-se
 * no card inteiro: `onClick` abre o modal na busca; `href` leva a outra
 * página.
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
  const local = localDoProjeto(projeto, compacto);

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

      {local && (
        <p className={styles.local} title={local}>
          {projeto.campus ? <IconePin /> : <IconePredio />}
          <span className={styles.localTexto}>{local}</span>
        </p>
      )}

      {projeto.descricao && !compacto && <p className={styles.resumo}>{projeto.descricao}</p>}

      {(projeto.area_conhecimento || projeto.e_remoto || projeto.ano) && (
        <div className={styles.rodape}>
          {projeto.area_conhecimento && (
            <span className={`ui-chip ${area.classe}`} title="Área do conhecimento (grande área do CNPq)">
              {area.icone}
              {projeto.area_conhecimento}
            </span>
          )}
          {projeto.e_remoto && (
            <span className="ui-chip ui-chip-success">
              <IconeGlobo />
              Remoto
            </span>
          )}
          {projeto.ano && (
            <span className={styles.ano} title="Ano do projeto">
              <IconeCalendario />
              {projeto.ano}
            </span>
          )}
        </div>
      )}
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
