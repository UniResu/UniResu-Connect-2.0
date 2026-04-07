"use client";

import { useState, FormEvent } from "react";
import { useAuth } from "@/contexts/AuthContext";
import { useRouter } from "next/navigation";
import Link from "next/link";
import styles from "./login.module.css";

export default function LoginPage() {
  const { login, loginWithOrcid, isLoading: authLoading } = useAuth();
  const router = useRouter();

  const [email, setEmail] = useState("");
  const [senha, setSenha] = useState("");
  const [error, setError] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setError("");
    setIsSubmitting(true);

    try {
      await login(email, senha);
      router.push("/perfil");
    } catch (err: unknown) {
      const apiError = err as { detail?: string };
      setError(apiError.detail || "Erro ao fazer login. Tente novamente.");
    } finally {
      setIsSubmitting(false);
    }
  }

  async function handleOrcidLogin() {
    try {
      await loginWithOrcid();
    } catch {
      setError("Erro ao conectar com ORCID. Tente novamente.");
    }
  }

  return (
    <div className={styles.page}>
      <div className={styles.card}>
        <div className={styles.header}>
          <h1 className={styles.title}>Bem-vindo de volta</h1>
          <p className={styles.subtitle}>
            Entre na sua conta UniResu Connect
          </p>
        </div>

        {/* ORCID Login */}
        <button
          onClick={handleOrcidLogin}
          className={styles.orcidButton}
          type="button"
        >
          <img
            src="https://info.orcid.org/wp-content/uploads/2019/11/orcid_16x16.png"
            alt="ORCID"
            width={20}
            height={20}
          />
          Entrar com ORCID
        </button>

        <div className={styles.divider}>
          <span>ou continue com email</span>
        </div>

        {/* Email + Senha */}
        <form onSubmit={handleSubmit} className={styles.form}>
          {error && <div className={styles.errorMessage}>{error}</div>}

          <div className={styles.fieldGroup}>
            <label htmlFor="email" className={styles.label}>
              E-mail
            </label>
            <input
              id="email"
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="seu@email.edu.br"
              required
              className={styles.input}
            />
          </div>

          <div className={styles.fieldGroup}>
            <label htmlFor="senha" className={styles.label}>
              Senha
            </label>
            <input
              id="senha"
              type="password"
              value={senha}
              onChange={(e) => setSenha(e.target.value)}
              placeholder="••••••••"
              required
              className={styles.input}
            />
          </div>

          <button
            type="submit"
            disabled={isSubmitting}
            className={styles.submitButton}
          >
            {isSubmitting ? "Entrando..." : "Entrar"}
          </button>
        </form>

        <p className={styles.footer}>
          Não tem uma conta?{" "}
          <Link href="/registrar" className={styles.link}>
            Registre-se
          </Link>
        </p>
      </div>
    </div>
  );
}
