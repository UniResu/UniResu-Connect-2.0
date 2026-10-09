"use client";

import { useState, FormEvent } from "react";
import Link from "next/link";
import { api } from "@/lib/api";
import { useAuth } from "@/contexts/AuthContext";
import { PERFIS, NIVEIS, PERIODO_POR_NIVEL, type TipoPerfil, emailInstitucionalValido } from "@/lib/perfis";
import { IconeVinculo } from "@/components/ui/Icones";
import { CODIGO_CONDUTA, CODIGO_CONDUTA_INTRODUCAO, CODIGO_CONDUTA_TITULO, DADOS_TEXTO, DADOS_TITULO } from "@/lib/codigoConduta";
import Modal from "@/components/ui/Modal";
import conta from "../login/conta.module.css";
import styles from "./registrar.module.css";

/** Marca "iD" do ORCID em traço, na cor do texto do botão. */
function IconeOrcid() {
  return (
    <svg
      width="20"
      height="20"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
    >
      <circle cx="12" cy="12" r="9" />
      <path d="M8.5 7.5v.01" />
      <path d="M8.5 10.5v5" />
      <path d="M11.5 8.5h2.5a3.5 3.5 0 0 1 0 7h-2.5z" />
    </svg>
  );
}

/**
 * Registro em blocos: acesso (e-mail institucional e senha, ou a conta
 * ORCID para quem não tem e-mail acadêmico), dados pessoais, vínculo
 * institucional (cartões de opção e os campos de cada vínculo), aceites
 * e as ações. Validações e chamadas iguais às de antes.
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
  // Resultado do reenvio na tela de confirmação, mostrado no próprio card.
  const [reenvio, setReenvio] = useState<{ tipo: "sucesso" | "erro"; texto: string } | null>(null);

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

  async function reenviarVerificacao() {
    try {
      await api.post("/api/auth/reenviar-verificacao", { email: emailEnviado });
      setReenvio({ tipo: "sucesso", texto: "E-mail reenviado com sucesso!" });
    } catch {
      setReenvio({ tipo: "erro", texto: "Erro ao reenviar. Tente novamente em alguns minutos." });
    }
  }

  if (emailEnviado) {
    return (
      <div className={conta.pagina}>
        <div className={`ui-card animate-fade-in ${conta.cartao}`}>
          <div className={conta.estado}>
            <span className={`${conta.estadoIcone} ${conta.estadoNeutro}`}>
              <svg
                width="24"
                height="24"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                strokeWidth="2"
                strokeLinecap="round"
                strokeLinejoin="round"
                aria-hidden="true"
              >
                <rect x="2" y="4" width="20" height="16" rx="2" />
                <path d="m22 7-8.97 5.7a1.94 1.94 0 0 1-2.06 0L2 7" />
              </svg>
            </span>
            <h1 className={conta.titulo}>Verifique seu e-mail</h1>
            <p className={conta.estadoTexto}>
              Enviamos um link de confirmação para <strong>{emailEnviado}</strong>.
            </p>
            <p className={conta.estadoTexto}>
              Clique no link recebido para ativar sua conta. O link é válido por 24 horas.
            </p>
            {reenvio && (
              <div
                className={`${conta.aviso} ${reenvio.tipo === "sucesso" ? conta.avisoSucesso : conta.avisoErro}`}
                role="status"
              >
                <p>{reenvio.texto}</p>
              </div>
            )}
            <p className={conta.estadoTexto}>Não recebeu? Verifique a pasta de spam ou peça um novo e-mail.</p>
            <div className={conta.estadoAcoes}>
              <button type="button" className="ui-btn ui-btn-secondary" onClick={reenviarVerificacao}>
                Reenviar e-mail
              </button>
              <Link href="/login" className="ui-btn ui-btn-primary">
                Ir para o login
              </Link>
            </div>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className={conta.pagina}>
      <div className={`ui-card animate-fade-in ${conta.cartao} ${conta.cartaoLargo}`}>
        <header className={styles.topo}>
          <div>
            <h1 className={conta.titulo}>Criar conta</h1>
            <p className={conta.subtitulo}>Com o e-mail institucional ou com a sua conta ORCID.</p>
          </div>
          <Link href="/login" className="ui-btn ui-btn-ghost">
            Entrar
          </Link>
        </header>

        <form onSubmit={handleSubmit} className={conta.formulario} noValidate>
          {error && (
            <div className={`${conta.aviso} ${conta.avisoErro}`} role="alert">
              <p>{error}</p>
            </div>
          )}

          {/* ── Acesso ── */}
          <section className={styles.bloco} aria-labelledby="bloco-acesso">
            <div className={styles.blocoCabecalho}>
              <h2 id="bloco-acesso" className={styles.blocoTitulo}>Acesso</h2>
              <p className={styles.blocoTexto}>O e-mail institucional comprova o seu vínculo com a instituição.</p>
            </div>

            {!semEmailAcademico && (
              <div className={conta.campo}>
                <label htmlFor="reg-email" className="ui-label">E-mail institucional</label>
                <input
                  id="reg-email"
                  type="email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  placeholder="voce@universidade.edu.br"
                  required
                  className="ui-field"
                  autoComplete="email"
                />
                <p className="ui-hint">Domínios acadêmicos, como .edu.br, ou os das instituições cadastradas.</p>
              </div>
            )}

            <label className={styles.marcar}>
              <input
                type="checkbox"
                checked={semEmailAcademico}
                onChange={(e) => setSemEmailAcademico(e.target.checked)}
              />
              <span>Não tenho e-mail acadêmico</span>
            </label>

            {semEmailAcademico && (
              <div className={`${conta.aviso} ${conta.avisoInfo}`} role="status">
                <p>
                  Sem um e-mail acadêmico, o registro é feito com a sua conta ORCID, que comprova o vínculo com a
                  instituição. Use o botão &ldquo;Registrar com ORCID&rdquo; no fim da página; depois você escolhe o
                  vínculo e completa o perfil.
                </p>
              </div>
            )}

            {!semEmailAcademico && (
              <div className={styles.grade2}>
                <div className={conta.campo}>
                  <label htmlFor="reg-senha" className="ui-label">Senha</label>
                  <input
                    id="reg-senha"
                    type="password"
                    value={senha}
                    onChange={(e) => setSenha(e.target.value)}
                    placeholder="Mínimo de 6 caracteres"
                    required
                    minLength={6}
                    className="ui-field"
                    autoComplete="new-password"
                  />
                </div>
                <div className={conta.campo}>
                  <label htmlFor="reg-senha-confirmar" className="ui-label">Confirmar senha</label>
                  <input
                    id="reg-senha-confirmar"
                    type="password"
                    value={senhaConfirm}
                    onChange={(e) => setSenhaConfirm(e.target.value)}
                    placeholder="Repita a senha"
                    required
                    className="ui-field"
                    autoComplete="new-password"
                  />
                </div>
              </div>
            )}
          </section>

          {/* ── Sobre você ── */}
          <section className={styles.bloco} aria-labelledby="bloco-dados">
            <div className={styles.blocoCabecalho}>
              <h2 id="bloco-dados" className={styles.blocoTitulo}>Sobre você</h2>
            </div>
            <div className={styles.grade2}>
              <div className={conta.campo}>
                <label htmlFor="reg-nome" className="ui-label">Nome completo</label>
                <input
                  id="reg-nome"
                  type="text"
                  value={nome}
                  onChange={(e) => setNome(e.target.value)}
                  placeholder="Como aparece nos documentos"
                  required
                  minLength={2}
                  className="ui-field"
                  autoComplete="name"
                />
              </div>
              <div className={conta.campo}>
                <label htmlFor="reg-inst" className="ui-label">Instituição</label>
                <input
                  id="reg-inst"
                  type="text"
                  value={instituicao}
                  onChange={(e) => setInstituicao(e.target.value)}
                  placeholder="Ex.: UNIR, UNIRIO, UFMG"
                  className="ui-field"
                  autoComplete="organization"
                />
              </div>
            </div>
          </section>

          {/* ── Vínculo institucional ── */}
          <section className={styles.bloco} aria-labelledby="bloco-vinculo">
            <div className={styles.blocoCabecalho}>
              <h2 id="bloco-vinculo" className={styles.blocoTitulo}>Vínculo institucional</h2>
              <p className={styles.blocoTexto}>Escolha o perfil que descreve a sua relação com a instituição.</p>
            </div>

            <div className={styles.perfis} role="radiogroup" aria-labelledby="bloco-vinculo">
              {PERFIS.map((p) => {
                const ativo = papel === p.value;
                return (
                  <label key={p.value} className={`${styles.perfil} ${ativo ? styles.perfilAtivo : ""}`}>
                    <input
                      type="radio"
                      name="papel"
                      value={p.value}
                      checked={ativo}
                      onChange={() => setPapel(p.value)}
                      className="sr-only"
                    />
                    <span className={styles.marcador} aria-hidden="true" />
                    <span className={styles.perfilIcone} aria-hidden="true">
                      <IconeVinculo papel={p.value} tamanho={18} />
                    </span>
                    <span className={styles.perfilTexto}>
                      <span className={styles.perfilNome}>{p.label}</span>
                      <span className={styles.perfilDesc}>{p.descricao}</span>
                    </span>
                  </label>
                );
              })}
            </div>

            {/* Campos específicos do vínculo: a pessoa só vê o que faz sentido para ela */}
            {papel === "aluno" && (
              <>
                <div className={conta.campo}>
                  <label htmlFor="reg-curso" className="ui-label">Curso</label>
                  <input id="reg-curso" type="text" value={curso} onChange={(e) => setCurso(e.target.value)}
                    placeholder="Ex.: Medicina" className="ui-field" />
                </div>
                <div className={styles.grade2}>
                  <div className={conta.campo}>
                    <label htmlFor="reg-nivel" className="ui-label">Grau de instrução</label>
                    <select id="reg-nivel" value={nivel} onChange={(e) => setNivel(e.target.value)} className="ui-field">
                      {NIVEIS.map((n) => <option key={n.value} value={n.value}>{n.label}</option>)}
                    </select>
                  </div>
                  {periodo && (
                    <div className={conta.campo}>
                      <label htmlFor="reg-semestre" className="ui-label">{periodo.rotulo}</label>
                      <input
                        id="reg-semestre"
                        type="number"
                        value={semestre}
                        onChange={(e) => setSemestre(e.target.value)}
                        min={1}
                        max={periodo.max}
                        className="ui-field"
                        placeholder={`1 a ${periodo.max}`}
                      />
                      <p className="ui-hint">De 1 a {periodo.max}.</p>
                    </div>
                  )}
                </div>
              </>
            )}

            {papel === "professor" && (
              <>
                <div className={conta.campo}>
                  <label htmlFor="reg-dep" className="ui-label">Departamento</label>
                  <input id="reg-dep" type="text" value={departamento} onChange={(e) => setDepartamento(e.target.value)}
                    placeholder="Ex.: Departamento de Medicina" className="ui-field" />
                </div>
                <div className={styles.grade2}>
                  <div className={conta.campo}>
                    <label htmlFor="reg-titulo" className="ui-label">Titulação</label>
                    <input id="reg-titulo" type="text" value={titulo} onChange={(e) => setTitulo(e.target.value)}
                      placeholder="Dr., Me., PhD" className="ui-field" />
                  </div>
                  <div className={conta.campo}>
                    <label htmlFor="reg-cargo" className="ui-label">Cargo</label>
                    <input id="reg-cargo" type="text" value={cargo} onChange={(e) => setCargo(e.target.value)}
                      placeholder="Ex.: Professor Adjunto" className="ui-field" />
                  </div>
                </div>
              </>
            )}

            {papel === "pesquisador" && (
              <>
                <div className={conta.campo}>
                  <label htmlFor="reg-dep-p" className="ui-label">Departamento ou grupo</label>
                  <input id="reg-dep-p" type="text" value={departamento} onChange={(e) => setDepartamento(e.target.value)}
                    placeholder="Ex.: Laboratório de Bioinformática" className="ui-field" />
                </div>
                <div className={styles.grade2}>
                  <div className={conta.campo}>
                    <label htmlFor="reg-titulo-p" className="ui-label">Titulação</label>
                    <input id="reg-titulo-p" type="text" value={titulo} onChange={(e) => setTitulo(e.target.value)}
                      placeholder="Dr., PhD" className="ui-field" />
                  </div>
                  <div className={conta.campo}>
                    <label htmlFor="reg-vinculo-p" className="ui-label">Vínculo</label>
                    <input id="reg-vinculo-p" type="text" value={vinculoPesq} onChange={(e) => setVinculoPesq(e.target.value)}
                      placeholder="Pós-doc, colaborador(a), visitante" className="ui-field" />
                  </div>
                </div>
              </>
            )}

            {papel === "tecnico" && (
              <div className={styles.grade2}>
                <div className={conta.campo}>
                  <label htmlFor="reg-setor" className="ui-label">Setor</label>
                  <input id="reg-setor" type="text" value={setor} onChange={(e) => setSetor(e.target.value)}
                    placeholder="Ex.: Pró-Reitoria de Pesquisa" className="ui-field" />
                </div>
                <div className={conta.campo}>
                  <label htmlFor="reg-cargo-t" className="ui-label">Cargo</label>
                  <input id="reg-cargo-t" type="text" value={cargo} onChange={(e) => setCargo(e.target.value)}
                    placeholder="Ex.: Técnico(a) de laboratório" className="ui-field" />
                </div>
              </div>
            )}

            {papel === "egresso" && (
              <>
                <div className={styles.grade2}>
                  <div className={conta.campo}>
                    <label htmlFor="reg-curso-e" className="ui-label">Curso concluído</label>
                    <input id="reg-curso-e" type="text" value={curso} onChange={(e) => setCurso(e.target.value)}
                      placeholder="Ex.: Enfermagem" className="ui-field" />
                  </div>
                  <div className={conta.campo}>
                    <label htmlFor="reg-ano" className="ui-label">Ano de conclusão</label>
                    <input id="reg-ano" type="number" value={anoConclusao} onChange={(e) => setAnoConclusao(e.target.value)}
                      min={1950} max={2100} placeholder="Ex.: 2022" className="ui-field" />
                  </div>
                </div>
                <div className={conta.campo}>
                  <label htmlFor="reg-atuacao" className="ui-label">Atuação atual</label>
                  <input id="reg-atuacao" type="text" value={atuacao} onChange={(e) => setAtuacao(e.target.value)}
                    placeholder="Ex.: Residência em Clínica Médica" className="ui-field" />
                </div>
              </>
            )}
          </section>

          {/* ── Aceites ── */}
          <section className={styles.bloco} aria-labelledby="bloco-aceites">
            <div className={styles.blocoCabecalho}>
              <h2 id="bloco-aceites" className={styles.blocoTitulo}>Aceites</h2>
            </div>
            <div className={styles.listaMarcar}>
              <label className={styles.marcar}>
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
              <label className={styles.marcar}>
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
          </section>

          {/* ── Ações ── */}
          <div className={styles.acoes}>
            {!semEmailAcademico && (
              <>
                <button type="submit" disabled={isSubmitting} className={`ui-btn ui-btn-primary ${conta.botaoLargo}`}>
                  {isSubmitting ? "Criando conta..." : "Criar conta"}
                </button>

                <div className={conta.separador}><span>ou</span></div>
              </>
            )}

            {/* No verde da marca ORCID, com ou sem e-mail acadêmico. */}
            <button
              onClick={() => loginWithOrcid()}
              className={`ui-btn ui-btn-orcid ${conta.botaoLargo}`}
              type="button"
            >
              <IconeOrcid />
              Registrar com ORCID
            </button>
            <p className={styles.ajuda}>
              Com o ORCID você entra sem senha e importa publicações e formação. Depois, escolhe o seu vínculo e
              informa o e-mail institucional.
            </p>

            <p className={styles.ajuda}>
              Problemas com o e-mail institucional?{" "}
              <a
                href="https://docs.google.com/forms/d/e/1FAIpQLSeW8URrJsHN4S-d7k-bOvmibn99fMgMLpB-ynxs9QKKCSvkug/viewform?usp=header"
                target="_blank"
                rel="noopener noreferrer"
              >
                Solicite acesso manual enviando o seu comprovante de vínculo.
              </a>
            </p>
          </div>
        </form>

        <p className={conta.rodape}>
          Já tem uma conta?{" "}
          <Link href="/login" className={conta.link}>
            Entrar
          </Link>
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
