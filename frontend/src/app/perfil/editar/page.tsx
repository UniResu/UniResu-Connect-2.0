"use client";

import { useState, useEffect, FormEvent } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { useAuth } from "@/contexts/AuthContext";
import { api } from "@/lib/api";
import { PERFIS, NIVEIS, PERIODO_POR_NIVEL, nivelAtual, type TipoPerfil, emailProvisorio } from "@/lib/perfis";
import styles from "./editar.module.css";

/**
 * Edição do perfil (mockup "Modal de Meu perfil" do Figma): dados pessoais,
 * vínculo institucional (que pode ser trocado), campos específicos do vínculo,
 * interesses e habilidades.
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
      <div className={styles.page}>
        <div className={styles.skeleton} style={{ height: 500 }} />
      </div>
    );
  }

  const perfilEscolhido = PERFIS.find((p) => p.value === papel);

  return (
    <div className={styles.page}>
      <div className={styles.headerRow}>
        <button onClick={() => router.push("/perfil")} className={styles.backBtn}>
          ← Voltar ao Perfil
        </button>
        <h1 className={styles.title}>Editar Perfil</h1>
      </div>

      <form onSubmit={handleSubmit} className={styles.form}>
        {error && <div className={styles.errorMsg}>{error}</div>}
        {success && <div className={styles.successMsg}>✅ Perfil salvo com sucesso!</div>}

        {/* ── Dados Pessoais ── */}
        <fieldset className={styles.section}>
          <legend className={styles.legend}>Dados Pessoais</legend>
          <div className={styles.fieldRow}>
            <div className={styles.field}>
              <label htmlFor="edit-nome">Nome</label>
              <input id="edit-nome" type="text" value={nome} onChange={(e) => setNome(e.target.value)} required minLength={2} maxLength={200} className={styles.input} />
            </div>
            <div className={styles.field}>
              <label htmlFor="edit-nsocial">Nome Social</label>
              <input id="edit-nsocial" type="text" value={nomeSocial} onChange={(e) => setNomeSocial(e.target.value)} placeholder="Opcional" className={styles.input} />
            </div>
          </div>
          <div className={styles.field}>
            <label htmlFor="edit-email">E-mail</label>
            <input id="edit-email" type="email" value={user.email} disabled className={styles.input} />
            <span className={styles.hint}>
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
            </span>
            <label className={styles.checkboxLinha}>
              <input type="checkbox" checked={semEmailAcademico} onChange={(e) => setSemEmailAcademico(e.target.checked)} />
              <span>Não tenho e-mail acadêmico</span>
            </label>
            {semEmailAcademico && (
              <div className={styles.avisoOrcid}>
                <p>
                  Sem um e-mail acadêmico, o vínculo com a instituição é comprovado pela conta ORCID. Vincule a sua
                  conta ORCID a este perfil: você passa a entrar por ela e o perfil importa a formação e as publicações.
                </p>
                <button type="button" className={styles.orcidBotao} onClick={() => loginWithOrcid()}>
                  Vincular conta ORCID
                </button>
              </div>
            )}
          </div>
          <div className={styles.field}>
            <label htmlFor="edit-bio">Sobre mim</label>
            <textarea id="edit-bio" value={bio} onChange={(e) => setBio(e.target.value)} rows={3} placeholder="Escreva um resumo sobre você..." className={styles.textarea} maxLength={2000} />
            <span className={styles.charCount}>{bio.length}/2000</span>
          </div>
        </fieldset>

        {/* ── Vínculo Institucional ── */}
        <fieldset className={styles.section}>
          <legend className={styles.legend}>Vínculo Institucional</legend>
          <div className={styles.fieldRow}>
            <div className={styles.field}>
              <label htmlFor="edit-papel">Vínculo</label>
              <select id="edit-papel" value={papel} onChange={(e) => setPapel(e.target.value as TipoPerfil)} className={styles.select}>
                {PERFIS.map((p) => <option key={p.value} value={p.value}>{p.label}</option>)}
              </select>
              {perfilEscolhido && <span className={styles.hint}>{perfilEscolhido.descricao}</span>}
            </div>
            <div className={styles.field}>
              <label htmlFor="edit-inst">Instituição</label>
              <input id="edit-inst" type="text" value={instituicao} onChange={(e) => setInstituicao(e.target.value)} placeholder="Ex.: UNIR, UNIRIO" maxLength={200} className={styles.input} />
            </div>
          </div>
          <div className={styles.fieldRow}>
            <div className={styles.field}>
              <label htmlFor="edit-curso">Curso</label>
              <input id="edit-curso" type="text" value={curso} onChange={(e) => setCurso(e.target.value)} placeholder="Ex.: Medicina" maxLength={200} className={styles.input} />
            </div>
            <div className={styles.field}>
              <label htmlFor="edit-dep">Departamento / Setor</label>
              <input id="edit-dep" type="text" value={departamento} onChange={(e) => setDepartamento(e.target.value)} placeholder="Ex.: Departamento de Medicina" maxLength={200} className={styles.input} />
            </div>
          </div>
        </fieldset>

        {/* ── Dados específicos por vínculo ── */}
        {papel === "aluno" && (
          <fieldset className={styles.section}>
            <legend className={styles.legend}>Dados de Discente</legend>
            <div className={styles.fieldRow}>
              <div className={styles.field}>
                <label htmlFor="edit-nivel">Grau de instrução</label>
                <select id="edit-nivel" value={nivel} onChange={(e) => setNivel(e.target.value)} className={styles.select}>
                  {NIVEIS.map((n) => <option key={n.value} value={n.value}>{n.label}</option>)}
                </select>
              </div>
              {periodo && (
                <div className={styles.field}>
                  <label htmlFor="edit-sem">{periodo.rotulo}</label>
                  <input id="edit-sem" type="number" value={semestre} onChange={(e) => setSemestre(e.target.value)} min="1" max={periodo.max} className={styles.input} />
                </div>
              )}
            </div>
            <div className={styles.field}>
              <label htmlFor="edit-orient">Orientador(a)</label>
              <input id="edit-orient" type="text" value={orientador} onChange={(e) => setOrientador(e.target.value)} placeholder="Prof. Dr. Fulano da Silva" className={styles.input} />
            </div>
            <div className={styles.field}>
              <label htmlFor="edit-linha">Linha de Pesquisa</label>
              <input id="edit-linha" type="text" value={linhaPesquisa} onChange={(e) => setLinhaPesquisa(e.target.value)} placeholder="Bioinformática Aplicada" className={styles.input} />
            </div>
          </fieldset>
        )}

        {papel === "professor" && (
          <fieldset className={styles.section}>
            <legend className={styles.legend}>Dados de Docente</legend>
            <div className={styles.fieldRow}>
              <div className={styles.field}>
                <label htmlFor="edit-titulo">Titulação</label>
                <input id="edit-titulo" type="text" value={tituloProf} onChange={(e) => setTituloProf(e.target.value)} placeholder="Dr., Me., PhD" className={styles.input} />
              </div>
              <div className={styles.field}>
                <label htmlFor="edit-cargo">Cargo</label>
                <input id="edit-cargo" type="text" value={cargoProf} onChange={(e) => setCargoProf(e.target.value)} placeholder="Professor Associado" className={styles.input} />
              </div>
            </div>
            <div className={styles.field}>
              <label htmlFor="edit-linhas-prof">Linhas de Pesquisa</label>
              <input id="edit-linhas-prof" type="text" value={linhasProf} onChange={(e) => setLinhasProf(e.target.value)} placeholder="Separar por vírgula" className={styles.input} />
            </div>
            <div className={styles.field}>
              <label htmlFor="edit-lab">Laboratório</label>
              <input id="edit-lab" type="text" value={laboratorio} onChange={(e) => setLaboratorio(e.target.value)} placeholder="Lab. de Bioinformática" className={styles.input} />
            </div>
          </fieldset>
        )}

        {papel === "pesquisador" && (
          <fieldset className={styles.section}>
            <legend className={styles.legend}>Dados de Pesquisador(a)</legend>
            <div className={styles.fieldRow}>
              <div className={styles.field}>
                <label htmlFor="edit-titulo-pesq">Titulação</label>
                <input id="edit-titulo-pesq" type="text" value={tituloPesq} onChange={(e) => setTituloPesq(e.target.value)} placeholder="Dr., PhD" className={styles.input} />
              </div>
              <div className={styles.field}>
                <label htmlFor="edit-vinculo">Vínculo</label>
                <input id="edit-vinculo" type="text" value={vinculo} onChange={(e) => setVinculo(e.target.value)} placeholder="Pós-doc, colaborador(a), visitante" className={styles.input} />
              </div>
            </div>
            <div className={styles.field}>
              <label htmlFor="edit-linhas-pesq">Linhas de Pesquisa</label>
              <input id="edit-linhas-pesq" type="text" value={linhasPesq} onChange={(e) => setLinhasPesq(e.target.value)} placeholder="Separar por vírgula" className={styles.input} />
            </div>
            <div className={styles.field}>
              <label htmlFor="edit-grupo">Grupo de Pesquisa</label>
              <input id="edit-grupo" type="text" value={grupoPesquisa} onChange={(e) => setGrupoPesquisa(e.target.value)} placeholder="GPBIO" className={styles.input} />
            </div>
          </fieldset>
        )}

        {papel === "tecnico" && (
          <fieldset className={styles.section}>
            <legend className={styles.legend}>Dados de Técnico(a)-administrativo(a)</legend>
            <div className={styles.fieldRow}>
              <div className={styles.field}>
                <label htmlFor="edit-setor">Setor</label>
                <input id="edit-setor" type="text" value={setor} onChange={(e) => setSetor(e.target.value)} placeholder="Ex.: Pró-Reitoria de Pesquisa" className={styles.input} />
              </div>
              <div className={styles.field}>
                <label htmlFor="edit-cargo-tec">Cargo</label>
                <input id="edit-cargo-tec" type="text" value={cargoTec} onChange={(e) => setCargoTec(e.target.value)} placeholder="Ex.: Técnico(a) de laboratório" className={styles.input} />
              </div>
            </div>
          </fieldset>
        )}

        {papel === "egresso" && (
          <fieldset className={styles.section}>
            <legend className={styles.legend}>Dados de Egresso(a)</legend>
            <div className={styles.fieldRow}>
              <div className={styles.field}>
                <label htmlFor="edit-ano">Ano de conclusão</label>
                <input id="edit-ano" type="number" value={anoConclusao} onChange={(e) => setAnoConclusao(e.target.value)} min="1950" max="2100" className={styles.input} />
              </div>
              <div className={styles.field}>
                <label htmlFor="edit-atuacao">Atuação atual</label>
                <input id="edit-atuacao" type="text" value={atuacao} onChange={(e) => setAtuacao(e.target.value)} placeholder="Ex.: Residência em Clínica Médica" className={styles.input} />
              </div>
            </div>
          </fieldset>
        )}

        {/* ── Tags ── */}
        <fieldset className={styles.section}>
          <legend className={styles.legend}>Interesses e Habilidades</legend>
          <div className={styles.field}>
            <label htmlFor="edit-interesses">Interesses</label>
            <input id="edit-interesses" type="text" value={interesses} onChange={(e) => setInteresses(e.target.value)} placeholder="Genômica, Machine Learning, Câncer" className={styles.input} />
            <span className={styles.hint}>Separar por vírgula</span>
          </div>
          <div className={styles.field}>
            <label htmlFor="edit-habilidades">Habilidades</label>
            <input id="edit-habilidades" type="text" value={habilidades} onChange={(e) => setHabilidades(e.target.value)} placeholder="Python, R, MySQL" className={styles.input} />
            <span className={styles.hint}>Separar por vírgula</span>
          </div>
        </fieldset>

        <button type="submit" disabled={isSaving} className={styles.saveButton}>
          {isSaving ? "Salvando..." : "Salvar Alterações"}
        </button>
      </form>
    </div>
  );
}
