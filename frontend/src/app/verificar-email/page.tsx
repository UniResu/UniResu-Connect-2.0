"use client";

import { useEffect, useState, Suspense } from "react";
import { useSearchParams, useRouter } from "next/navigation";
import Link from "next/link";
import { api } from "@/lib/api";
import styles from "../login/conta.module.css";

const svgProps = {
  width: 24,
  height: 24,
  viewBox: "0 0 24 24",
  fill: "none",
  stroke: "currentColor",
  strokeWidth: 2,
  strokeLinecap: "round" as const,
  strokeLinejoin: "round" as const,
  "aria-hidden": true,
};

function VerificarEmailContent() {
  const searchParams = useSearchParams();
  const router = useRouter();
  const token = searchParams.get("token");

  const [status, setStatus] = useState<"loading" | "success" | "error">("loading");
  const [message, setMessage] = useState("");

  useEffect(() => {
    if (!token) return;

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

  // Sem token não há o que verificar: o erro é derivado direto da URL.
  const statusExibido = token ? status : "error";
  const mensagemExibida = token ? message : "Link de verificação inválido ou ausente.";

  return (
    <div className={styles.pagina}>
      <div className={`ui-card animate-fade-in ${styles.cartao}`}>
        {statusExibido === "loading" && (
          <div className={styles.estado} aria-busy="true">
            <div className={styles.spinner} aria-hidden="true" />
            <h1 className={styles.titulo}>Verificando seu e-mail...</h1>
            <p className={styles.estadoTexto}>Aguarde um momento.</p>
          </div>
        )}

        {statusExibido === "success" && (
          <div className={styles.estado} role="status">
            <span className={`${styles.estadoIcone} ${styles.estadoSucesso}`}>
              <svg {...svgProps}>
                <path d="M20 6 9 17l-5-5" />
              </svg>
            </span>
            <h1 className={styles.titulo}>E-mail verificado</h1>
            <p className={styles.estadoTexto}>{mensagemExibida}</p>
            <p className={styles.estadoTexto}>Redirecionando para o login em instantes...</p>
            <div className={styles.estadoAcoes}>
              <Link href="/login" className="ui-btn ui-btn-primary">
                Ir para o login
              </Link>
            </div>
          </div>
        )}

        {statusExibido === "error" && (
          <div className={styles.estado} role="alert">
            <span className={`${styles.estadoIcone} ${styles.estadoErro}`}>
              <svg {...svgProps}>
                <path d="M18 6 6 18" />
                <path d="m6 6 12 12" />
              </svg>
            </span>
            <h1 className={styles.titulo}>Falha na verificação</h1>
            <div className={`${styles.aviso} ${styles.avisoErro}`}>
              <p>{mensagemExibida}</p>
            </div>
            <p className={styles.estadoTexto}>
              O link pode ter expirado. Solicite um novo e-mail de verificação
              na página de login.
            </p>
            <div className={styles.estadoAcoes}>
              <Link href="/login" className="ui-btn ui-btn-primary">
                Ir para o login
              </Link>
            </div>
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
        <div className={styles.pagina}>
          <div className={`ui-card ${styles.cartao}`}>
            <div className={styles.estado}>
              <div className={styles.spinner} aria-hidden="true" />
              <p className={styles.estadoTexto}>Carregando...</p>
            </div>
          </div>
        </div>
      }
    >
      <VerificarEmailContent />
    </Suspense>
  );
}
