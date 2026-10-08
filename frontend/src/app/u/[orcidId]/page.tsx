"use client";

import { useState, useEffect, use } from "react";
import { api } from "@/lib/api";
import { PERFIL_LABELS, descreverNivel } from "@/lib/perfis";
import styles from "./perfil-publico.module.css";

interface PerfilPublico {
  id: string;
  nome: string;
  nome_social?: string;
  avatar_url?: string;
  bio?: string;
  papel: string;
  instituicao?: string;
  curso?: string;
  interesses: string[];
  habilidades: string[];
  dados_aluno?: {
    nivel?: string;
    semestre?: number | null;
    orientador?: string;
    linha_pesquisa?: string;
  };
  dados_professor?: {
    titulo?: string;
    cargo?: string;
    linhas_pesquisa?: string[];
    laboratorio?: string;
  };
  dados_pesquisador?: {
    titulo?: string;
    vinculo?: string;
    linhas_pesquisa?: string[];
    grupo_pesquisa?: string;
  };
  orcid_id?: string;
  publicacoes: {
    titulo: string;
    doi?: string;
    ano?: number;
    tipo?: string;
  }[];
}

/* Ícones inline (traço 2, estilo Lucide). */

function IconeOrcid() {
  return (
    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <circle cx="12" cy="12" r="10" />
      <path d="M8.5 10.5v6" />
      <path d="M8.5 7.5h.01" />
      <path d="M12.5 7.5h2a4.5 4.5 0 0 1 0 9h-2z" />
    </svg>
  );
}

function IconeLinkExterno() {
  return (
    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <path d="M15 3h6v6" />
      <path d="M10 14 21 3" />
      <path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6" />
    </svg>
  );
}

function IconeUsuarioAusente() {
  return (
    <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <path d="M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2" />
      <circle cx="9" cy="7" r="4" />
      <path d="m17 8 5 5" />
      <path d="m22 8-5 5" />
    </svg>
  );
}

/** Chip que detalha o vínculo (grau de instrução com o período, titulação e
 * cargo ou vínculo). O papel em si já aparece no primeiro chip. */
function detalheDoVinculo(perfil: PerfilPublico): string | null {
  switch (perfil.papel) {
    case "aluno":
      return perfil.dados_aluno?.nivel ? descreverNivel(perfil.dados_aluno.nivel, perfil.dados_aluno.semestre) : null;
    case "professor":
      return [perfil.dados_professor?.titulo, perfil.dados_professor?.cargo].filter(Boolean).join(" ") || null;
    case "pesquisador":
      return [perfil.dados_pesquisador?.titulo, perfil.dados_pesquisador?.vinculo].filter(Boolean).join(" ") || null;
    default:
      return null;
  }
}

export default function PerfilPublicoPage({
  params,
}: {
  params: Promise<{ orcidId: string }>;
}) {
  const { orcidId } = use(params);
  const [perfil, setPerfil] = useState<PerfilPublico | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    async function carregarPerfil() {
      try {
        const data = await api.get<PerfilPublico>(
          `/api/perfil/${orcidId}`
        );
        setPerfil(data);
      } catch {
        setError("Perfil não encontrado.");
      } finally {
        setIsLoading(false);
      }
    }
    carregarPerfil();
  }, [orcidId]);

  if (isLoading) {
    return (
      <div className={styles.pagina}>
        <div className={`skeleton ${styles.esqueleto}`} />
        <div className={`skeleton ${styles.esqueleto}`} />
      </div>
    );
  }

  if (error || !perfil) {
    return (
      <div className={styles.pagina}>
        <div className={`ui-card ${styles.erro}`} role="status">
          <span className={styles.erroIcone}>
            <IconeUsuarioAusente />
          </span>
          <h1 className={styles.erroTitulo}>Perfil não encontrado</h1>
          <p className={styles.erroTexto}>O identificador informado não corresponde a nenhum usuário.</p>
        </div>
      </div>
    );
  }

  const nomeExibido = perfil.nome_social || perfil.nome;
  const detalhe = detalheDoVinculo(perfil);
  const linhasPesquisa = perfil.dados_aluno?.linha_pesquisa
    ? [perfil.dados_aluno.linha_pesquisa]
    : perfil.dados_professor?.linhas_pesquisa?.length
      ? perfil.dados_professor.linhas_pesquisa
      : perfil.dados_pesquisador?.linhas_pesquisa?.length
        ? perfil.dados_pesquisador.linhas_pesquisa
        : [];

  const detalhes: [string, string][] = [];
  if (perfil.dados_aluno?.orientador) detalhes.push(["Orientador(a)", perfil.dados_aluno.orientador]);
  if (perfil.dados_professor?.laboratorio) detalhes.push(["Laboratório", perfil.dados_professor.laboratorio]);
  if (perfil.dados_pesquisador?.grupo_pesquisa) detalhes.push(["Grupo de pesquisa", perfil.dados_pesquisador.grupo_pesquisa]);

  const temConteudo =
    !!perfil.bio ||
    perfil.interesses.length > 0 ||
    perfil.habilidades.length > 0 ||
    linhasPesquisa.length > 0 ||
    detalhes.length > 0 ||
    perfil.publicacoes.length > 0;

  return (
    <div className={styles.pagina}>
      <header className={`ui-page-header ${styles.topo}`}>
        <span className="ui-chip ui-chip-outline">Perfil público</span>
      </header>

      {/* ── Cabeçalho: avatar, nome, chips e ORCID ── */}
      <section className={`ui-card ${styles.cabecalho}`} aria-labelledby="perfil-nome">
        <div className={styles.avatar} aria-hidden="true">
          {perfil.avatar_url ? (
            // O avatar vem de domínios variados (ORCID, geradores): <img> simples,
            // sem passar pelo otimizador do Next, que exige lista fixa de hosts.
            // eslint-disable-next-line @next/next/no-img-element
            <img src={perfil.avatar_url} alt="" />
          ) : (
            <span>{nomeExibido.charAt(0).toUpperCase()}</span>
          )}
        </div>

        <div className={styles.identidade}>
          <h1 id="perfil-nome" className={styles.nome}>{nomeExibido}</h1>
          <ul className={styles.chips} aria-label="Vínculo institucional">
            <li className="ui-chip ui-chip-primary">{PERFIL_LABELS[perfil.papel] || perfil.papel}</li>
            {perfil.instituicao && (
              <li className="ui-chip ui-chip-truncate" title={perfil.instituicao}>{perfil.instituicao}</li>
            )}
            {perfil.curso && (
              <li className="ui-chip ui-chip-truncate" title={perfil.curso}>{perfil.curso}</li>
            )}
            {detalhe && (
              <li className="ui-chip ui-chip-truncate" title={detalhe}>{detalhe}</li>
            )}
          </ul>
        </div>

        {perfil.orcid_id && (
          <div className={styles.acoes}>
            <a
              href={`https://orcid.org/${perfil.orcid_id}`}
              target="_blank"
              rel="noopener noreferrer"
              className="ui-btn ui-btn-ghost"
              aria-label={`Abrir o registro ORCID ${perfil.orcid_id}`}
            >
              <IconeOrcid />
              {perfil.orcid_id}
            </a>
          </div>
        )}
      </section>

      {/* ── Seções ── */}
      {temConteudo ? (
        <div className={styles.secoes}>
          {perfil.bio && (
            <section className={`ui-card ${styles.secao}`} aria-labelledby="perfil-sobre">
              <h2 id="perfil-sobre" className={styles.secaoTitulo}>Sobre</h2>
              <p className={styles.texto}>{perfil.bio}</p>
            </section>
          )}

          {(perfil.interesses.length > 0 || perfil.habilidades.length > 0) && (
            <div className={styles.duas}>
              {perfil.interesses.length > 0 && (
                <section className={`ui-card ${styles.secao}`} aria-labelledby="perfil-interesses">
                  <h2 id="perfil-interesses" className={styles.secaoTitulo}>Interesses</h2>
                  <ul className={styles.chips}>
                    {perfil.interesses.map((t) => (
                      <li key={t} className="ui-chip ui-chip-truncate" title={t}>{t}</li>
                    ))}
                  </ul>
                </section>
              )}
              {perfil.habilidades.length > 0 && (
                <section className={`ui-card ${styles.secao}`} aria-labelledby="perfil-habilidades">
                  <h2 id="perfil-habilidades" className={styles.secaoTitulo}>Habilidades</h2>
                  <ul className={styles.chips}>
                    {perfil.habilidades.map((t) => (
                      <li key={t} className="ui-chip ui-chip-truncate" title={t}>{t}</li>
                    ))}
                  </ul>
                </section>
              )}
            </div>
          )}

          {linhasPesquisa.length > 0 && (
            <section className={`ui-card ${styles.secao}`} aria-labelledby="perfil-linhas">
              <h2 id="perfil-linhas" className={styles.secaoTitulo}>
                {linhasPesquisa.length === 1 ? "Linha de pesquisa" : "Linhas de pesquisa"}
              </h2>
              <ul className={styles.chips}>
                {linhasPesquisa.map((linha) => (
                  <li key={linha} className="ui-chip ui-chip-primary ui-chip-truncate" title={linha}>{linha}</li>
                ))}
              </ul>
            </section>
          )}

          {detalhes.length > 0 && (
            <section className={`ui-card ${styles.secao}`} aria-labelledby="perfil-vinculo">
              <h2 id="perfil-vinculo" className={styles.secaoTitulo}>Vínculo</h2>
              <dl className={styles.detalhes}>
                {detalhes.map(([rotulo, valor]) => (
                  <div key={rotulo} className={styles.detalhe}>
                    <dt>{rotulo}</dt>
                    <dd>{valor}</dd>
                  </div>
                ))}
              </dl>
            </section>
          )}

          {perfil.publicacoes.length > 0 && (
            <section className={`ui-card ${styles.secao}`} aria-labelledby="perfil-publicacoes">
              <h2 id="perfil-publicacoes" className={styles.secaoTitulo}>Publicações</h2>
              <ul className={styles.publicacoes}>
                {perfil.publicacoes.map((pub, i) => (
                  <li key={`${pub.doi || pub.titulo}-${i}`} className={styles.publicacao}>
                    <p className={styles.pubTitulo}>{pub.titulo}</p>
                    <div className={styles.pubMeta}>
                      {pub.ano && <span>{pub.ano}</span>}
                      {pub.tipo && <span>{pub.tipo}</span>}
                      {pub.doi && (
                        <a href={`https://doi.org/${pub.doi}`} target="_blank" rel="noopener noreferrer">
                          DOI
                          <IconeLinkExterno />
                        </a>
                      )}
                    </div>
                  </li>
                ))}
              </ul>
            </section>
          )}
        </div>
      ) : (
        <div className={`ui-card ${styles.semConteudo}`}>
          Esta pessoa ainda não preencheu apresentação, interesses nem habilidades.
        </div>
      )}
    </div>
  );
}
