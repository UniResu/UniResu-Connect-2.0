"use client";

import { useState, FormEvent } from "react";
import { api } from "@/lib/api";
import Link from "next/link";
import styles from "./recuperar.module.css";

export default function RecuperarSenhaPage() {
  const [email, setEmail] = useState("");
  const [status, setStatus] = useState<"idle" | "loading" | "success" | "error">("idle");
  const [message, setMessage] = useState("");

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setStatus("loading");
    setMessage("");

    try {
      await api.post("/api/auth/recuperar-senha", { email });
      setStatus("success");
      setMessage("Se este e-mail estiver cadastrado, você receberá um link de redefinição na sua caixa de entrada em instantes.");
    } catch (err: unknown) {
      setStatus("error");
      const error = err as { detail?: string };
      setMessage(error.detail || "Ocorreu um erro ao tentar enviar o e-mail.");
    }
  }

  return (
    <div className={styles.page}>
      <div className={styles.card}>
        <div className={styles.header}>
          <h1 className={styles.title}>Recuperar Senha</h1>
          <p className={styles.subtitle}>
            Informe o e-mail da sua conta para receber as instruções de recuperação.
          </p>
        </div>

        {status === "success" ? (
          <div className={styles.successMessage}>
            <p>{message}</p>
          </div>
        ) : (
          <form onSubmit={handleSubmit} className={styles.form}>
            {status === "error" && <div className={styles.errorMessage}>{message}</div>}

            <div className={styles.fieldGroup}>
              <label htmlFor="email" className={styles.label}>
                E-mail
              </label>
              <input
                id="email"
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="seu.email@instituicao.br"
                required
                className={styles.input}
              />
            </div>

            <button
              type="submit"
              disabled={status === "loading"}
              className={styles.submitButton}
            >
              {status === "loading" ? "Enviando solicitacão..." : "Enviar link de recuperação"}
            </button>
          </form>
        )}

        <div className={styles.footer}>
          Lembrou sua senha?{" "}
          <Link href="/login" className={styles.link}>
            Fazer login
          </Link>
        </div>
      </div>
    </div>
  );
}
