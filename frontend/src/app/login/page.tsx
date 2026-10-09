"use client";

import { useState, FormEvent } from "react";
import { useAuth } from "@/contexts/AuthContext";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { api } from "@/lib/api";
import { IconeUfo } from "@/components/ui/Icones";
import styles from "./conta.module.css";

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

export default function LoginPage() {
  const { login, loginWithOrcid } = useAuth();
  const router = useRouter();

  const [email, setEmail] = useState("");
  const [senha, setSenha] = useState("");
  const [error, setError] = useState("");
  // O aviso usa a cor de sucesso só depois de reenviar a verificação.
  const [avisoSucesso, setAvisoSucesso] = useState(false);
  const [emailNaoVerificado, setEmailNaoVerificado] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setError("");
    setAvisoSucesso(false);
    setIsSubmitting(true);

    try {
      setEmailNaoVerificado(false);
      await login(email, senha);
      router.push("/perfil");
    } catch (err: unknown) {
      const apiError = err as { detail?: string; status?: number };
      if (apiError.status === 403) {
        setEmailNaoVerificado(true);
      }
      setError(apiError.detail || "Erro ao fazer login. Tente novamente.");
    } finally {
      setIsSubmitting(false);
    }
  }

  async function handleOrcidLogin() {
    try {
      await loginWithOrcid();
    } catch {
      setAvisoSucesso(false);
      setError("Erro ao conectar com ORCID. Tente novamente.");
    }
  }

  async function reenviarVerificacao() {
    try {
      await api.post("/api/auth/reenviar-verificacao", { email });
      setAvisoSucesso(true);
      setError("Novo e-mail de verificação enviado! Verifique sua caixa de entrada.");
      setEmailNaoVerificado(false);
    } catch {
      setAvisoSucesso(false);
      setError("Erro ao reenviar e-mail. Tente novamente.");
    }
  }

  return (
    <div className={styles.pagina}>
      <div className={`ui-card animate-fade-in ${styles.cartao}`}>
        <header className={styles.topo}>
          <span className={styles.marcaIcone} aria-hidden="true">
            <IconeUfo tamanho={26} />
          </span>
          <h1 className={styles.titulo}>Entrar</h1>
          <p className={styles.subtitulo}>
            Acesse sua conta do UniResu Connect com o ORCID ou com e-mail e senha.
          </p>
        </header>

        <div className={styles.pilha}>
          <button
            onClick={handleOrcidLogin}
            className={`ui-btn ui-btn-orcid ${styles.botaoLargo}`}
            type="button"
          >
            <IconeOrcid />
            Entrar com ORCID
          </button>

          <div className={styles.separador}>
            <span>ou continue com e-mail</span>
          </div>

          <form onSubmit={handleSubmit} className={styles.formulario}>
            {error && (
              <div
                className={`${styles.aviso} ${avisoSucesso ? styles.avisoSucesso : styles.avisoErro}`}
                role="alert"
              >
                <p>{error}</p>
                {emailNaoVerificado && (
                  <button type="button" className="ui-btn ui-btn-ghost" onClick={reenviarVerificacao}>
                    Reenviar e-mail de verificação
                  </button>
                )}
              </div>
            )}

            <div className={styles.campo}>
              <label htmlFor="email" className="ui-label">
                E-mail
              </label>
              <input
                id="email"
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="voce@universidade.edu.br"
                autoComplete="email"
                required
                className="ui-field"
              />
            </div>

            <div className={styles.campo}>
              <div className={styles.linhaRotulo}>
                <label htmlFor="senha" className="ui-label">
                  Senha
                </label>
                <Link href="/recuperar-senha" className={styles.linkDiscreto}>
                  Perdi minha senha
                </Link>
              </div>
              <input
                id="senha"
                type="password"
                value={senha}
                onChange={(e) => setSenha(e.target.value)}
                autoComplete="current-password"
                required
                className="ui-field"
              />
            </div>

            <button
              type="submit"
              disabled={isSubmitting}
              className={`ui-btn ui-btn-primary ${styles.botaoLargo}`}
            >
              {isSubmitting ? "Entrando..." : "Entrar"}
            </button>
          </form>
        </div>

        <p className={styles.rodape}>
          Não tem uma conta?{" "}
          <Link href="/registrar" className={styles.link}>
            Registre-se
          </Link>
        </p>
      </div>
    </div>
  );
}
