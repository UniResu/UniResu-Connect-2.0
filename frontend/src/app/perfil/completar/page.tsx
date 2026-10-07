"use client";

import { useEffect, useState, FormEvent } from "react";
import { useRouter } from "next/navigation";
import { api } from "@/lib/api";
import { useAuth } from "@/contexts/AuthContext";
import { PERFIS, NIVEIS, type TipoPerfil, emailInstitucionalValido, emailProvisorio, PERIODO_POR_NIVEL } from "@/lib/perfis";
import styles from "../../registrar/registrar.module.css";

/**
 * Completar o perfil depois do login via ORCID.
 *
 * O ORCID não diz se a pessoa é discente, docente ou pesquisador(a), e a conta
 * nasce com um e-mail provisório. Aqui ela escolhe o vínculo, informa o e-mail
 * institucional e a instituição, e só então segue para o perfil.
 */
export default function CompletarPerfilPage() {
  const { user, token, isAuthenticated, isLoading, refreshUser } = useAuth();
  const router = useRouter();

  const [papel, setPapel] = useState<TipoPerfil | "">("");
  const [email, setEmail] = useState("");
  const [instituicao, setInstituicao] = useState("");
  const [curso, setCurso] = useState("");
  const [departamento, setDepartamento] = useState("");
  const [nivel, setNivel] = useState("graduacao_incompleta");
  const [semestre, setSemestre] = useState("1");
  const periodo = PERIODO_POR_NIVEL[nivel];
  const [titulo, setTitulo] = useState("");
  const [cargo, setCargo] = useState("");
  const [vinculoPesq, setVinculoPesq] = useState("");
  const [setor, setSetor] = useState("");
  const [anoConclusao, setAnoConclusao] = useState("");
  const [atuacao, setAtuacao] = useState("");
  const [aceiteRegras, setAceiteRegras] = useState(false);
  const [aceiteDados, setAceiteDados] = useState(false);
  const [error, setError] = useState("");
  const [salvando, setSalvando] = useState(false);
  const [preenchido, setPreenchido] = useState(false);

  useEffect(() => {
    if (!isLoading && !isAuthenticated) router.push("/login");
  }, [isLoading, isAuthenticated, router]);

  // Pré-preenche uma vez com o que o ORCID já trouxe (instituição de afiliação)
  // e, para quem já concluiu o perfil e só veio corrigir o e-mail, com o
  // vínculo e os aceites já registrados.
  useEffect(() => {
    if (user && !preenchido) {
      setInstituicao(user.instituicao || "");
      setCurso(user.curso || "");
      setDepartamento(user.departamento || "");
      if (user.perfil_completo !== false) {
        setPapel(user.papel);
        setAceiteRegras(!!user.aceite_regras);
        setAceiteDados(!!user.aceite_dados);
        setEmail(user.email_pendente || "");
      }
      setPreenchido(true);
    }
  }, [user, preenchido]);

  if (isLoading || !user) {
    return (
      <div className={styles.page}>
        <div className={styles.card}><p className={styles.subtitle}>Carregando...</p></div>
      </div>
    );
  }

  const precisaEmail = emailProvisorio(user.email);
  const perfilEscolhido = PERFIS.find((p) => p.value === papel);

  function dadosDoVinculo(): Record<string, unknown> {
    switch (papel) {
      case "aluno":
        return { dados_aluno: { nivel, semestre: periodo ? parseInt(semestre, 10) || 1 : null } };
      case "professor":
        return { dados_professor: { titulo: titulo || null, cargo: cargo || null } };
      case "pesquisador":
        return { dados_pesquisador: { titulo: titulo || null, vinculo: vinculoPesq || null } };
      case "tecnico":
        return { dados_tecnico: { setor: setor || null, cargo: cargo || null } };
      case "egresso":
        return { dados_egresso: { ano_conclusao: anoConclusao ? parseInt(anoConclusao, 10) : null, atuacao: atuacao || null } };
      default:
        return {};
    }
  }

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setError("");
    if (!papel) {
      setError("Escolha o seu vínculo institucional.");
      return;
    }
    if (precisaEmail && !emailInstitucionalValido(email)) {
      setError("Informe o seu e-mail institucional acadêmico.");
      return;
    }
    if (!aceiteRegras || !aceiteDados) {
      setError("É preciso marcar os dois aceites para concluir.");
      return;
    }
    setSalvando(true);
    try {
      await api.patch(
        "/api/perfil",
        {
          papel,
          instituicao: instituicao || null,
          // só os campos que o vínculo escolhido mostra no formulário
          curso: papel === "aluno" || papel === "egresso" ? curso || null : null,
          departamento: papel === "professor" || papel === "pesquisador" ? departamento || null : null,
          ...(precisaEmail ? { email } : {}),
          aceite_regras: aceiteRegras,
          aceite_dados: aceiteDados,
          perfil_completo: true,
          ...dadosDoVinculo(),
        },
        { token: token || undefined }
      );
      await refreshUser();
      router.push("/perfil");
    } catch (err: unknown) {
      const apiErr = err as { detail?: unknown };
      const detail = apiErr.detail;
      setError(
        typeof detail === "string"
          ? detail
          : Array.isArray(detail)
            ? detail.map((d: { msg?: string }) => (d.msg || "").replace(/^Value error, /, "")).join(" ")
            : "Não foi possível salvar. Tente novamente."
      );
    } finally {
      setSalvando(false);
    }
  }

  return (
    <div className={styles.page}>
      <div className={`${styles.card} ${styles.cardWide}`}>
        <div className={styles.topBar}>
          <h1 className={styles.title}>Complete seu perfil</h1>
        </div>
        <p className={styles.subtitle} style={{ textAlign: "left", marginBottom: "1rem" }}>
          Olá, {user.nome_social || user.nome}. Seu ORCID já está vinculado. Falta dizer qual é o seu vínculo
          institucional{precisaEmail ? " e o seu e-mail institucional" : ""}.
        </p>

        <form onSubmit={handleSubmit} className={styles.form} noValidate>
          {error && <div className={styles.errorMessage}>{error}</div>}

          <div className={styles.panel}>
            {precisaEmail && (
              <div className={styles.row}>
                <label htmlFor="cp-email" className={styles.rowLabel}>E-mail institucional</label>
                <input id="cp-email" type="email" value={email} onChange={(e) => setEmail(e.target.value)}
                  placeholder="voce@universidade.edu.br" required className={styles.rowInput} autoComplete="email" />
              </div>
            )}

            <div className={styles.row}>
              <label htmlFor="cp-inst" className={styles.rowLabel}>Instituição</label>
              <input id="cp-inst" type="text" value={instituicao} onChange={(e) => setInstituicao(e.target.value)}
                placeholder="Ex.: UNIR, UNIRIO, UFMG" className={styles.rowInput} />
            </div>

            <div className={styles.row}>
              <label htmlFor="cp-papel" className={styles.rowLabel}>Vínculo institucional</label>
              <select id="cp-papel" value={papel} onChange={(e) => setPapel(e.target.value as TipoPerfil)} required className={styles.rowInput}>
                <option value="">Escolha o seu vínculo</option>
                {PERFIS.map((p) => <option key={p.value} value={p.value}>{p.label}</option>)}
              </select>
            </div>
            {perfilEscolhido && <p className={styles.rowHint}>{perfilEscolhido.descricao}</p>}

            {papel === "aluno" && (
              <>
                <div className={styles.row}>
                  <label htmlFor="cp-curso" className={styles.rowLabel}>Curso</label>
                  <input id="cp-curso" type="text" value={curso} onChange={(e) => setCurso(e.target.value)} className={styles.rowInput} />
                </div>
                <div className={styles.row}>
                  <label htmlFor="cp-nivel" className={styles.rowLabel}>Grau de instrução</label>
                  <div className={styles.rowSplit}>
                    <select id="cp-nivel" value={nivel} onChange={(e) => setNivel(e.target.value)} className={styles.rowInput}>
                      {NIVEIS.map((n) => <option key={n.value} value={n.value}>{n.label}</option>)}
                    </select>
                    {periodo && (
                      <input type="number" value={semestre} onChange={(e) => setSemestre(e.target.value)} min={1}
                        max={periodo.max} className={styles.rowInput} aria-label={periodo.rotulo}
                        placeholder={`${periodo.rotulo} (1 a ${periodo.max})`} />
                    )}
                  </div>
                </div>
              </>
            )}

            {(papel === "professor" || papel === "pesquisador") && (
              <>
                <div className={styles.row}>
                  <label htmlFor="cp-dep" className={styles.rowLabel}>Departamento ou grupo</label>
                  <input id="cp-dep" type="text" value={departamento} onChange={(e) => setDepartamento(e.target.value)} className={styles.rowInput} />
                </div>
                <div className={styles.row}>
                  <label htmlFor="cp-titulo" className={styles.rowLabel}>
                    {papel === "professor" ? "Titulação e cargo" : "Titulação e vínculo"}
                  </label>
                  <div className={styles.rowSplit}>
                    <input id="cp-titulo" type="text" value={titulo} onChange={(e) => setTitulo(e.target.value)}
                      placeholder="Dr., Me., PhD" className={styles.rowInput} />
                    {papel === "professor" ? (
                      <input type="text" value={cargo} onChange={(e) => setCargo(e.target.value)}
                        placeholder="Ex.: Professor Adjunto" className={styles.rowInput} aria-label="Cargo" />
                    ) : (
                      <input type="text" value={vinculoPesq} onChange={(e) => setVinculoPesq(e.target.value)}
                        placeholder="Pós-doc, colaborador(a), visitante" className={styles.rowInput} aria-label="Vínculo" />
                    )}
                  </div>
                </div>
              </>
            )}

            {papel === "tecnico" && (
              <div className={styles.row}>
                <label htmlFor="cp-setor" className={styles.rowLabel}>Setor e cargo</label>
                <div className={styles.rowSplit}>
                  <input id="cp-setor" type="text" value={setor} onChange={(e) => setSetor(e.target.value)}
                    placeholder="Ex.: Pró-Reitoria de Pesquisa" className={styles.rowInput} />
                  <input type="text" value={cargo} onChange={(e) => setCargo(e.target.value)}
                    placeholder="Ex.: Técnico(a) de laboratório" className={styles.rowInput} aria-label="Cargo" />
                </div>
              </div>
            )}

            {papel === "egresso" && (
              <>
                <div className={styles.row}>
                  <label htmlFor="cp-curso-e" className={styles.rowLabel}>Curso concluído</label>
                  <div className={styles.rowSplit}>
                    <input id="cp-curso-e" type="text" value={curso} onChange={(e) => setCurso(e.target.value)} className={styles.rowInput} />
                    <input type="number" value={anoConclusao} onChange={(e) => setAnoConclusao(e.target.value)}
                      min={1950} max={2100} placeholder="Ano" className={styles.rowInput} aria-label="Ano de conclusão" />
                  </div>
                </div>
                <div className={styles.row}>
                  <label htmlFor="cp-atuacao" className={styles.rowLabel}>Atuação atual</label>
                  <input id="cp-atuacao" type="text" value={atuacao} onChange={(e) => setAtuacao(e.target.value)} className={styles.rowInput} />
                </div>
              </>
            )}
          </div>

          <div className={styles.consents}>
            <label className={styles.consent}>
              <input type="checkbox" checked={aceiteRegras} onChange={(e) => setAceiteRegras(e.target.checked)} />
              <span>Declaro que estou ciente das regras de utilização e convivência da plataforma.</span>
            </label>
            <label className={styles.consent}>
              <input type="checkbox" checked={aceiteDados} onChange={(e) => setAceiteDados(e.target.checked)} />
              <span>Declaro que estou ciente do compartilhamento desses dados com as coordenações dos projetos a que eu me candidatar.</span>
            </label>
          </div>

          <button type="submit" disabled={salvando} className={styles.submitButton}>
            {salvando ? "Salvando..." : "Concluir"}
          </button>
        </form>
      </div>
    </div>
  );
}
