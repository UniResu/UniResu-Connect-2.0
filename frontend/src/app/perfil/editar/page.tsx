"use client";

import { useState, useEffect, FormEvent } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/contexts/AuthContext";
import { api } from "@/lib/api";
import { NIVEL_LABELS } from "@/lib/constants";
import styles from "./editar.module.css";

export default function EditarPerfilPage() {
  const { user, token, isAuthenticated, isLoading: authLoading, refreshUser } = useAuth();
  const router = useRouter();

  const [nome, setNome] = useState("");
  const [nomeSocial, setNomeSocial] = useState("");
  const [bio, setBio] = useState("");
  const [instituicao, setInstituicao] = useState("");
  const [curso, setCurso] = useState("");
  const [interesses, setInteresses] = useState("");
  const [habilidades, setHabilidades] = useState("");

  // Dados específicos
  const [nivel, setNivel] = useState("graduacao");
  const [semestre, setSemestre] = useState("1");
  const [orientador, setOrientador] = useState("");
  const [linhaPesquisa, setLinhaPesquisa] = useState("");
  const [laboratorio, setLaboratorio] = useState("");
  const [grupoPesquisa, setGrupoPesquisa] = useState("");
  const [titulo, setTitulo] = useState("");
  const [cargo, setCargo] = useState("");
  const [vinculo, setVinculo] = useState("");

  const [isSaving, setIsSaving] = useState(false);
  const [success, setSuccess] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    if (!authLoading && !isAuthenticated) {
      router.push("/login");
    }
  }, [authLoading, isAuthenticated, router]);

  useEffect(() => {
    if (user) {
      setNome(user.nome || "");
      setNomeSocial(user.nome_social || "");
      setBio(user.bio || "");
      setInstituicao(user.instituicao || "");
      setCurso(user.curso || "");
      setInteresses(user.interesses.join(", "));
      setHabilidades(user.habilidades.join(", "));

      if (user.dados_aluno) {
        setNivel(user.dados_aluno.nivel || "graduacao");
        setSemestre(String(user.dados_aluno.semestre || 1));
        setOrientador(user.dados_aluno.orientador || "");
        setLinhaPesquisa(user.dados_aluno.linha_pesquisa || "");
      }
      if (user.dados_professor) {
        setTitulo(user.dados_professor.titulo || "");
        setCargo(user.dados_professor.cargo || "");
        setLabhaPesquisaProf(user.dados_professor.linhas_pesquisa?.join(", ") || "");
        setLaboratorio(user.dados_professor.laboratorio || "");
      }
      if (user.dados_pesquisador) {
        setTitulo(user.dados_pesquisador.titulo || "");
        setVinculo(user.dados_pesquisador.vinculo || "");
        setGrupoPesquisa(user.dados_pesquisador.grupo_pesquisa || "");
      }
    }
  }, [user]);

  const [linhaPesquisaProf, setLabhaPesquisaProf] = useState("");

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
        instituicao: instituicao || null,
        curso: curso || null,
        interesses: parseTagList(interesses),
        habilidades: parseTagList(habilidades),
      };

      if (user?.papel === "aluno") {
        payload.dados_aluno = {
          nivel,
          semestre: parseInt(semestre) || 1,
          orientador: orientador || null,
          linha_pesquisa: linhaPesquisa || null,
        };
      } else if (user?.papel === "professor") {
        payload.dados_professor = {
          titulo: titulo || null,
          cargo: cargo || null,
          linhas_pesquisa: parseTagList(linhaPesquisaProf),
          laboratorio: laboratorio || null,
        };
      } else if (user?.papel === "pesquisador") {
        payload.dados_pesquisador = {
          titulo: titulo || null,
          vinculo: vinculo || null,
          linhas_pesquisa: parseTagList(linhaPesquisaProf),
          grupo_pesquisa: grupoPesquisa || null,
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
              <input id="edit-nome" type="text" value={nome} onChange={(e) => setNome(e.target.value)} required className={styles.input} />
            </div>
            <div className={styles.field}>
              <label htmlFor="edit-nsocial">Nome Social</label>
              <input id="edit-nsocial" type="text" value={nomeSocial} onChange={(e) => setNomeSocial(e.target.value)} placeholder="Opcional" className={styles.input} />
            </div>
          </div>
          <div className={styles.field}>
            <label htmlFor="edit-bio">Sobre mim</label>
            <textarea id="edit-bio" value={bio} onChange={(e) => setBio(e.target.value)} rows={3} placeholder="Escreva um resumo sobre você..." className={styles.textarea} maxLength={2000} />
            <span className={styles.charCount}>{bio.length}/2000</span>
          </div>
        </fieldset>

        {/* ── Vínculo Acadêmico ── */}
        <fieldset className={styles.section}>
          <legend className={styles.legend}>Vínculo Acadêmico</legend>
          <div className={styles.fieldRow}>
            <div className={styles.field}>
              <label htmlFor="edit-inst">Instituição</label>
              <input id="edit-inst" type="text" value={instituicao} onChange={(e) => setInstituicao(e.target.value)} className={styles.input} />
            </div>
            <div className={styles.field}>
              <label htmlFor="edit-curso">Curso / Departamento</label>
              <input id="edit-curso" type="text" value={curso} onChange={(e) => setCurso(e.target.value)} className={styles.input} />
            </div>
          </div>
        </fieldset>

        {/* ── Dados Específicos por Papel ── */}
        {user.papel === "aluno" && (
          <fieldset className={styles.section}>
            <legend className={styles.legend}>🎓 Dados do Aluno</legend>
            <div className={styles.fieldRow}>
              <div className={styles.field}>
                <label htmlFor="edit-nivel">Nível</label>
                <select id="edit-nivel" value={nivel} onChange={(e) => setNivel(e.target.value)} className={styles.select}>
                  <option value="graduacao">Graduação</option>
                  <option value="mestrado">Mestrado</option>
                  <option value="doutorado">Doutorado</option>
                </select>
              </div>
              <div className={styles.field}>
                <label htmlFor="edit-sem">Semestre</label>
                <input id="edit-sem" type="number" value={semestre} onChange={(e) => setSemestre(e.target.value)} min="1" max="100" className={styles.input} />
              </div>
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

        {user.papel === "professor" && (
          <fieldset className={styles.section}>
            <legend className={styles.legend}>👨‍🏫 Dados do Professor</legend>
            <div className={styles.fieldRow}>
              <div className={styles.field}>
                <label htmlFor="edit-titulo">Título</label>
                <input id="edit-titulo" type="text" value={titulo} onChange={(e) => setTitulo(e.target.value)} placeholder="Dr., Me., PhD" className={styles.input} />
              </div>
              <div className={styles.field}>
                <label htmlFor="edit-cargo">Cargo</label>
                <input id="edit-cargo" type="text" value={cargo} onChange={(e) => setCargo(e.target.value)} placeholder="Professor Associado" className={styles.input} />
              </div>
            </div>
            <div className={styles.field}>
              <label htmlFor="edit-linhas-prof">Linhas de Pesquisa</label>
              <input id="edit-linhas-prof" type="text" value={linhaPesquisaProf} onChange={(e) => setLabhaPesquisaProf(e.target.value)} placeholder="Separar por vírgula" className={styles.input} />
            </div>
            <div className={styles.field}>
              <label htmlFor="edit-lab">Laboratório</label>
              <input id="edit-lab" type="text" value={laboratorio} onChange={(e) => setLaboratorio(e.target.value)} placeholder="Lab. de Bioinformática" className={styles.input} />
            </div>
          </fieldset>
        )}

        {user.papel === "pesquisador" && (
          <fieldset className={styles.section}>
            <legend className={styles.legend}>🔬 Dados do Pesquisador</legend>
            <div className={styles.fieldRow}>
              <div className={styles.field}>
                <label htmlFor="edit-titulo-pesq">Título</label>
                <input id="edit-titulo-pesq" type="text" value={titulo} onChange={(e) => setTitulo(e.target.value)} placeholder="Dr., PhD" className={styles.input} />
              </div>
              <div className={styles.field}>
                <label htmlFor="edit-vinculo">Vínculo</label>
                <input id="edit-vinculo" type="text" value={vinculo} onChange={(e) => setVinculo(e.target.value)} placeholder="Pós-Doc, Colaborador" className={styles.input} />
              </div>
            </div>
            <div className={styles.field}>
              <label htmlFor="edit-linhas-pesq">Linhas de Pesquisa</label>
              <input id="edit-linhas-pesq" type="text" value={linhaPesquisaProf} onChange={(e) => setLabhaPesquisaProf(e.target.value)} placeholder="Separar por vírgula" className={styles.input} />
            </div>
            <div className={styles.field}>
              <label htmlFor="edit-grupo">Grupo de Pesquisa</label>
              <input id="edit-grupo" type="text" value={grupoPesquisa} onChange={(e) => setGrupoPesquisa(e.target.value)} placeholder="GPBIO" className={styles.input} />
            </div>
          </fieldset>
        )}

        {/* ── Tags ── */}
        <fieldset className={styles.section}>
          <legend className={styles.legend}>Tags & Habilidades</legend>
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
