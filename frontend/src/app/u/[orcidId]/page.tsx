"use client";

import { useState, useEffect, use } from "react";
import { api } from "@/lib/api";
import { NIVEL_LABELS } from "@/lib/constants";
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
    semestre?: number;
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
      <div className={styles.page}>
        <div className={styles.skeleton} style={{ height: 400 }} />
      </div>
    );
  }

  if (error || !perfil) {
    return (
      <div className={styles.page}>
        <div className={styles.errorCard}>
          <span className={styles.errorIcon}>😕</span>
          <h2>Perfil não encontrado</h2>
          <p>O identificador informado não corresponde a nenhum usuário.</p>
        </div>
      </div>
    );
  }

  const nivelLabel =
    perfil.dados_aluno?.nivel
      ? NIVEL_LABELS[perfil.dados_aluno.nivel] || perfil.dados_aluno.nivel
      : null;

  const subtitulo =
    perfil.papel === "aluno" && perfil.dados_aluno
      ? `${nivelLabel} - ${perfil.dados_aluno.semestre}º Semestre`
      : perfil.papel === "professor" && perfil.dados_professor
        ? `${perfil.dados_professor.titulo || ""} ${perfil.dados_professor.cargo || "Professor"}`.trim()
        : perfil.papel === "pesquisador" && perfil.dados_pesquisador
          ? `${perfil.dados_pesquisador.titulo || ""} ${perfil.dados_pesquisador.vinculo || "Pesquisador"}`.trim()
          : perfil.papel;

  return (
    <div className={styles.page}>
      <div className={styles.publicBadge}>👁️ Perfil Público</div>

      <div className={styles.profileHeader}>
        <div className={styles.avatarLarge}>
          {perfil.avatar_url ? (
            <img src={perfil.avatar_url} alt={perfil.nome} />
          ) : (
            <span>{perfil.nome.charAt(0).toUpperCase()}</span>
          )}
        </div>
        <h1 className={styles.profileName}>{perfil.nome_social || perfil.nome}</h1>
        <p className={styles.profileSubtitle}>{subtitulo}</p>
        {perfil.instituicao && (
          <p className={styles.profileInst}>🏛️ {perfil.instituicao}</p>
        )}
        {perfil.orcid_id && (
          <a
            href={`https://orcid.org/${perfil.orcid_id}`}
            target="_blank"
            rel="noopener noreferrer"
            className={styles.orcidBadge}
          >
            <img src="https://info.orcid.org/wp-content/uploads/2019/11/orcid_16x16.png" alt="ORCID" width={16} height={16} />
            {perfil.orcid_id}
          </a>
        )}
      </div>

      {/* Bio */}
      {perfil.bio && (
        <div className={styles.infoCard}>
          <span className={styles.cardLabel}>Sobre</span>
          <p className={styles.cardValue}>{perfil.bio}</p>
        </div>
      )}

      {/* Pesquisa */}
      {perfil.dados_aluno?.linha_pesquisa && (
        <div className={styles.infoCard}>
          <span className={styles.cardLabel}>Linha de Pesquisa</span>
          <span className={styles.cardValue}>{perfil.dados_aluno.linha_pesquisa}</span>
        </div>
      )}
      {(perfil.dados_professor?.linhas_pesquisa?.length ?? 0) > 0 && (
        <div className={styles.infoCard}>
          <span className={styles.cardLabel}>Linhas de Pesquisa</span>
          <span className={styles.cardValue}>{perfil.dados_professor!.linhas_pesquisa!.join(", ")}</span>
        </div>
      )}
      {(perfil.dados_pesquisador?.linhas_pesquisa?.length ?? 0) > 0 && (
        <div className={styles.infoCard}>
          <span className={styles.cardLabel}>Linhas de Pesquisa</span>
          <span className={styles.cardValue}>{perfil.dados_pesquisador!.linhas_pesquisa!.join(", ")}</span>
        </div>
      )}

      {/* Tags */}
      {perfil.interesses.length > 0 && (
        <div className={styles.infoCard}>
          <span className={styles.cardLabel}>Interesses</span>
          <div className={styles.tagList}>
            {perfil.interesses.map((t) => (
              <span key={t} className={styles.tag}>{t}</span>
            ))}
          </div>
        </div>
      )}
      {perfil.habilidades.length > 0 && (
        <div className={styles.infoCard}>
          <span className={styles.cardLabel}>Habilidades</span>
          <div className={styles.tagList}>
            {perfil.habilidades.map((t) => (
              <span key={t} className={styles.tag}>{t}</span>
            ))}
          </div>
        </div>
      )}

      {/* Publicações */}
      {perfil.publicacoes.length > 0 && (
        <div className={styles.pubSection}>
          <h3 className={styles.sectionTitle}>📄 Publicações</h3>
          <div className={styles.pubList}>
            {perfil.publicacoes.map((pub, i) => (
              <div key={i} className={styles.pubItem}>
                <span className={styles.pubTitulo}>{pub.titulo}</span>
                <div className={styles.pubMeta}>
                  {pub.ano && <span>{pub.ano}</span>}
                  {pub.tipo && <span>{pub.tipo}</span>}
                  {pub.doi && (
                    <a href={`https://doi.org/${pub.doi}`} target="_blank" rel="noopener noreferrer">DOI ↗</a>
                  )}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
