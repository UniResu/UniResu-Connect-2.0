"use client";

import { useState, FormEvent } from "react";
import Link from "next/link";
import { api } from "@/lib/api";
import type { PapelUsuario } from "@/types/user";
import { useAuth } from "@/contexts/AuthContext";
import styles from "./registrar.module.css";

export default function RegistrarPage() {
  const { loginWithOrcid } = useAuth();

  const [nome, setNome] = useState("");
  const [email, setEmail] = useState("");
  const [senha, setSenha] = useState("");
  const [senhaConfirm, setSenhaConfirm] = useState("");
  const [papel, setPapel] = useState<PapelUsuario>("aluno");
  const [instituicao, setInstituicao] = useState("");
  const [curso, setCurso] = useState("");
  const [error, setError] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [step, setStep] = useState(1); // 1 = role, 2 = form, 3 = email enviado
  const [emailEnviado, setEmailEnviado] = useState("");

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setError("");

    // Validação por whitelist de domínios acadêmicos (aceita subdomínios).
    // Regra:
    //  - Aceita qualquer domínio terminado em .edu.br ou .edu.
    //  - Aceita qualquer subdomínio das instituições listadas
    //    (ex.: sga.pucminas.br, diretoria.uerj.br, aluno.unb.br).
    const dominio = email.split("@")[1]?.toLowerCase().trim();
    if (!dominio) {
      setError("Por favor, informe um e-mail válido.");
      return;
    }

    const dominiosPermitidos = [
      // Federais
      "ufrj.br", "ufmg.br", "unb.br", "ufrgs.br", "ufsc.br",
      "ufpr.br", "ufpe.br", "ufba.br", "ufg.br", "ufrn.br",
      "ufv.br", "ufscar.br", "unifesp.br", "ufc.br", "ufu.br",
      // Estaduais
      "usp.br", "unicamp.br", "unesp.br", "uerj.br", "udesc.br",
      "uems.br", "unemat.br", "uenp.br",
      // PUCs
      "pucminas.br", "puc-rio.br", "pucsp.br", "pucpr.br",
      "pucrs.br", "puccampinas.edu.br",
      // Privadas e institutos
      "fgv.br", "insper.edu.br", "mackenzie.br", "einstein.br",
      "fia.com.br", "senai.br", "itajuba.edu.br", "ita.br",
      "ime.eb.mil.br",
    ];

    const ehEduGenerico =
      dominio.endsWith(".edu.br") || dominio === "edu.br" ||
      dominio.endsWith(".edu") || dominio === "edu";
    const ehDominioPermitido = dominiosPermitidos.some(
      (alvo) => dominio === alvo || dominio.endsWith("." + alvo)
    );

    if (!ehEduGenerico && !ehDominioPermitido) {
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

    setIsSubmitting(true);
    try {
      // Registrar (conta criada como pendente — e-mail de verificação enviado)
      await api.post("/api/usuarios/registrar", {
        nome,
        email,
        senha,
        papel,
        instituicao: instituicao || null,
        curso: curso || null,
      });

      // Mostrar tela de confirmação (não faz login automático)
      setEmailEnviado(email);
      setStep(3);
    } catch (err: unknown) {
      const apiErr = err as { detail?: string };
      setError(apiErr.detail || "Erro ao criar conta. Tente novamente.");
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <div className={styles.page}>
      <div className={styles.card}>
        <div className={styles.header}>
          <h1 className={styles.title}>Criar Conta</h1>
          <p className={styles.subtitle}>
            Junte-se à comunidade UniResu Connect
          </p>
        </div>

        {/* Step 1: escolha de papel */}
        {step === 1 && (
          <div className={styles.roleSelection}>
            <p className={styles.roleLabel}>Eu sou:</p>
            <div className={styles.roleGrid}>
              <button
                className={`${styles.roleCard} ${papel === "aluno" ? styles.roleActive : ""}`}
                onClick={() => setPapel("aluno")}
                type="button"
              >
                <span className={styles.roleIcon}>🎓</span>
                <span className={styles.roleName}>Aluno</span>
                <span className={styles.roleDesc}>Graduação ou Pós-Graduação</span>
              </button>
              <button
                className={`${styles.roleCard} ${papel === "professor" ? styles.roleActive : ""}`}
                onClick={() => setPapel("professor")}
                type="button"
              >
                <span className={styles.roleIcon}>👨‍🏫</span>
                <span className={styles.roleName}>Professor</span>
                <span className={styles.roleDesc}>Docente e orientador</span>
              </button>
              <button
                className={`${styles.roleCard} ${papel === "pesquisador" ? styles.roleActive : ""}`}
                onClick={() => setPapel("pesquisador")}
                type="button"
              >
                <span className={styles.roleIcon}>🔬</span>
                <span className={styles.roleName}>Pesquisador</span>
                <span className={styles.roleDesc}>Pós-Doc ou colaborador</span>
              </button>
            </div>

            {(papel === "professor" || papel === "pesquisador") && (
              <button
                onClick={() => loginWithOrcid()}
                className={styles.orcidButton}
                type="button"
              >
                <img
                  src="https://info.orcid.org/wp-content/uploads/2019/11/orcid_16x16.png"
                  alt="ORCID"
                  width={20}
                  height={20}
                />
                Registrar com ORCID (recomendado)
              </button>
            )}

            <div className={styles.divider}>
              <span>ou preencha manualmente</span>
            </div>

            <button
              onClick={() => setStep(2)}
              className={styles.continueButton}
              type="button"
            >
              Continuar com email
            </button>
          </div>
        )}

        {/* Step 2: formulário */}
        {step === 2 && (
          <>
            <button
              onClick={() => setStep(1)}
              className={styles.backButton}
              type="button"
            >
              ← Voltar
            </button>

            <div className={styles.roleBadge}>
              {papel === "aluno" ? "🎓" : papel === "professor" ? "👨‍🏫" : "🔬"}{" "}
              {papel.charAt(0).toUpperCase() + papel.slice(1)}
            </div>

            <form onSubmit={handleSubmit} className={styles.form}>
              {error && <div className={styles.errorMessage}>{error}</div>}

              <div className={styles.fieldGroup}>
                <label htmlFor="nome" className={styles.label}>Nome completo</label>
                <input
                  id="nome"
                  type="text"
                  value={nome}
                  onChange={(e) => setNome(e.target.value)}
                  placeholder="Seu nome completo"
                  required
                  className={styles.input}
                />
              </div>

              <div className={styles.fieldGroup}>
                <label htmlFor="reg-email" className={styles.label}>E-mail institucional</label>
                <input
                  id="reg-email"
                  type="email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  placeholder="seu@universidade.edu.br"
                  required
                  className={styles.input}
                />
              </div>

              <div className={styles.fieldRow}>
                <div className={styles.fieldGroup}>
                  <label htmlFor="instituicao" className={styles.label}>Instituição</label>
                  <input
                    id="instituicao"
                    type="text"
                    value={instituicao}
                    onChange={(e) => setInstituicao(e.target.value)}
                    placeholder="Ex: UERJ, USP, UFMG"
                    className={styles.input}
                  />
                </div>
                <div className={styles.fieldGroup}>
                  <label htmlFor="curso" className={styles.label}>Curso / Departamento</label>
                  <input
                    id="curso"
                    type="text"
                    value={curso}
                    onChange={(e) => setCurso(e.target.value)}
                    placeholder="Ex: Bioinformática"
                    className={styles.input}
                  />
                </div>
              </div>

              <div className={styles.fieldGroup}>
                <label htmlFor="reg-senha" className={styles.label}>Senha</label>
                <input
                  id="reg-senha"
                  type="password"
                  value={senha}
                  onChange={(e) => setSenha(e.target.value)}
                  placeholder="Mínimo 6 caracteres"
                  required
                  minLength={6}
                  className={styles.input}
                />
              </div>

              <div className={styles.fieldGroup}>
                <label htmlFor="reg-senha-confirm" className={styles.label}>Confirmar senha</label>
                <input
                  id="reg-senha-confirm"
                  type="password"
                  value={senhaConfirm}
                  onChange={(e) => setSenhaConfirm(e.target.value)}
                  placeholder="Repita a senha"
                  required
                  className={styles.input}
                />
              </div>

              <button
                type="submit"
                disabled={isSubmitting}
                className={styles.submitButton}
              >
                {isSubmitting ? "Criando conta..." : "Criar conta"}
              </button>

              <p className="text-sm text-gray-500 mt-4">Problemas com o e-mail institucional? <a href="https://docs.google.com/forms/d/e/1FAIpQLSeW8URrJsHN4S-d7k-bOvmibn99fMgMLpB-ynxs9QKKCSvkug/viewform?usp=header" target="_blank" rel="noopener noreferrer" className="text-purple-600 hover:underline">Solicite acesso manual enviando o seu comprovante de vínculo.</a></p>
            </form>
          </>
        )}

        {/* Step 3: confirmação de e-mail enviado */}
        {step === 3 && (
          <div className={styles.emailConfirmation}>
            <div className={styles.emailIcon}>✉️</div>
            <h2 className={styles.emailTitle}>Verifique seu e-mail</h2>
            <p className={styles.emailText}>
              Enviamos um link de confirmação para{" "}
              <strong>{emailEnviado}</strong>.
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
                    await api.post("/api/auth/reenviar-verificacao", {
                      email: emailEnviado,
                    });
                    setError("");
                    alert("E-mail reenviado com sucesso!");
                  } catch {
                    alert("Erro ao reenviar. Tente novamente em alguns minutos.");
                  }
                }}
              >
                reenvie o e-mail
              </button>.
            </p>
            <Link href="/login" className={styles.loginButton}>
              Ir para o Login
            </Link>
          </div>
        )}

        <p className={styles.footer}>
          Já tem uma conta?{" "}
          <Link href="/login" className={styles.link}>Entrar</Link>
        </p>
      </div>
    </div>
  );
}
