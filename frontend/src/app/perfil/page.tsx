"use client";

import { useAuth } from "@/contexts/AuthContext";
import { useRouter } from "next/navigation";
import { useEffect } from "react";
import Link from "next/link";
import { NIVEL_LABELS } from "@/lib/constants";
import styles from "./perfil.module.css";

export default function PerfilPage() {
  const { user, isAuthenticated, isLoading } = useAuth();
  const router = useRouter();

  useEffect(() => {
    if (!isLoading && !isAuthenticated) {
      router.push("/login");
    }
  }, [isLoading, isAuthenticated, router]);

  if (isLoading) {
    return (
      <div className={styles.container}>
        <div className={styles.skeleton} style={{ height: 400 }} />
      </div>
    );
  }

  if (!user) return null;

  const nivelLabel =
    user.dados_aluno?.nivel
      ? NIVEL_LABELS[user.dados_aluno.nivel] || user.dados_aluno.nivel
      : null;

  const subtitulo =
    user.papel === "aluno" && user.dados_aluno
      ? `${nivelLabel} - ${user.dados_aluno.semestre}º Semestre`
      : user.papel === "professor" && user.dados_professor
        ? `${user.dados_professor.titulo || ""} ${user.dados_professor.cargo || "Professor"}`.trim()
        : user.papel === "pesquisador" && user.dados_pesquisador
          ? `${user.dados_pesquisador.titulo || ""} ${user.dados_pesquisador.vinculo || "Pesquisador"}`.trim()
          : user.papel;

  return (
    <div className={styles.container}>
      <div className={styles.pageHeader}>
        <div className={styles.pageHeaderLeft}>
          <span className={styles.pageIcon}>🎓</span>
          <h1 className={styles.pageTitle}>Perfil</h1>
        </div>
        <Link href="/perfil/editar" className={styles.editButton}>
          ✏️ Editar Perfil
        </Link>
      </div>

      <div className={styles.profileWrapper}>
        {/* ── Avatar & Nome ── */}
        <div className={styles.profileHeader}>
          <div className={styles.avatarLarge}>
            {user.avatar_url ? (
              <img src={user.avatar_url} alt={user.nome} />
            ) : (
              <span>{user.nome.charAt(0).toUpperCase()}</span>
            )}
          </div>
          <h2 className={styles.profileName}>{user.nome_social || user.nome}</h2>
          <p className={styles.profileSubtitle}>{subtitulo}</p>
          {user.orcid?.orcid_id && (
            <a
              href={`https://orcid.org/${user.orcid.orcid_id}`}
              target="_blank"
              rel="noopener noreferrer"
              className={styles.orcidBadge}
            >
              <img
                src="https://info.orcid.org/wp-content/uploads/2019/11/orcid_16x16.png"
                alt="ORCID"
                width={16}
                height={16}
              />
              {user.orcid.orcid_id}
            </a>
          )}
        </div>

        {/* ── Info Cards ── */}
        <div className={styles.cardsGrid}>
          {/* Linha de Pesquisa (aluno) */}
          {user.dados_aluno?.linha_pesquisa && (
            <div className={styles.infoCard}>
              <span className={styles.cardLabel}>Linha de Pesquisa</span>
              <span className={styles.cardValue}>
                {user.dados_aluno.linha_pesquisa}
              </span>
            </div>
          )}

          {/* Linhas de Pesquisa (professor/pesquisador) */}
          {(user.dados_professor?.linhas_pesquisa?.length ?? 0) > 0 && (
            <div className={styles.infoCard}>
              <span className={styles.cardLabel}>Linhas de Pesquisa</span>
              <span className={styles.cardValue}>
                {user.dados_professor!.linhas_pesquisa.join(", ")}
              </span>
            </div>
          )}
          {(user.dados_pesquisador?.linhas_pesquisa?.length ?? 0) > 0 && (
            <div className={styles.infoCard}>
              <span className={styles.cardLabel}>Linhas de Pesquisa</span>
              <span className={styles.cardValue}>
                {user.dados_pesquisador!.linhas_pesquisa.join(", ")}
              </span>
            </div>
          )}

          {/* Orientador */}
          {user.dados_aluno?.orientador && (
            <div className={styles.infoCard}>
              <span className={styles.cardLabel}>Orientador(a)</span>
              <span className={styles.cardValue}>
                {user.dados_aluno.orientador}
              </span>
            </div>
          )}

          {/* Instituição */}
          {user.instituicao && (
            <div className={styles.infoCard}>
              <span className={styles.cardLabel}>Instituição</span>
              <span className={styles.cardValue}>{user.instituicao}</span>
            </div>
          )}

          {/* Laboratório */}
          {user.dados_professor?.laboratorio && (
            <div className={styles.infoCard}>
              <span className={styles.cardLabel}>Laboratório</span>
              <span className={styles.cardValue}>
                {user.dados_professor.laboratorio}
              </span>
            </div>
          )}

          {/* Grupo de Pesquisa */}
          {user.dados_pesquisador?.grupo_pesquisa && (
            <div className={styles.infoCard}>
              <span className={styles.cardLabel}>Grupo de Pesquisa</span>
              <span className={styles.cardValue}>
                {user.dados_pesquisador.grupo_pesquisa}
              </span>
            </div>
          )}

          {/* Interesses */}
          {user.interesses.length > 0 && (
            <div className={styles.infoCard}>
              <span className={styles.cardLabel}>Interesses</span>
              <div className={styles.tagList}>
                {user.interesses.map((tag) => (
                  <span key={tag} className={styles.tag}>
                    {tag}
                  </span>
                ))}
              </div>
            </div>
          )}

          {/* Habilidades */}
          {user.habilidades.length > 0 && (
            <div className={styles.infoCard}>
              <span className={styles.cardLabel}>Habilidades</span>
              <div className={styles.tagList}>
                {user.habilidades.map((tag) => (
                  <span key={tag} className={styles.tag}>
                    {tag}
                  </span>
                ))}
              </div>
            </div>
          )}

          {/* Bio */}
          {user.bio && (
            <div className={`${styles.infoCard} ${styles.cardFull}`}>
              <span className={styles.cardLabel}>Sobre</span>
              <p className={styles.cardValue}>{user.bio}</p>
            </div>
          )}
        </div>

        {/* ── Publicações ORCID ── */}
        {user.orcid?.publicacoes && user.orcid.publicacoes.length > 0 && (
          <div className={styles.publicacoesSection}>
            <h3 className={styles.sectionTitle}>
              📄 Publicações (via ORCID)
            </h3>
            <div className={styles.publicacoesList}>
              {user.orcid.publicacoes.map((pub, i) => (
                <div key={i} className={styles.publicacaoItem}>
                  <span className={styles.pubTitulo}>{pub.titulo}</span>
                  <div className={styles.pubMeta}>
                    {pub.ano && <span>{pub.ano}</span>}
                    {pub.tipo && <span>{pub.tipo}</span>}
                    {pub.doi && (
                      <a
                        href={`https://doi.org/${pub.doi}`}
                        target="_blank"
                        rel="noopener noreferrer"
                      >
                        DOI ↗
                      </a>
                    )}
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
