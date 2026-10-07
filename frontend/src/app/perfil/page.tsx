"use client";

import { useAuth } from "@/contexts/AuthContext";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import Link from "next/link";
import { api } from "@/lib/api";
import { NIVEL_LABELS } from "@/lib/constants";
import { PERFIL_LABELS, emailProvisorio } from "@/lib/perfis";
import styles from "./perfil.module.css";

/** Linha abaixo do nome: o que a pessoa é, no vocabulário do seu vínculo.
 * Não é exportada: uma página do App Router só pode exportar o componente e
 * os campos que o Next reconhece, e o `next build` recusa qualquer outro. */
function subtituloDoPerfil(user: {
  papel: string;
  dados_aluno?: { nivel?: string; semestre?: number } | null;
  dados_professor?: { titulo?: string | null; cargo?: string | null } | null;
  dados_pesquisador?: { titulo?: string | null; vinculo?: string | null } | null;
  dados_tecnico?: { setor?: string | null; cargo?: string | null } | null;
  dados_egresso?: { ano_conclusao?: number | null; atuacao?: string | null } | null;
  curso?: string | null;
}) {
  switch (user.papel) {
    case "aluno": {
      const nivel = user.dados_aluno?.nivel ? NIVEL_LABELS[user.dados_aluno.nivel] || user.dados_aluno.nivel : "Discente";
      const semestre = user.dados_aluno?.semestre;
      return semestre ? `${nivel} - ${semestre}º Semestre` : nivel;
    }
    case "professor":
      return `${user.dados_professor?.titulo || ""} ${user.dados_professor?.cargo || "Docente"}`.trim();
    case "pesquisador":
      return `${user.dados_pesquisador?.titulo || ""} ${user.dados_pesquisador?.vinculo || "Pesquisador(a)"}`.trim();
    case "tecnico":
      return [user.dados_tecnico?.cargo || "Técnico(a)-administrativo(a)", user.dados_tecnico?.setor]
        .filter(Boolean)
        .join(" - ");
    case "egresso":
      return [
        user.curso ? `Egresso(a) de ${user.curso}` : "Egresso(a)",
        user.dados_egresso?.ano_conclusao ? `turma de ${user.dados_egresso.ano_conclusao}` : null,
      ]
        .filter(Boolean)
        .join(", ");
    default:
      return PERFIL_LABELS[user.papel] || user.papel;
  }
}

export default function PerfilPage() {
  const { user, isAuthenticated, isLoading } = useAuth();
  const router = useRouter();
  const [reenvio, setReenvio] = useState<"" | "enviando" | "enviado" | "erro">("");

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

  const extra = user;
  const perfilIncompleto = user.perfil_completo === false;
  // Conta do ORCID que informou o e-mail institucional e ainda não confirmou.
  const emailPendente = user.email_pendente || null;
  const semEmail = !perfilIncompleto && !emailPendente && emailProvisorio(user.email);

  async function reenviarConfirmacao() {
    if (!emailPendente) return;
    setReenvio("enviando");
    try {
      await api.post("/api/auth/reenviar-verificacao", { email: emailPendente });
      setReenvio("enviado");
    } catch {
      setReenvio("erro");
    }
  }

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

      {perfilIncompleto && (
        <div className={styles.noticeCard}>
          Seu perfil ainda não está completo: falta escolher o vínculo institucional
          {emailProvisorio(user.email) ? " e informar o e-mail institucional" : ""}.{" "}
          <Link href="/perfil/completar">Completar agora</Link>
        </div>
      )}

      {emailPendente && (
        <div className={styles.noticeCard}>
          Enviamos um link de confirmação para <strong>{emailPendente}</strong>.{" "}
          {user.email_pendente_vincula
            ? "Esse e-mail já tem uma conta na plataforma: ao confirmar, o seu ORCID passa a entrar nela."
            : "Até você confirmar, a conta continua com o e-mail provisório do ORCID."}{" "}
          <Link href="/perfil/completar">Informar outro e-mail</Link>.{" "}
          {reenvio === "enviado" ? (
            <span>Novo link enviado.</span>
          ) : reenvio === "erro" ? (
            <span>Não foi possível reenviar agora. Tente de novo em instantes.</span>
          ) : (
            <button type="button" className={styles.linkButton} onClick={reenviarConfirmacao} disabled={reenvio === "enviando"}>
              {reenvio === "enviando" ? "Reenviando..." : "Reenviar e-mail"}
            </button>
          )}
        </div>
      )}

      {semEmail && (
        <div className={styles.noticeCard}>
          Sua conta ainda usa o e-mail provisório do ORCID.{" "}
          <Link href="/perfil/completar">Informar o e-mail institucional</Link>
        </div>
      )}

      <div className={styles.profileWrapper}>
        {/* ── Avatar & Nome ── */}
        <div className={styles.profileHeader}>
          <div className={styles.avatarLarge}>
            {user.avatar_url ? (
              <img src={user.avatar_url} alt={user.nome} />
            ) : (
              <span>{(user.nome_social || user.nome).charAt(0).toUpperCase()}</span>
            )}
          </div>
          <h2 className={styles.profileName}>{user.nome_social || user.nome}</h2>
          <p className={styles.profileSubtitle}>{subtituloDoPerfil(extra)}</p>
          {extra.username && <p className={styles.profileHandle}>@{extra.username}</p>}
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
          <div className={styles.infoCard}>
            <span className={styles.cardLabel}>Vínculo institucional</span>
            <span className={styles.cardValue}>{PERFIL_LABELS[user.papel] || user.papel}</span>
          </div>

          {user.instituicao && (
            <div className={styles.infoCard}>
              <span className={styles.cardLabel}>Instituição</span>
              <span className={styles.cardValue}>{user.instituicao}</span>
            </div>
          )}

          {user.curso && (
            <div className={styles.infoCard}>
              <span className={styles.cardLabel}>Curso</span>
              <span className={styles.cardValue}>{user.curso}</span>
            </div>
          )}

          {user.departamento && (
            <div className={styles.infoCard}>
              <span className={styles.cardLabel}>Departamento</span>
              <span className={styles.cardValue}>{user.departamento}</span>
            </div>
          )}

          {/* Linha de Pesquisa (discente) */}
          {user.dados_aluno?.linha_pesquisa && (
            <div className={styles.infoCard}>
              <span className={styles.cardLabel}>Linha de Pesquisa</span>
              <span className={styles.cardValue}>{user.dados_aluno.linha_pesquisa}</span>
            </div>
          )}

          {/* Linhas de Pesquisa (docente/pesquisador) */}
          {(user.dados_professor?.linhas_pesquisa?.length ?? 0) > 0 && (
            <div className={styles.infoCard}>
              <span className={styles.cardLabel}>Linhas de Pesquisa</span>
              <span className={styles.cardValue}>{user.dados_professor!.linhas_pesquisa.join(", ")}</span>
            </div>
          )}
          {(user.dados_pesquisador?.linhas_pesquisa?.length ?? 0) > 0 && (
            <div className={styles.infoCard}>
              <span className={styles.cardLabel}>Linhas de Pesquisa</span>
              <span className={styles.cardValue}>{user.dados_pesquisador!.linhas_pesquisa.join(", ")}</span>
            </div>
          )}

          {/* Orientador(a) */}
          {user.dados_aluno?.orientador && (
            <div className={styles.infoCard}>
              <span className={styles.cardLabel}>Orientador(a)</span>
              <span className={styles.cardValue}>{user.dados_aluno.orientador}</span>
            </div>
          )}

          {/* Laboratório */}
          {user.dados_professor?.laboratorio && (
            <div className={styles.infoCard}>
              <span className={styles.cardLabel}>Laboratório</span>
              <span className={styles.cardValue}>{user.dados_professor.laboratorio}</span>
            </div>
          )}

          {/* Grupo de Pesquisa */}
          {user.dados_pesquisador?.grupo_pesquisa && (
            <div className={styles.infoCard}>
              <span className={styles.cardLabel}>Grupo de Pesquisa</span>
              <span className={styles.cardValue}>{user.dados_pesquisador.grupo_pesquisa}</span>
            </div>
          )}

          {/* Técnico(a): setor */}
          {extra.dados_tecnico?.setor && (
            <div className={styles.infoCard}>
              <span className={styles.cardLabel}>Setor</span>
              <span className={styles.cardValue}>{extra.dados_tecnico.setor}</span>
            </div>
          )}

          {/* Egresso(a): atuação */}
          {extra.dados_egresso?.atuacao && (
            <div className={styles.infoCard}>
              <span className={styles.cardLabel}>Atuação atual</span>
              <span className={styles.cardValue}>{extra.dados_egresso.atuacao}</span>
            </div>
          )}

          {/* Interesses */}
          {user.interesses.length > 0 && (
            <div className={styles.infoCard}>
              <span className={styles.cardLabel}>Interesses</span>
              <div className={styles.tagList}>
                {user.interesses.map((tag) => (
                  <span key={tag} className={styles.tag}>{tag}</span>
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
                  <span key={tag} className={styles.tag}>{tag}</span>
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
            <h3 className={styles.sectionTitle}>📄 Publicações (via ORCID)</h3>
            <div className={styles.publicacoesList}>
              {user.orcid.publicacoes.map((pub, i) => (
                <div key={i} className={styles.publicacaoItem}>
                  <span className={styles.pubTitulo}>{pub.titulo}</span>
                  <div className={styles.pubMeta}>
                    {pub.ano && <span>{pub.ano}</span>}
                    {pub.tipo && <span>{pub.tipo}</span>}
                    {pub.doi && (
                      <a href={`https://doi.org/${pub.doi}`} target="_blank" rel="noopener noreferrer">
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
