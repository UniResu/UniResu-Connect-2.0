"use client";

import { useState, FormEvent } from "react";
import { api } from "@/lib/api";
import Link from "next/link";
import styles from "../login/conta.module.css";

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
    <div className={styles.pagina}>
      <div className={`ui-card animate-fade-in ${styles.cartao}`}>
        <header className={styles.topo}>
          <h1 className={styles.titulo}>Recuperar senha</h1>
          <p className={styles.subtitulo}>
            Informe o e-mail da sua conta para receber as instruções de recuperação.
          </p>
        </header>

        {status === "success" ? (
          <div className={`${styles.aviso} ${styles.avisoSucesso}`} role="status">
            <p>{message}</p>
          </div>
        ) : (
          <form onSubmit={handleSubmit} className={styles.formulario}>
            {status === "error" && (
              <div className={`${styles.aviso} ${styles.avisoErro}`} role="alert">
                <p>{message}</p>
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

            <button
              type="submit"
              disabled={status === "loading"}
              className={`ui-btn ui-btn-primary ${styles.botaoLargo}`}
            >
              {status === "loading" ? "Enviando solicitação..." : "Enviar link de recuperação"}
            </button>
          </form>
        )}

        <p className={styles.rodape}>
          Lembrou sua senha?{" "}
          <Link href="/login" className={styles.link}>
            Entrar
          </Link>
        </p>
      </div>
    </div>
  );
}
