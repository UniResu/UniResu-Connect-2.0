"use client";

import { useEffect, useState, Suspense } from "react";
import { useSearchParams, useRouter } from "next/navigation";
import Link from "next/link";
import { api } from "@/lib/api";
import styles from "./verificar-email.module.css";

function VerificarEmailContent() {
  const searchParams = useSearchParams();
  const router = useRouter();
  const token = searchParams.get("token");

  const [status, setStatus] = useState<"loading" | "success" | "error">("loading");
  const [message, setMessage] = useState("");

  useEffect(() => {
    if (!token) {
      setStatus("error");
      setMessage("Link de verificação inválido ou ausente.");
      return;
    }

    async function verificar() {
      try {
        const res = await api.get<{ message: string }>(
          `/api/auth/verificar-email?token=${encodeURIComponent(token!)}`
        );
        setStatus("success");
        setMessage(res.message);
        // Redirecionar para login após 3 segundos
        setTimeout(() => router.push("/login"), 3000);
      } catch (err: unknown) {
        setStatus("error");
        const apiErr = err as { detail?: string };
        setMessage(
          apiErr.detail || "O link de confirmação é inválido ou expirou."
        );
      }
    }

    verificar();
  }, [token, router]);

  return (
    <div className={styles.page}>
      <div className={styles.card}>
        {status === "loading" && (
          <div className={styles.content}>
            <div className={styles.spinner} />
            <h1 className={styles.title}>Verificando seu e-mail...</h1>
            <p className={styles.text}>Aguarde um momento.</p>
          </div>
        )}

        {status === "success" && (
          <div className={styles.content}>
            <div className={styles.iconSuccess}>&#10003;</div>
            <h1 className={styles.title}>E-mail verificado!</h1>
            <p className={styles.text}>{message}</p>
            <p className={styles.text}>
              Redirecionando para o login em instantes...
            </p>
            <Link href="/login" className={styles.button}>
              Ir para o Login
            </Link>
          </div>
        )}

        {status === "error" && (
          <div className={styles.content}>
            <div className={styles.iconError}>&#10007;</div>
            <h1 className={styles.title}>Falha na verificação</h1>
            <p className={styles.textError}>{message}</p>
            <p className={styles.text}>
              O link pode ter expirado. Solicite um novo e-mail de verificação
              na página de login.
            </p>
            <Link href="/login" className={styles.button}>
              Ir para o Login
            </Link>
          </div>
        )}
      </div>
    </div>
  );
}

export default function VerificarEmailPage() {
  return (
    <Suspense
      fallback={
        <div className={styles.page}>
          <div className={styles.card}>
            <div className={styles.content}>
              <div className={styles.spinner} />
              <p className={styles.text}>Carregando...</p>
            </div>
          </div>
        </div>
      }
    >
      <VerificarEmailContent />
    </Suspense>
  );
}
