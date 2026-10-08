"use client";

import { useState, useEffect, FormEvent } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { useAuth } from "@/contexts/AuthContext";
import { api } from "@/lib/api";
import { PERFIS, NIVEIS, PERIODO_POR_NIVEL, nivelAtual, type TipoPerfil, emailProvisorio } from "@/lib/perfis";
import styles from "./editar.module.css";

function IconeVoltar() {
  return (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <path d="m12 19-7-7 7-7" />
      <path d="M19 12H5" />
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

/**
 * Edição do perfil: dados pessoais, vínculo institucional (que pode ser
 * trocado), campos específicos do vínculo, interesses e habilidades.
 */
export default function EditarPerfilPage() {
  const { user, token, isAuthenticated, isLoading: authLoading, refreshUser, loginWithOrcid } = useAuth();
  // Quem não tem e-mail acadêmico comprova o vínculo pela conta ORCID.
  const [semEmailAcademico, setSemEmailAcademico] = useState(false);
  const router = useRouter();

  const [nome, setNome] = useState("");
  const [nomeSocial, setNomeSocial] = useState("");
  const [bio, setBio] = useState("");
  const [papel, setPapel] = useState<TipoPerfil>("aluno");
  const [instituicao, setInstituicao] = useState("");
  const [curso, setCurso] = useState("");
  const [departamento, setDepartamento] = useState("");
  const [interesses, setInteresses] = useState("");
  const [habilidades, setHabilidades] = useState("");

  // Dados específicos por vínculo. Cada sub-documento tem os seus próprios
  // estados: campos homônimos (titulação, cargo, linhas de pesquisa) não
  // podem ser compartilhados, senão trocar de vínculo e voltar sobrescreve
  // os dados do vínculo anterior, que continuam gravados no banco.
  const [nivel, setNivel] = useState("graduacao_incompleta");
  const [semestre, setSemestre] = useState("1");
  const periodo = PERIODO_POR_NIVEL[nivel];
  const [orientador, setOrientador] = useState("");
  const [linhaPesquisa, setLinhaPesquisa] = useState("");
  const [tituloProf, setTituloProf] = useState("");
  const [cargoProf, setCargoProf] = useState("");
  const [linhasProf, setLinhasProf] = useState("");
  const [laboratorio, setLaboratorio] = useState("");
  const [tituloPesq, setTituloPesq] = useState("");
  const [vinculo, setVinculo] = useState("");
  const [linhasPesq, setLinhasPesq] = useState("");
  const [grupoPesquisa, setGrupoPesquisa] = useState("");
  const [setor, setSetor] = useState("");
  const [cargoTec, setCargoTec] = useState("");
  const [anoConclusao, setAnoConclusao] = useState("");
  const [atuacao, setAtuacao] = useState("");

  const [isSaving, setIsSaving] = useState(false);
  const [success, setSuccess] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    if (!authLoading && !isAuthenticated) {
      router.push("/login");
    }
  }, [authLoading, isAuthenticated, router]);

  useEffect(() => {
    if (!user) return;
    setNome(user.nome || "");
    setNomeSocial(user.nome_social || "");
    setBio(user.bio || "");
    setPapel((user.papel as TipoPerfil) || "aluno");
    setInstituicao(user.instituicao || "");
    setCurso(user.curso || "");
    setDepartamento(user.departamento || "");
    setInteresses(user.interesses.join(", "));
    setHabilidades(user.habilidades.join(", "));

    if (user.dados_aluno) {
      setNivel(nivelAtual(user.dados_aluno.nivel));
      setSemestre(String(user.dados_aluno.semestre || 1));
      setOrientador(user.dados_aluno.orientador || "");
      setLinhaPesquisa(user.dados_aluno.linha_pesquisa || "");
    }
    if (user.dados_professor) {
      setTituloProf(user.dados_professor.titulo || "");
      setCargoProf(user.dados_professor.cargo || "");
      setLinhasProf(user.dados_professor.linhas_pesquisa?.join(", ") || "");
      setLaboratorio(user.dados_professor.laboratorio || "");
    }
    if (user.dados_pesquisador) {
      setTituloPesq(user.dados_pesquisador.titulo || "");
      setVinculo(user.dados_pesquisador.vinculo || "");
      setLinhasPesq(user.dados_pesquisador.linhas_pesquisa?.join(", ") || "");
      setGrupoPesquisa(user.dados_pesquisador.grupo_pesquisa || "");
    }
    if (user.dados_tecnico) {
      setSetor(user.dados_tecnico.setor || "");
      setCargoTec(user.dados_tecnico.cargo || "");
    }
    if (user.dados_egresso) {
      setAnoConclusao(user.dados_egresso.ano_conclusao ? String(user.dados_egresso.ano_conclusao) : "");
      setAtuacao(user.dados_egresso.atuacao || "");
    }
  }, [user]);

  function parseTagList(str: string): string[] {
    return str
      .split(",")
      .map((s) => s.trim())
      .filter(Boolean);
  }

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setError("");
    setSuccess(false);
    setIsSaving(true);

    try {
      const payload: Record<string, unknown> = {
        nome,
        nome_social: nomeSocial || null,
        bio: bio || null,
        papel,
        instituicao: instituicao || null,
        curso: curso || null,
        departamento: departamento || null,
        interesses: parseTagList(interesses),
        habilidades: parseTagList(habilidades),
      };

      if (papel === "aluno") {
        payload.dados_aluno = {
          nivel,
          semestre: periodo ? parseInt(semestre) || 1 : null,
          orientador: orientador || null,
          linha_pesquisa: linhaPesquisa || null,
        };
      } else if (papel === "professor") {
        payload.dados_professor = {
          titulo: tituloProf || null,
          cargo: cargoProf || null,
          linhas_pesquisa: parseTagList(linhasProf),
          laboratorio: laboratorio || null,
        };
      } else if (papel === "pesquisador") {
        payload.dados_pesquisador = {
          titulo: tituloPesq || null,
          vinculo: vinculo || null,
          linhas_pesquisa: parseTagList(linhasPesq),
          grupo_pesquisa: grupoPesquisa || null,
        };
      } else if (papel === "tecnico") {
        payload.dados_tecnico = { setor: setor || null, cargo: cargoTec || null };
      } else if (papel === "egresso") {
        payload.dados_egresso = {
          ano_conclusao: anoConclusao ? parseInt(anoConclusao) : null,
          atuacao: atuacao || null,
        };
      }

      await api.patch("/api/perfil", payload, { token: token || undefined });
      await refreshUser();
      setSuccess(true);
      setTimeout(() => setSuccess(false), 3000);
    } catch (err: unknown) {
      const apiErr = err as { detail?: string };
      setError(apiErr.detail || "Erro ao salvar perfil.");
    } finally {
      setIsSaving(false);
    }
  }

  if (authLoading || !user) {
    return (
      <div className={styles.pagina}>
        <div className={`skeleton ${styles.esqueleto}`} />
      </div>
    );
  }

  const perfilEscolhido = PERFIS.find((p) => p.value === papel);

  return (
    <div className={styles.pagina}>
      <header className={`ui-page-header ${styles.topo}`}>
        <Link href="/perfil" className={`ui-btn ui-btn-ghost ui-btn-sm ${styles.voltar}`}>
          <IconeVoltar />
          Voltar ao perfil
        </Link>
        <h1 className="ui-page-title">Editar perfil</h1>
        <p className="ui-page-subtitle">Atualize seus dados, seu vínculo e o que você quer mostrar à comunidade.</p>
      </header>

      <form onSubmit={handleSubmit} className={`ui-card ${styles.cartao}`}>
        {/* ── Dados pessoais ── */}
        <section className={styles.grupo} aria-labelledby="grupo-pessoais">
          <h2 id="grupo-pessoais" className={styles.grupoTitulo}>Dados pessoais</h2>
          <div className={styles.campos}>
            <div className={styles.campo}>
              <label htmlFor="edit-nome" className="ui-label">Nome</label>
              <input id="edit-nome" type="text" value={nome} onChange={(e) => setNome(e.target.value)} required minLength={2} maxLength={200} className="ui-field" autoComplete="name" />
            </div>
            <div className={styles.campo}>
              <label htmlFor="edit-nsocial" className="ui-label">Nome social</label>
              <input id="edit-nsocial" type="text" value={nomeSocial} onChange={(e) => setNomeSocial(e.target.value)} placeholder="Opcional" className="ui-field" />
            </div>
            <div className={`${styles.campo} ${styles.inteiro}`}>
              <label htmlFor="edit-email" className="ui-label">E-mail</label>
              <input id="edit-email" type="email" value={user.email} disabled className="ui-field" aria-describedby="edit-email-hint" />
              <p id="edit-email-hint" className="ui-hint">
                {user.email_pendente ? (
                  <>
                    Aguardando a confirmação de {user.email_pendente} pelo link enviado.{" "}
                    <Link href="/perfil/completar">Informar outro e-mail</Link>
                  </>
                ) : emailProvisorio(user.email) ? (
                  <>
                    E-mail provisório do ORCID. <Link href="/perfil/completar">Informar o e-mail institucional</Link>
                  </>
                ) : (
                  "O e-mail da conta não muda por aqui."
                )}
              </p>
              <label className={styles.caixa}>
                <input type="checkbox" checked={semEmailAcademico} onChange={(e) => setSemEmailAcademico(e.target.checked)} />
                <span>Não tenho e-mail acadêmico</span>
              </label>
              {semEmailAcademico && (
                <div className={styles.destaqueOrcid}>
                  <p>
                    Sem um e-mail acadêmico, o vínculo com a instituição é comprovado pela conta ORCID. Vincule a sua
                    conta ORCID a este perfil: você passa a entrar por ela e o perfil importa a formação e as publicações.
                  </p>
                  <button type="button" className="ui-btn ui-btn-primary" onClick={() => loginWithOrcid()}>
                    <IconeOrcid />
                    Vincular conta ORCID
                  </button>
                </div>
              )}
            </div>
            <div className={`${styles.campo} ${styles.inteiro}`}>
              <label htmlFor="edit-bio" className="ui-label">Sobre mim</label>
              <textarea id="edit-bio" value={bio} onChange={(e) => setBio(e.target.value)} rows={4} placeholder="Escreva um resumo sobre você" className="ui-field" maxLength={2000} />
              <p className={`ui-hint ${styles.contador}`}>{bio.length}/2000</p>
            </div>
          </div>
        </section>

        {/* ── Vínculo institucional ── */}
        <section className={styles.grupo} aria-labelledby="grupo-vinculo">
          <h2 id="grupo-vinculo" className={styles.grupoTitulo}>Vínculo institucional</h2>
          <div className={styles.campos}>
            <div className={styles.campo}>
              <label htmlFor="edit-papel" className="ui-label">Vínculo</label>
              <select id="edit-papel" value={papel} onChange={(e) => setPapel(e.target.value as TipoPerfil)} className="ui-field" aria-describedby="edit-papel-hint">
                {PERFIS.map((p) => <option key={p.value} value={p.value}>{p.label}</option>)}
              </select>
              {perfilEscolhido && <p id="edit-papel-hint" className="ui-hint">{perfilEscolhido.descricao}</p>}
            </div>
            <div className={styles.campo}>
              <label htmlFor="edit-inst" className="ui-label">Instituição</label>
              <input id="edit-inst" type="text" value={instituicao} onChange={(e) => setInstituicao(e.target.value)} placeholder="Ex.: UNIR, UNIRIO" maxLength={200} className="ui-field" autoComplete="organization" />
            </div>
            <div className={styles.campo}>
              <label htmlFor="edit-curso" className="ui-label">Curso</label>
              <input id="edit-curso" type="text" value={curso} onChange={(e) => setCurso(e.target.value)} placeholder="Ex.: Medicina" maxLength={200} className="ui-field" />
            </div>
            <div className={styles.campo}>
              <label htmlFor="edit-dep" className="ui-label">Departamento ou setor</label>
              <input id="edit-dep" type="text" value={departamento} onChange={(e) => setDepartamento(e.target.value)} placeholder="Ex.: Departamento de Medicina" maxLength={200} className="ui-field" />
            </div>
          </div>
        </section>

        {/* ── Dados específicos por vínculo ── */}
        {papel === "aluno" && (
          <section className={styles.grupo} aria-labelledby="grupo-discente">
            <h2 id="grupo-discente" className={styles.grupoTitulo}>Dados de discente</h2>
            <div className={styles.campos}>
              <div className={styles.campo}>
                <label htmlFor="edit-nivel" className="ui-label">Grau de instrução</label>
                <select id="edit-nivel" value={nivel} onChange={(e) => setNivel(e.target.value)} className="ui-field">
                  {NIVEIS.map((n) => <option key={n.value} value={n.value}>{n.label}</option>)}
                </select>
              </div>
              {periodo && (
                <div className={styles.campo}>
                  <label htmlFor="edit-sem" className="ui-label">{periodo.rotulo}</label>
                  <input id="edit-sem" type="number" value={semestre} onChange={(e) => setSemestre(e.target.value)} min="1" max={periodo.max} className="ui-field" inputMode="numeric" />
                </div>
              )}
              <div className={styles.campo}>
                <label htmlFor="edit-orient" className="ui-label">Orientador(a)</label>
                <input id="edit-orient" type="text" value={orientador} onChange={(e) => setOrientador(e.target.value)} placeholder="Prof. Dr. Fulano da Silva" className="ui-field" />
              </div>
              <div className={styles.campo}>
                <label htmlFor="edit-linha" className="ui-label">Linha de pesquisa</label>
                <input id="edit-linha" type="text" value={linhaPesquisa} onChange={(e) => setLinhaPesquisa(e.target.value)} placeholder="Bioinformática aplicada" className="ui-field" />
              </div>
            </div>
          </section>
        )}

        {papel === "professor" && (
          <section className={styles.grupo} aria-labelledby="grupo-docente">
            <h2 id="grupo-docente" className={styles.grupoTitulo}>Dados de docente</h2>
            <div className={styles.campos}>
              <div className={styles.campo}>
                <label htmlFor="edit-titulo" className="ui-label">Titulação</label>
                <input id="edit-titulo" type="text" value={tituloProf} onChange={(e) => setTituloProf(e.target.value)} placeholder="Dr., Me., PhD" className="ui-field" />
              </div>
              <div className={styles.campo}>
                <label htmlFor="edit-cargo" className="ui-label">Cargo</label>
                <input id="edit-cargo" type="text" value={cargoProf} onChange={(e) => setCargoProf(e.target.value)} placeholder="Professor associado" className="ui-field" />
              </div>
              <div className={`${styles.campo} ${styles.inteiro}`}>
                <label htmlFor="edit-linhas-prof" className="ui-label">Linhas de pesquisa</label>
                <input id="edit-linhas-prof" type="text" value={linhasProf} onChange={(e) => setLinhasProf(e.target.value)} placeholder="Separar por vírgula" className="ui-field" aria-describedby="edit-linhas-prof-hint" />
                <p id="edit-linhas-prof-hint" className="ui-hint">Separe as linhas por vírgula.</p>
              </div>
              <div className={`${styles.campo} ${styles.inteiro}`}>
                <label htmlFor="edit-lab" className="ui-label">Laboratório</label>
                <input id="edit-lab" type="text" value={laboratorio} onChange={(e) => setLaboratorio(e.target.value)} placeholder="Lab. de Bioinformática" className="ui-field" />
              </div>
            </div>
          </section>
        )}

        {papel === "pesquisador" && (
          <section className={styles.grupo} aria-labelledby="grupo-pesquisador">
            <h2 id="grupo-pesquisador" className={styles.grupoTitulo}>Dados de pesquisador(a)</h2>
            <div className={styles.campos}>
              <div className={styles.campo}>
                <label htmlFor="edit-titulo-pesq" className="ui-label">Titulação</label>
                <input id="edit-titulo-pesq" type="text" value={tituloPesq} onChange={(e) => setTituloPesq(e.target.value)} placeholder="Dr., PhD" className="ui-field" />
              </div>
              <div className={styles.campo}>
                <label htmlFor="edit-vinculo" className="ui-label">Vínculo</label>
                <input id="edit-vinculo" type="text" value={vinculo} onChange={(e) => setVinculo(e.target.value)} placeholder="Pós-doc, colaborador(a), visitante" className="ui-field" />
              </div>
              <div className={`${styles.campo} ${styles.inteiro}`}>
                <label htmlFor="edit-linhas-pesq" className="ui-label">Linhas de pesquisa</label>
                <input id="edit-linhas-pesq" type="text" value={linhasPesq} onChange={(e) => setLinhasPesq(e.target.value)} placeholder="Separar por vírgula" className="ui-field" aria-describedby="edit-linhas-pesq-hint" />
                <p id="edit-linhas-pesq-hint" className="ui-hint">Separe as linhas por vírgula.</p>
              </div>
              <div className={`${styles.campo} ${styles.inteiro}`}>
                <label htmlFor="edit-grupo" className="ui-label">Grupo de pesquisa</label>
                <input id="edit-grupo" type="text" value={grupoPesquisa} onChange={(e) => setGrupoPesquisa(e.target.value)} placeholder="GPBIO" className="ui-field" />
              </div>
            </div>
          </section>
        )}

        {papel === "tecnico" && (
          <section className={styles.grupo} aria-labelledby="grupo-tecnico">
            <h2 id="grupo-tecnico" className={styles.grupoTitulo}>Dados de técnico(a)-administrativo(a)</h2>
            <div className={styles.campos}>
              <div className={styles.campo}>
                <label htmlFor="edit-setor" className="ui-label">Setor</label>
                <input id="edit-setor" type="text" value={setor} onChange={(e) => setSetor(e.target.value)} placeholder="Ex.: Pró-Reitoria de Pesquisa" className="ui-field" />
              </div>
              <div className={styles.campo}>
                <label htmlFor="edit-cargo-tec" className="ui-label">Cargo</label>
                <input id="edit-cargo-tec" type="text" value={cargoTec} onChange={(e) => setCargoTec(e.target.value)} placeholder="Ex.: Técnico(a) de laboratório" className="ui-field" />
              </div>
            </div>
          </section>
        )}

        {papel === "egresso" && (
          <section className={styles.grupo} aria-labelledby="grupo-egresso">
            <h2 id="grupo-egresso" className={styles.grupoTitulo}>Dados de egresso(a)</h2>
            <div className={styles.campos}>
              <div className={styles.campo}>
                <label htmlFor="edit-ano" className="ui-label">Ano de conclusão</label>
                <input id="edit-ano" type="number" value={anoConclusao} onChange={(e) => setAnoConclusao(e.target.value)} min="1950" max="2100" className="ui-field" inputMode="numeric" />
              </div>
              <div className={styles.campo}>
                <label htmlFor="edit-atuacao" className="ui-label">Atuação atual</label>
                <input id="edit-atuacao" type="text" value={atuacao} onChange={(e) => setAtuacao(e.target.value)} placeholder="Ex.: Residência em Clínica Médica" className="ui-field" />
              </div>
            </div>
          </section>
        )}

        {/* ── Interesses e habilidades ── */}
        <section className={styles.grupo} aria-labelledby="grupo-tags">
          <h2 id="grupo-tags" className={styles.grupoTitulo}>Interesses e habilidades</h2>
          <p className={styles.grupoDescricao}>Aparecem como etiquetas no seu perfil e ajudam a comunidade a encontrar você.</p>
          <div className={styles.campos}>
            <div className={styles.campo}>
              <label htmlFor="edit-interesses" className="ui-label">Interesses</label>
              <input id="edit-interesses" type="text" value={interesses} onChange={(e) => setInteresses(e.target.value)} placeholder="Genômica, aprendizado de máquina, câncer" className="ui-field" aria-describedby="edit-interesses-hint" />
              <p id="edit-interesses-hint" className="ui-hint">Separe por vírgula.</p>
            </div>
            <div className={styles.campo}>
              <label htmlFor="edit-habilidades" className="ui-label">Habilidades</label>
              <input id="edit-habilidades" type="text" value={habilidades} onChange={(e) => setHabilidades(e.target.value)} placeholder="Python, R, MySQL" className="ui-field" aria-describedby="edit-habilidades-hint" />
              <p id="edit-habilidades-hint" className="ui-hint">Separe por vírgula.</p>
            </div>
          </div>
        </section>

        {/* ── Rodapé ── */}
        <div className={styles.rodape}>
          {error && <div className={`${styles.alerta} ${styles.alertaErro}`} role="alert">{error}</div>}
          {success && <div className={`${styles.alerta} ${styles.alertaSucesso}`} role="status">Perfil salvo.</div>}
          <div className={styles.acoes}>
            <Link href="/perfil" className="ui-btn ui-btn-ghost">Cancelar</Link>
            <button type="submit" disabled={isSaving} className="ui-btn ui-btn-primary">
              {isSaving ? "Salvando..." : "Salvar alterações"}
            </button>
          </div>
        </div>
      </form>
    </div>
  );
}
