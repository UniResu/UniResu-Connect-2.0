"use client";

import { useState, FormEvent, Suspense } from "react";
import { api } from "@/lib/api";
import { useRouter, useSearchParams } from "next/navigation";
import Link from "next/link";
import styles from "../login/conta.module.css";

function ResetSenhaForm() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const token = searchParams.get("token");

  const [senha, setSenha] = useState("");
  const [confirmarSenha, setConfirmarSenha] = useState("");
  const [status, setStatus] = useState<"idle" | "loading" | "success" | "error">("idle");
  const [message, setMessage] = useState("");

  if (!token) {
    return (
      <div className={`ui-card animate-fade-in ${styles.cartao}`}>
        <div className={styles.estado}>
          <span className={`${styles.estadoIcone} ${styles.estadoErro}`}>
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
              <path d="M18 6 6 18" />
              <path d="m6 6 12 12" />
            </svg>
          </span>
          <h1 className={styles.titulo}>Link inválido</h1>
          <p className={styles.estadoTexto}>Link de recuperação ausente ou formato inválido.</p>
          <div className={styles.estadoAcoes}>
            <Link href="/recuperar-senha" className="ui-btn ui-btn-primary">
              Solicitar um novo link
            </Link>
          </div>
        </div>
      </div>
    );
  }

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();

    if (senha !== confirmarSenha) {
      setStatus("error");
      setMessage("As senhas não coincidem.");
      return;
    }

    if (senha.length < 6) {
      setStatus("error");
      setMessage("A senha deve ter pelo menos 6 caracteres.");
      return;
    }

    setStatus("loading");
    setMessage("");

    try {
      await api.post("/api/auth/resetar-senha", { token, nova_senha: senha });
      setStatus("success");
      setMessage("Sua senha foi redefinida com sucesso!");
      setTimeout(() => {
        router.push("/login");
      }, 3000);
    } catch (err: unknown) {
      setStatus("error");
      const error = err as { detail?: string };
      setMessage(error.detail || "Erro ao redefinir a senha. O link pode estar expirado.");
    }
  }

  return (
    <div className={`ui-card animate-fade-in ${styles.cartao}`}>
      <header className={styles.topo}>
        <h1 className={styles.titulo}>Redefinir senha</h1>
        <p className={styles.subtitulo}>Crie uma nova senha para a sua conta.</p>
      </header>

      {status === "success" ? (
        <div className={`${styles.aviso} ${styles.avisoSucesso}`} role="status">
          <p>{message}</p>
          <p>Redirecionando para o login...</p>
        </div>
      ) : (
        <form onSubmit={handleSubmit} className={styles.formulario}>
          {status === "error" && (
            <div className={`${styles.aviso} ${styles.avisoErro}`} role="alert">
              <p>{message}</p>
            </div>
          )}

          <div className={styles.campo}>
            <label htmlFor="senha" className="ui-label">
              Nova senha
            </label>
            <input
              id="senha"
              type="password"
              value={senha}
              onChange={(e) => setSenha(e.target.value)}
              autoComplete="new-password"
              required
              className="ui-field"
            />
            <p className="ui-hint">Mínimo de 6 caracteres.</p>
          </div>

          <div className={styles.campo}>
            <label htmlFor="confirmarSenha" className="ui-label">
              Confirmar nova senha
            </label>
            <input
              id="confirmarSenha"
              type="password"
              value={confirmarSenha}
              onChange={(e) => setConfirmarSenha(e.target.value)}
              autoComplete="new-password"
              required
              className="ui-field"
            />
          </div>

          <button
            type="submit"
            disabled={status === "loading"}
            className={`ui-btn ui-btn-primary ${styles.botaoLargo}`}
          >
            {status === "loading" ? "Salvando..." : "Salvar nova senha"}
          </button>
        </form>
      )}
    </div>
  );
}

export default function ResetarSenhaPage() {
  return (
    <div className={styles.pagina}>
      <Suspense
        fallback={
          <div className={`ui-card ${styles.cartao}`}>
            <div className={styles.estado}>
              <div className={styles.spinner} aria-hidden="true" />
              <p className={styles.estadoTexto}>Carregando...</p>
            </div>
          </div>
        }
      >
        <ResetSenhaForm />
      </Suspense>
    </div>
  );
}
