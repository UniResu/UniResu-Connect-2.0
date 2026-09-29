"use client";

import { Suspense, useEffect, useState, useRef } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { api } from "@/lib/api";
import { TOKEN_KEY } from "@/lib/constants";
import type { LoginResponse } from "@/types/user";
import styles from "./callback.module.css";

function OrcidCallbackContent() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const [status, setStatus] = useState<"loading" | "error">("loading");
  const [errorMsg, setErrorMsg] = useState("");

  const hasProcessed = useRef(false);

  const code = searchParams.get("code");
  const state = searchParams.get("state");
  const error = searchParams.get("error");

  // Erros de parâmetro são derivados direto da URL (sem setState no effect).
  const erroParametros = error
    ? "Autorização negada pelo ORCID."
    : !code || !state
      ? "Parâmetros inválidos no callback."
      : "";

  useEffect(() => {
    if (erroParametros || !code || !state || hasProcessed.current) return;
    hasProcessed.current = true;

    async function processarCallback(code: string, state: string) {
      try {
        const response = await api.post<LoginResponse>(
          "/api/auth/orcid/callback",
          { code, state }
        );

        localStorage.setItem(TOKEN_KEY, response.access_token);
        window.location.href = "/perfil";
      } catch (err: unknown) {
        const apiErr = err as { detail?: string };
        setStatus("error");
        setErrorMsg(apiErr.detail || "Erro ao autenticar com ORCID.");
      }
    }

    processarCallback(code, state);
  }, [code, state, erroParametros]);

  if (erroParametros || status === "error") {
    return (
      <div className={styles.page}>
        <div className={styles.card}>
          <span className={styles.icon}>❌</span>
          <h2 className={styles.title}>Erro na Autenticação</h2>
          <p className={styles.message}>{erroParametros || errorMsg}</p>
          <button
            onClick={() => router.push("/login")}
            className={styles.button}
          >
            Voltar ao Login
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className={styles.page}>
      <div className={styles.card}>
        <div className={styles.spinner} />
        <h2 className={styles.title}>Autenticando com ORCID...</h2>
        <p className={styles.message}>
          Estamos processando sua autenticação. Aguarde um momento.
        </p>
      </div>
    </div>
  );
}

export default function OrcidCallbackPage() {
  return (
    <Suspense
      fallback={
        <div className={styles.page}>
          <div className={styles.card}>
            <div className={styles.spinner} />
            <h2 className={styles.title}>Carregando...</h2>
          </div>
        </div>
      }
    >
      <OrcidCallbackContent />
    </Suspense>
  );
}
