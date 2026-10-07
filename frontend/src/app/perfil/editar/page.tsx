"use client";

import { useState, useEffect, FormEvent } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/contexts/AuthContext";
import { api } from "@/lib/api";
import { PERFIS, NIVEIS, type TipoPerfil, type DadosTecnico, type DadosEgresso } from "@/lib/perfis";
import styles from "./editar.module.css";

/**
 * Edição do perfil (mockup "Modal de Meu perfil" do Figma): dados pessoais,
 * vínculo institucional (que pode ser trocado), campos específicos do vínculo,
 * interesses e habilidades.
 */
export default function EditarPerfilPage() {
  const { user, token, isAuthenticated, isLoading: authLoading, refreshUser } = useAuth();
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

  // Dados específicos por vínculo
  const [nivel, setNivel] = useState("graduacao");
  const [semestre, setSemestre] = useState("1");
  const [orientador, setOrientador] = useState("");
  const [linhaPesquisa, setLinhaPesquisa] = useState("");
  const [linhasPesquisa, setLinhasPesquisa] = useState("");
  const [laboratorio, setLaboratorio] = useState("");
  const [grupoPesquisa, setGrupoPesquisa] = useState("");
  const [titulo, setTitulo] = useState("");
  const [cargo, setCargo] = useState("");
  const [vinculo, setVinculo] = useState("");
  const [setor, setSetor] = useState("");
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
    const extra = user as typeof user & { dados_tecnico?: DadosTecnico | null; dados_egresso?: DadosEgresso | null };
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
      setNivel(user.dados_aluno.nivel || "graduacao");
      setSemestre(String(user.dados_aluno.semestre || 1));
      setOrientador(user.dados_aluno.orientador || "");
      setLinhaPesquisa(user.dados_aluno.linha_pesquisa || "");
    }
    if (user.dados_professor) {
      setTitulo(user.dados_professor.titulo || "");
      setCargo(user.dados_professor.cargo || "");
      setLinhasPesquisa(user.dados_professor.linhas_pesquisa?.join(", ") || "");
      setLaboratorio(user.dados_professor.laboratorio || "");
    }
    if (user.dados_pesquisador) {
      setTitulo(user.dados_pesquisador.titulo || "");
      setVinculo(user.dados_pesquisador.vinculo || "");
      setLinhasPesquisa(user.dados_pesquisador.linhas_pesquisa?.join(", ") || "");
      setGrupoPesquisa(user.dados_pesquisador.grupo_pesquisa || "");
    }
    if (extra.dados_tecnico) {
      setSetor(extra.dados_tecnico.setor || "");
      setCargo(extra.dados_tecnico.cargo || "");
    }
    if (extra.dados_egresso) {
      setAnoConclusao(extra.dados_egresso.ano_conclusao ? String(extra.dados_egresso.ano_conclusao) : "");
      setAtuacao(extra.dados_egresso.atuacao || "");
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
          semestre: parseInt(semestre) || 1,
          orientador: orientador || null,
          linha_pesquisa: linhaPesquisa || null,
        };
      } else if (papel === "professor") {
        payload.dados_professor = {
          titulo: titulo || null,
          cargo: cargo || null,
          linhas_pesquisa: parseTagList(linhasPesquisa),
          laboratorio: laboratorio || null,
        };
      } else if (papel === "pesquisador") {
        payload.dados_pesquisador = {
          titulo: titulo || null,
          vinculo: vinculo || null,
          linhas_pesquisa: parseTagList(linhasPesquisa),
          grupo_pesquisa: grupoPesquisa || null,
        };
      } else if (papel === "tecnico") {
        payload.dados_tecnico = { setor: setor || null, cargo: cargo || null };
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
              <input id="edit-nome" type="text" value={nome} onChange={(e) => setNome(e.target.value)} required className={styles.input} />
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
              {user.email_pendente
                ? `Aguardando a confirmação de ${user.email_pendente} pelo link enviado.`
                : "O e-mail da conta não muda por aqui."}
            </span>
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
              <input id="edit-inst" type="text" value={instituicao} onChange={(e) => setInstituicao(e.target.value)} placeholder="Ex.: UNIR, UNIRIO" className={styles.input} />
            </div>
          </div>
          <div className={styles.fieldRow}>
            <div className={styles.field}>
              <label htmlFor="edit-curso">Curso</label>
              <input id="edit-curso" type="text" value={curso} onChange={(e) => setCurso(e.target.value)} placeholder="Ex.: Medicina" className={styles.input} />
            </div>
            <div className={styles.field}>
              <label htmlFor="edit-dep">Departamento / Setor</label>
              <input id="edit-dep" type="text" value={departamento} onChange={(e) => setDepartamento(e.target.value)} placeholder="Ex.: Departamento de Medicina" className={styles.input} />
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
              <div className={styles.field}>
                <label htmlFor="edit-sem">Período</label>
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

        {papel === "professor" && (
          <fieldset className={styles.section}>
            <legend className={styles.legend}>Dados de Docente</legend>
            <div className={styles.fieldRow}>
              <div className={styles.field}>
                <label htmlFor="edit-titulo">Titulação</label>
                <input id="edit-titulo" type="text" value={titulo} onChange={(e) => setTitulo(e.target.value)} placeholder="Dr., Me., PhD" className={styles.input} />
              </div>
              <div className={styles.field}>
                <label htmlFor="edit-cargo">Cargo</label>
                <input id="edit-cargo" type="text" value={cargo} onChange={(e) => setCargo(e.target.value)} placeholder="Professor Associado" className={styles.input} />
              </div>
            </div>
            <div className={styles.field}>
              <label htmlFor="edit-linhas-prof">Linhas de Pesquisa</label>
              <input id="edit-linhas-prof" type="text" value={linhasPesquisa} onChange={(e) => setLinhasPesquisa(e.target.value)} placeholder="Separar por vírgula" className={styles.input} />
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
                <input id="edit-titulo-pesq" type="text" value={titulo} onChange={(e) => setTitulo(e.target.value)} placeholder="Dr., PhD" className={styles.input} />
              </div>
              <div className={styles.field}>
                <label htmlFor="edit-vinculo">Vínculo</label>
                <input id="edit-vinculo" type="text" value={vinculo} onChange={(e) => setVinculo(e.target.value)} placeholder="Pós-doc, colaborador(a), visitante" className={styles.input} />
              </div>
            </div>
            <div className={styles.field}>
              <label htmlFor="edit-linhas-pesq">Linhas de Pesquisa</label>
              <input id="edit-linhas-pesq" type="text" value={linhasPesquisa} onChange={(e) => setLinhasPesquisa(e.target.value)} placeholder="Separar por vírgula" className={styles.input} />
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
                <input id="edit-cargo-tec" type="text" value={cargo} onChange={(e) => setCargo(e.target.value)} placeholder="Ex.: Técnico(a) de laboratório" className={styles.input} />
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
