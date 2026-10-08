"use client";

import { memo } from "react";
import Link from "next/link";
import {
  formatarSituacao,
  moduloDoProjeto,
  tomDaSituacao,
  type Projeto,
} from "@/types/projeto";
import styles from "./ProjetoCard.module.css";

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
          <span className={`${styles.tag} ${styles.tagArea}`} title="Área do conhecimento (grande área do CNPq)">
            {projeto.area_conhecimento}
          </span>
        )}
        {projeto.instituicao && (
          <span
            className={`${styles.tag} ${projeto.origem ? styles.tagInstituicao : styles.tagLonga}`}
            title={projeto.instituicao}
          >
            {projeto.instituicao}
          </span>
        )}
        {projeto.campus && !compacto && (
          <span className={`${styles.tag} ${styles.tagLonga}`} title={`Campus ${projeto.campus}`}>
            {projeto.campus}
          </span>
        )}
        {projeto.unidade && !compacto && (
          <span className={`${styles.tag} ${styles.tagLonga}`} title={projeto.unidade}>
            {projeto.unidade}
          </span>
        )}
        {projeto.ano && <span className={styles.tag}>{projeto.ano}</span>}
        {projeto.e_remoto && <span className={`${styles.tag} ${styles.tagRemoto}`}>Remoto</span>}
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
