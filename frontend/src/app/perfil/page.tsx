"use client";

import { useAuth } from "@/contexts/AuthContext";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import Link from "next/link";
import { api } from "@/lib/api";
import { PERFIL_LABELS, descreverNivel, emailProvisorio } from "@/lib/perfis";
import type { User } from "@/types/user";
import styles from "./perfil.module.css";

/* Ícones inline (traço 2, estilo Lucide). Não são exportados: uma página do
 * App Router só pode exportar o componente e os campos que o Next reconhece. */

function IconeAlerta() {
  return (
    <svg className={styles.avisoIcone} width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <circle cx="12" cy="12" r="10" />
      <path d="M12 8v4" />
      <path d="M12 16h.01" />
    </svg>
  );
}

function IconeLapis() {
  return (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <path d="M17 3a2.85 2.83 0 1 1 4 4L7.5 20.5 2 22l1.5-5.5Z" />
      <path d="m15 5 4 4" />
    </svg>
  );
}

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

/** Chip que detalha o vínculo no vocabulário de cada papel (grau de instrução
 * com o período, titulação e cargo, setor, turma). O papel em si já aparece no
 * primeiro chip, então aqui entra só o que acrescenta informação. */
function detalheDoVinculo(user: User): string | null {
  switch (user.papel) {
    case "aluno":
      return user.dados_aluno?.nivel ? descreverNivel(user.dados_aluno.nivel, user.dados_aluno.semestre) : null;
    case "professor":
      return [user.dados_professor?.titulo, user.dados_professor?.cargo].filter(Boolean).join(" ") || null;
    case "pesquisador":
      return [user.dados_pesquisador?.titulo, user.dados_pesquisador?.vinculo].filter(Boolean).join(" ") || null;
    case "tecnico":
      return [user.dados_tecnico?.cargo, user.dados_tecnico?.setor].filter(Boolean).join(", ") || null;
    case "egresso":
      return user.dados_egresso?.ano_conclusao ? `Turma de ${user.dados_egresso.ano_conclusao}` : null;
    default:
      return null;
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
      <div className={styles.pagina}>
        <div className={`skeleton ${styles.esqueleto}`} />
        <div className={`skeleton ${styles.esqueleto}`} />
      </div>
    );
  }

  if (!user) return null;

  const perfilIncompleto = user.perfil_completo === false;
  // Conta do ORCID que informou o e-mail institucional e ainda não confirmou.
  const emailPendente = user.email_pendente || null;
  const semEmail = !perfilIncompleto && !emailPendente && emailProvisorio(user.email);
  const temAviso = perfilIncompleto || !!emailPendente || semEmail;

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

  const nomeExibido = user.nome_social || user.nome;
  const detalhe = detalheDoVinculo(user);
  const linhasPesquisa = user.dados_aluno?.linha_pesquisa
    ? [user.dados_aluno.linha_pesquisa]
    : user.dados_professor?.linhas_pesquisa?.length
      ? user.dados_professor.linhas_pesquisa
      : user.dados_pesquisador?.linhas_pesquisa?.length
        ? user.dados_pesquisador.linhas_pesquisa
        : [];

  // Pares rótulo/valor que não cabem em chip (o setor e o cargo já estão no chip do vínculo).
  const detalhes: [string, string][] = [];
  if (user.departamento) detalhes.push(["Departamento", user.departamento]);
  if (user.dados_aluno?.orientador) detalhes.push(["Orientador(a)", user.dados_aluno.orientador]);
  if (user.dados_professor?.laboratorio) detalhes.push(["Laboratório", user.dados_professor.laboratorio]);
  if (user.dados_pesquisador?.grupo_pesquisa) detalhes.push(["Grupo de pesquisa", user.dados_pesquisador.grupo_pesquisa]);
  if (user.dados_egresso?.atuacao) detalhes.push(["Atuação atual", user.dados_egresso.atuacao]);

  const publicacoes = user.orcid?.publicacoes ?? [];
  const temConteudo =
    !!user.bio ||
    user.interesses.length > 0 ||
    user.habilidades.length > 0 ||
    linhasPesquisa.length > 0 ||
    detalhes.length > 0 ||
    publicacoes.length > 0;

  return (
    <div className={styles.pagina}>
      <header className="ui-page-header">
        <h1 className="ui-page-title">Perfil</h1>
      </header>

      {temAviso && (
        <div className={styles.avisos}>
          {perfilIncompleto && (
            <div className={styles.aviso} role="status">
              <IconeAlerta />
              <p className={styles.avisoTexto}>
                Seu perfil ainda não está completo: falta escolher o vínculo institucional
                {emailProvisorio(user.email) ? " e informar o e-mail institucional" : ""}.{" "}
                <Link href="/perfil/completar">Completar agora</Link>
              </p>
            </div>
          )}

          {emailPendente && (
            <div className={styles.aviso} role="status">
              <IconeAlerta />
              <p className={styles.avisoTexto}>
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
                  <button
                    type="button"
                    className={styles.avisoBotao}
                    onClick={reenviarConfirmacao}
                    disabled={reenvio === "enviando"}
                  >
                    {reenvio === "enviando" ? "Reenviando..." : "Reenviar e-mail"}
                  </button>
                )}
              </p>
            </div>
          )}

          {semEmail && (
            <div className={styles.aviso} role="status">
              <IconeAlerta />
              <p className={styles.avisoTexto}>
                Sua conta ainda usa o e-mail provisório do ORCID.{" "}
                <Link href="/perfil/completar">Informar o e-mail institucional</Link>
              </p>
            </div>
          )}
        </div>
      )}

      {/* ── Cabeçalho: avatar, nome, chips e ações ── */}
      <section className={`ui-card ${styles.cabecalho}`} aria-labelledby="perfil-nome">
        <div className={styles.avatar} aria-hidden="true">
          {user.avatar_url ? (
            // O avatar vem de domínios variados (ORCID, geradores): <img> simples,
            // sem passar pelo otimizador do Next, que exige lista fixa de hosts.
            // eslint-disable-next-line @next/next/no-img-element
            <img src={user.avatar_url} alt="" />
          ) : (
            <span>{nomeExibido.charAt(0).toUpperCase()}</span>
          )}
        </div>

        <div className={styles.identidade}>
          <h2 id="perfil-nome" className={styles.nome}>{nomeExibido}</h2>
          {user.username && <p className={styles.usuario}>@{user.username}</p>}
          <ul className={styles.chips} aria-label="Vínculo institucional">
            <li className="ui-chip ui-chip-primary">{PERFIL_LABELS[user.papel] || user.papel}</li>
            {user.instituicao && (
              <li className="ui-chip ui-chip-truncate" title={user.instituicao}>{user.instituicao}</li>
            )}
            {user.curso && (
              <li className="ui-chip ui-chip-truncate" title={user.curso}>{user.curso}</li>
            )}
            {detalhe && (
              <li className="ui-chip ui-chip-truncate" title={detalhe}>{detalhe}</li>
            )}
          </ul>
        </div>

        <div className={styles.acoes}>
          <Link href="/perfil/editar" className="ui-btn ui-btn-secondary">
            <IconeLapis />
            Editar perfil
          </Link>
          {user.orcid?.orcid_id && (
            <a
              href={`https://orcid.org/${user.orcid.orcid_id}`}
              target="_blank"
              rel="noopener noreferrer"
              className="ui-btn ui-btn-ghost"
              aria-label={`Abrir o registro ORCID ${user.orcid.orcid_id}`}
            >
              <IconeOrcid />
              {user.orcid.orcid_id}
            </a>
          )}
        </div>
      </section>

      {/* ── Seções ── */}
      {temConteudo ? (
        <div className={styles.secoes}>
          {user.bio && (
            <section className={`ui-card ${styles.secao}`} aria-labelledby="perfil-sobre">
              <h3 id="perfil-sobre" className={styles.secaoTitulo}>Sobre</h3>
              <p className={styles.texto}>{user.bio}</p>
            </section>
          )}

          {(user.interesses.length > 0 || user.habilidades.length > 0) && (
            <div className={styles.duas}>
              {user.interesses.length > 0 && (
                <section className={`ui-card ${styles.secao}`} aria-labelledby="perfil-interesses">
                  <h3 id="perfil-interesses" className={styles.secaoTitulo}>Interesses</h3>
                  <ul className={styles.chips}>
                    {user.interesses.map((tag) => (
                      <li key={tag} className="ui-chip ui-chip-truncate" title={tag}>{tag}</li>
                    ))}
                  </ul>
                </section>
              )}
              {user.habilidades.length > 0 && (
                <section className={`ui-card ${styles.secao}`} aria-labelledby="perfil-habilidades">
                  <h3 id="perfil-habilidades" className={styles.secaoTitulo}>Habilidades</h3>
                  <ul className={styles.chips}>
                    {user.habilidades.map((tag) => (
                      <li key={tag} className="ui-chip ui-chip-truncate" title={tag}>{tag}</li>
                    ))}
                  </ul>
                </section>
              )}
            </div>
          )}

          {linhasPesquisa.length > 0 && (
            <section className={`ui-card ${styles.secao}`} aria-labelledby="perfil-linhas">
              <h3 id="perfil-linhas" className={styles.secaoTitulo}>
                {linhasPesquisa.length === 1 ? "Linha de pesquisa" : "Linhas de pesquisa"}
              </h3>
              <ul className={styles.chips}>
                {linhasPesquisa.map((linha) => (
                  <li key={linha} className="ui-chip ui-chip-primary ui-chip-truncate" title={linha}>{linha}</li>
                ))}
              </ul>
            </section>
          )}

          {detalhes.length > 0 && (
            <section className={`ui-card ${styles.secao}`} aria-labelledby="perfil-vinculo">
              <h3 id="perfil-vinculo" className={styles.secaoTitulo}>Vínculo</h3>
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

          {publicacoes.length > 0 && (
            <section className={`ui-card ${styles.secao}`} aria-labelledby="perfil-publicacoes">
              <h3 id="perfil-publicacoes" className={styles.secaoTitulo}>Publicações (via ORCID)</h3>
              <ul className={styles.publicacoes}>
                {publicacoes.map((pub, i) => (
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
          Seu perfil ainda não tem apresentação, interesses nem habilidades.{" "}
          <Link href="/perfil/editar">Editar o perfil</Link> para contar à comunidade com o que você trabalha.
        </div>
      )}
    </div>
  );
}
