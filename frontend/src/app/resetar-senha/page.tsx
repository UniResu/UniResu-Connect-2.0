"use client";

import { useState, FormEvent, Suspense } from "react";
import { api } from "@/lib/api";
import { useRouter, useSearchParams } from "next/navigation";
import Link from "next/link";
import styles from "../recuperar-senha/recuperar.module.css";

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
      <div className={styles.card}>
        <div className={styles.header}>
          <h1 className={styles.title}>Token Inválido</h1>
        </div>
        <div className={styles.errorMessage} style={{ margin: "2rem 0" }}>
          Link de recuperação ausente ou formato inválido.
        </div>
        <div className={styles.footer}>
          <Link href="/recuperar-senha" className={styles.link}>
            Solicitar um novo link
          </Link>
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
    <div className={styles.card}>
      <div className={styles.header}>
        <h1 className={styles.title}>Redefinir Senha</h1>
        <p className={styles.subtitle}>
          Crie uma nova senha segura para sua conta.
        </p>
      </div>

      {status === "success" ? (
        <div className={styles.successMessage}>
          <p>{message}</p>
          <p style={{ marginTop: "0.5rem", fontSize: "0.8rem", opacity: 0.8 }}>
            Redirecionando para o login...
          </p>
        </div>
      ) : (
        <form onSubmit={handleSubmit} className={styles.form}>
          {status === "error" && <div className={styles.errorMessage}>{message}</div>}

          <div className={styles.fieldGroup}>
            <label htmlFor="senha" className={styles.label}>
              Nova Senha
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

          <div className={styles.fieldGroup}>
            <label htmlFor="confirmarSenha" className={styles.label}>
              Confirmar Nova Senha
            </label>
            <input
              id="confirmarSenha"
              type="password"
              value={confirmarSenha}
              onChange={(e) => setConfirmarSenha(e.target.value)}
              placeholder="••••••••"
              required
              className={styles.input}
            />
          </div>

          <button
            type="submit"
            disabled={status === "loading"}
            className={styles.submitButton}
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
    <div className={styles.page}>
      <Suspense fallback={<div style={{ color: "white" }}>Carregando validador de sessão...</div>}>
        <ResetSenhaForm />
      </Suspense>
    </div>
  );
}
