"use client";

import { useState, FormEvent } from "react";
import Link from "next/link";
import { api } from "@/lib/api";
import { useAuth } from "@/contexts/AuthContext";
import { PERFIS, NIVEIS, PERIODO_POR_NIVEL, type TipoPerfil, emailInstitucionalValido } from "@/lib/perfis";
import { CODIGO_CONDUTA, CODIGO_CONDUTA_INTRODUCAO, CODIGO_CONDUTA_TITULO, DADOS_TEXTO, DADOS_TITULO } from "@/lib/codigoConduta";
import Modal from "@/components/ui/Modal";
import styles from "./registrar.module.css";

/**
 * Registro, seguindo o mockup "Modal de Registro" do Figma: um painel com
 * rótulo à esquerda e campo à direita (e-mail institucional, instituição,
 * nome completo, vínculo institucional), os campos específicos do vínculo
 * escolhido, senha, os dois aceites e o botão "Registrar-se".
 */
export default function RegistrarPage() {
  const { loginWithOrcid } = useAuth();

  const [nome, setNome] = useState("");
  const [email, setEmail] = useState("");
  const [senha, setSenha] = useState("");
  const [senhaConfirm, setSenhaConfirm] = useState("");
  const [papel, setPapel] = useState<TipoPerfil | "">("");
  const [instituicao, setInstituicao] = useState("");
  const [curso, setCurso] = useState("");
  const [departamento, setDepartamento] = useState("");

  // Campos por vínculo
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
  const [modal, setModal] = useState<"regras" | "dados" | null>(null);
  // Sem e-mail acadêmico, o registro é feito pela conta ORCID, que comprova o vínculo.
  const [semEmailAcademico, setSemEmailAcademico] = useState(false);

  const [error, setError] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [emailEnviado, setEmailEnviado] = useState("");

  const perfilEscolhido = PERFIS.find((p) => p.value === papel);

  function dadosDoVinculo(): Record<string, unknown> {
    switch (papel) {
      case "aluno":
        return { dados_aluno: { nivel, semestre: periodo ? parseInt(semestre, 10) || 1 : null } };
      case "professor":
        return { dados_professor: { titulo: titulo || null, cargo: cargo || null, linhas_pesquisa: [] } };
      case "pesquisador":
        return { dados_pesquisador: { titulo: titulo || null, vinculo: vinculoPesq || null, linhas_pesquisa: [] } };
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
    if (!emailInstitucionalValido(email)) {
      setError("Por favor, utilize o seu e-mail institucional acadêmico.");
      return;
    }
    if (senha !== senhaConfirm) {
      setError("As senhas não coincidem.");
      return;
    }
    if (senha.length < 6) {
      setError("A senha deve ter pelo menos 6 caracteres.");
      return;
    }
    if (!aceiteRegras || !aceiteDados) {
      setError("É preciso marcar os dois aceites para concluir o registro.");
      return;
    }

    setIsSubmitting(true);
    try {
      // Conta criada como pendente: um e-mail de verificação é enviado.
      await api.post("/api/usuarios/registrar", {
        nome,
        email,
        senha,
        papel,
        instituicao: instituicao || null,
        // só os campos que o vínculo escolhido mostra no formulário
        curso: papel === "aluno" || papel === "egresso" ? curso || null : null,
        departamento: papel === "professor" || papel === "pesquisador" ? departamento || null : null,
        aceite_regras: aceiteRegras,
        aceite_dados: aceiteDados,
        ...dadosDoVinculo(),
      });
      setEmailEnviado(email);
    } catch (err: unknown) {
      const apiErr = err as { detail?: unknown };
      const detail = apiErr.detail;
      setError(
        typeof detail === "string"
          ? detail
          : Array.isArray(detail)
            ? detail.map((d: { msg?: string }) => (d.msg || "").replace(/^Value error, /, "")).join(" ")
            : "Erro ao criar conta. Tente novamente."
      );
    } finally {
      setIsSubmitting(false);
    }
  }

  if (emailEnviado) {
    return (
      <div className={styles.page}>
        <div className={styles.card}>
          <div className={styles.emailConfirmation}>
            <h2 className={styles.emailTitle}>Verifique seu e-mail</h2>
            <p className={styles.emailText}>
              Enviamos um link de confirmação para <strong>{emailEnviado}</strong>.
            </p>
            <p className={styles.emailText}>
              Clique no link recebido para ativar sua conta. O link é válido por 24 horas.
            </p>
            <p className={styles.emailHint}>
              Não recebeu? Verifique a pasta de spam ou{" "}
              <button
                type="button"
                className={styles.resendLink}
                onClick={async () => {
                  try {
                    await api.post("/api/auth/reenviar-verificacao", { email: emailEnviado });
                    alert("E-mail reenviado com sucesso!");
                  } catch {
                    alert("Erro ao reenviar. Tente novamente em alguns minutos.");
                  }
                }}
              >
                reenvie o e-mail
              </button>.
            </p>
            <Link href="/login" className={styles.loginButton}>Ir para o Login</Link>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className={styles.page}>
      <div className={`${styles.card} ${styles.cardWide}`}>
        <div className={styles.topBar}>
          <h1 className={styles.title}>Registre-se</h1>
          <Link href="/login" className={styles.topLogin}>Login</Link>
        </div>

        <form onSubmit={handleSubmit} className={styles.form} noValidate>
          {error && <div className={styles.errorMessage}>{error}</div>}

          <div className={styles.panel}>
            {!semEmailAcademico && (
              <div className={styles.row}>
                <label htmlFor="reg-email" className={styles.rowLabel}>E-mail institucional</label>
                <input
                  id="reg-email"
                  type="email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  placeholder="voce@universidade.edu.br"
                  required
                  className={styles.rowInput}
                  autoComplete="email"
                />
              </div>
            )}
            <label className={`${styles.consent} ${styles.consentCompacto}`}>
              <input
                type="checkbox"
                checked={semEmailAcademico}
                onChange={(e) => setSemEmailAcademico(e.target.checked)}
              />
              <span>Não tenho e-mail acadêmico</span>
            </label>
            {semEmailAcademico && (
              <p className={styles.rowHint}>
                Sem um e-mail acadêmico, o registro é feito com a sua conta ORCID, que comprova o vínculo com a
                instituição. Use o botão &ldquo;Registrar com ORCID&rdquo; abaixo; depois você escolhe o vínculo e
                completa o perfil.
              </p>
            )}

            <div className={styles.row}>
              <label htmlFor="reg-inst" className={styles.rowLabel}>Instituição</label>
              <input
                id="reg-inst"
                type="text"
                value={instituicao}
                onChange={(e) => setInstituicao(e.target.value)}
                placeholder="Ex.: UNIR, UNIRIO, UFMG"
                className={styles.rowInput}
                autoComplete="organization"
              />
            </div>

            <div className={styles.row}>
              <label htmlFor="reg-nome" className={styles.rowLabel}>Nome completo</label>
              <input
                id="reg-nome"
                type="text"
                value={nome}
                onChange={(e) => setNome(e.target.value)}
                placeholder="Como aparece nos documentos"
                required
                minLength={2}
                className={styles.rowInput}
                autoComplete="name"
              />
            </div>

            <div className={styles.row}>
              <label htmlFor="reg-papel" className={styles.rowLabel}>Vínculo institucional</label>
              <select
                id="reg-papel"
                value={papel}
                onChange={(e) => setPapel(e.target.value as TipoPerfil)}
                required
                className={styles.rowInput}
              >
                <option value="">Escolha o seu vínculo</option>
                {PERFIS.map((p) => (
                  <option key={p.value} value={p.value}>{p.label}</option>
                ))}
              </select>
            </div>
            {perfilEscolhido && <p className={styles.rowHint}>{perfilEscolhido.descricao}</p>}

            {/* Campos específicos do vínculo: a pessoa só vê o que faz sentido para ela */}
            {papel === "aluno" && (
              <>
                <div className={styles.row}>
                  <label htmlFor="reg-curso" className={styles.rowLabel}>Curso</label>
                  <input id="reg-curso" type="text" value={curso} onChange={(e) => setCurso(e.target.value)}
                    placeholder="Ex.: Medicina" className={styles.rowInput} />
                </div>
                <div className={styles.row}>
                  <label htmlFor="reg-nivel" className={styles.rowLabel}>Grau de instrução</label>
                  <div className={styles.rowSplit}>
                    <select id="reg-nivel" value={nivel} onChange={(e) => setNivel(e.target.value)} className={styles.rowInput}>
                      {NIVEIS.map((n) => <option key={n.value} value={n.value}>{n.label}</option>)}
                    </select>
                    {periodo && (
                      <input
                        type="number"
                        value={semestre}
                        onChange={(e) => setSemestre(e.target.value)}
                        min={1}
                        max={periodo.max}
                        className={styles.rowInput}
                        aria-label={periodo.rotulo}
                        placeholder={`${periodo.rotulo} (1 a ${periodo.max})`}
                      />
                    )}
                  </div>
                </div>
              </>
            )}

            {papel === "professor" && (
              <>
                <div className={styles.row}>
                  <label htmlFor="reg-dep" className={styles.rowLabel}>Departamento</label>
                  <input id="reg-dep" type="text" value={departamento} onChange={(e) => setDepartamento(e.target.value)}
                    placeholder="Ex.: Departamento de Medicina" className={styles.rowInput} />
                </div>
                <div className={styles.row}>
                  <label htmlFor="reg-titulo" className={styles.rowLabel}>Titulação e cargo</label>
                  <div className={styles.rowSplit}>
                    <input id="reg-titulo" type="text" value={titulo} onChange={(e) => setTitulo(e.target.value)}
                      placeholder="Dr., Me., PhD" className={styles.rowInput} />
                    <input type="text" value={cargo} onChange={(e) => setCargo(e.target.value)}
                      placeholder="Ex.: Professor Adjunto" className={styles.rowInput} aria-label="Cargo" />
                  </div>
                </div>
              </>
            )}

            {papel === "pesquisador" && (
              <>
                <div className={styles.row}>
                  <label htmlFor="reg-dep-p" className={styles.rowLabel}>Departamento ou grupo</label>
                  <input id="reg-dep-p" type="text" value={departamento} onChange={(e) => setDepartamento(e.target.value)}
                    placeholder="Ex.: Laboratório de Bioinformática" className={styles.rowInput} />
                </div>
                <div className={styles.row}>
                  <label htmlFor="reg-titulo-p" className={styles.rowLabel}>Titulação e vínculo</label>
                  <div className={styles.rowSplit}>
                    <input id="reg-titulo-p" type="text" value={titulo} onChange={(e) => setTitulo(e.target.value)}
                      placeholder="Dr., PhD" className={styles.rowInput} />
                    <input type="text" value={vinculoPesq} onChange={(e) => setVinculoPesq(e.target.value)}
                      placeholder="Pós-doc, colaborador(a), visitante" className={styles.rowInput} aria-label="Vínculo" />
                  </div>
                </div>
              </>
            )}

            {papel === "tecnico" && (
              <div className={styles.row}>
                <label htmlFor="reg-setor" className={styles.rowLabel}>Setor e cargo</label>
                <div className={styles.rowSplit}>
                  <input id="reg-setor" type="text" value={setor} onChange={(e) => setSetor(e.target.value)}
                    placeholder="Ex.: Pró-Reitoria de Pesquisa" className={styles.rowInput} />
                  <input type="text" value={cargo} onChange={(e) => setCargo(e.target.value)}
                    placeholder="Ex.: Técnico(a) de laboratório" className={styles.rowInput} aria-label="Cargo" />
                </div>
              </div>
            )}

            {papel === "egresso" && (
              <>
                <div className={styles.row}>
                  <label htmlFor="reg-curso-e" className={styles.rowLabel}>Curso concluído</label>
                  <div className={styles.rowSplit}>
                    <input id="reg-curso-e" type="text" value={curso} onChange={(e) => setCurso(e.target.value)}
                      placeholder="Ex.: Enfermagem" className={styles.rowInput} />
                    <input type="number" value={anoConclusao} onChange={(e) => setAnoConclusao(e.target.value)}
                      min={1950} max={2100} placeholder="Ano" className={styles.rowInput} aria-label="Ano de conclusão" />
                  </div>
                </div>
                <div className={styles.row}>
                  <label htmlFor="reg-atuacao" className={styles.rowLabel}>Atuação atual</label>
                  <input id="reg-atuacao" type="text" value={atuacao} onChange={(e) => setAtuacao(e.target.value)}
                    placeholder="Ex.: Residência em Clínica Médica" className={styles.rowInput} />
                </div>
              </>
            )}

            {!semEmailAcademico && (
            <div className={styles.row}>
              <label htmlFor="reg-senha" className={styles.rowLabel}>Senha</label>
              <div className={styles.rowSplit}>
                <input
                  id="reg-senha"
                  type="password"
                  value={senha}
                  onChange={(e) => setSenha(e.target.value)}
                  placeholder="Mínimo 6 caracteres"
                  required
                  minLength={6}
                  className={styles.rowInput}
                  autoComplete="new-password"
                />
                <input
                  type="password"
                  value={senhaConfirm}
                  onChange={(e) => setSenhaConfirm(e.target.value)}
                  placeholder="Repita a senha"
                  required
                  className={styles.rowInput}
                  aria-label="Confirmar senha"
                  autoComplete="new-password"
                />
              </div>
            </div>
            )}
          </div>

          <div className={styles.consents}>
            <label className={styles.consent}>
              <input type="checkbox" checked={aceiteRegras} onChange={(e) => setAceiteRegras(e.target.checked)} />
              <span>
                Declaro, ao fazer o registro, que estou ciente das{" "}
                <button
                  type="button"
                  className={styles.linkBotao}
                  onClick={(e) => { e.preventDefault(); e.stopPropagation(); setModal("regras"); }}
                >
                  regras de utilização e convivência
                </button>{" "}
                da plataforma.
              </span>
            </label>
            <label className={styles.consent}>
              <input type="checkbox" checked={aceiteDados} onChange={(e) => setAceiteDados(e.target.checked)} />
              <span>
                Declaro, ao fazer o registro, que estou ciente do{" "}
                <button
                  type="button"
                  className={styles.linkBotao}
                  onClick={(e) => { e.preventDefault(); e.stopPropagation(); setModal("dados"); }}
                >
                  compartilhamento desses dados
                </button>{" "}
                com as coordenações dos projetos a que eu me candidatar.
              </span>
            </label>
          </div>

          {!semEmailAcademico && (
            <>
              <button type="submit" disabled={isSubmitting} className={styles.submitButton}>
                {isSubmitting ? "Criando conta..." : "Registrar-se"}
              </button>

              <div className={styles.divider}><span>ou</span></div>
            </>
          )}

          <button
            onClick={() => loginWithOrcid()}
            className={`${styles.orcidButton} ${semEmailAcademico ? styles.orcidDestaque : ""}`}
            type="button"
          >
            <img
              src="https://info.orcid.org/wp-content/uploads/2019/11/orcid_16x16.png"
              alt="ORCID"
              width={20}
              height={20}
            />
            Registrar com ORCID
          </button>
          <p className={styles.orcidHint}>
            Com o ORCID você entra sem senha e importa publicações e formação. Depois, escolhe o seu vínculo e
            informa o e-mail institucional.
          </p>

          <p className={styles.helpText}>
            Problemas com o e-mail institucional?{" "}
            <a
              href="https://docs.google.com/forms/d/e/1FAIpQLSeW8URrJsHN4S-d7k-bOvmibn99fMgMLpB-ynxs9QKKCSvkug/viewform?usp=header"
              target="_blank"
              rel="noopener noreferrer"
              className={styles.link}
            >
              Solicite acesso manual enviando o seu comprovante de vínculo.
            </a>
          </p>
        </form>

        <p className={styles.footer}>
          Já tem uma conta? <Link href="/login" className={styles.link}>Entrar</Link>
        </p>
      </div>

      <Modal aberto={modal === "regras"} titulo={CODIGO_CONDUTA_TITULO} onFechar={() => setModal(null)}>
        <p>{CODIGO_CONDUTA_INTRODUCAO}</p>
        <ol>
          {CODIGO_CONDUTA.map((item) => <li key={item}>{item}</li>)}
        </ol>
      </Modal>
      <Modal aberto={modal === "dados"} titulo={DADOS_TITULO} onFechar={() => setModal(null)}>
        {DADOS_TEXTO.map((p) => <p key={p}>{p}</p>)}
      </Modal>
    </div>
  );
}
