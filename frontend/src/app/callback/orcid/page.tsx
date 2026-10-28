"use client";

import { Suspense, useEffect, useState, useRef } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { api } from "@/lib/api";
import { TOKEN_KEY } from "@/lib/constants";
import { descartarRegistroPendente, guardarRegistroPendente, lerRegistroPendente } from "@/lib/registroOrcid";
import type { LoginResponse } from "@/types/user";
import styles from "../../login/conta.module.css";

function OrcidCallbackContent() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const [status, setStatus] = useState<"loading" | "concluindo" | "error">("loading");
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

        // Conta nova vinda de /registrar: grava o formulário preenchido antes
        // do ORCID, e a pessoa vai direto ao perfil, sem outro formulário.
        const pendente = lerRegistroPendente();
        if (response.usuario?.perfil_completo === false && pendente) {
          setStatus("concluindo");
          try {
            await api.patch(
              "/api/perfil",
              { ...pendente.dados, perfil_completo: true },
              { token: response.access_token }
            );
            descartarRegistroPendente();
            window.location.href = "/perfil";
          } catch (err: unknown) {
            // E-mail já usado em outra conta, por exemplo: /perfil/completar
            // abre com os mesmos dados e o motivo.
            const apiErr = err as { detail?: string };
            guardarRegistroPendente(pendente.dados, apiErr.detail || "Não foi possível concluir o registro.");
            window.location.href = "/perfil/completar";
          }
          return;
        }

        // Conta que já existia: um formulário guardado não se aplica a ela.
        descartarRegistroPendente();
        // Quem entrou pelo ORCID sem passar por /registrar ainda não escolheu
        // o vínculo nem informou um e-mail: segue para completar o perfil.
        const completo = response.usuario?.perfil_completo !== false;
        window.location.href = completo ? "/perfil" : "/perfil/completar";
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
      <div className={styles.pagina}>
        <div className={`ui-card animate-fade-in ${styles.cartao}`}>
          <div className={styles.estado} role="alert">
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
            <h1 className={styles.titulo}>Erro na autenticação</h1>
            <p className={styles.estadoTexto}>{erroParametros || errorMsg}</p>
            <div className={styles.estadoAcoes}>
              <button
                type="button"
                onClick={() => router.push("/login")}
                className="ui-btn ui-btn-primary"
              >
                Voltar ao login
              </button>
            </div>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className={styles.pagina}>
      <div className={`ui-card animate-fade-in ${styles.cartao}`}>
        <div className={styles.estado} aria-busy="true">
          <div className={styles.spinner} aria-hidden="true" />
          <h1 className={styles.titulo}>
            {status === "concluindo" ? "Concluindo seu registro..." : "Autenticando com ORCID..."}
          </h1>
          <p className={styles.estadoTexto}>
            {status === "concluindo"
              ? "Estamos gravando os dados que você preencheu. Aguarde um momento."
              : "Estamos processando sua autenticação. Aguarde um momento."}
          </p>
        </div>
      </div>
    </div>
  );
}

export default function OrcidCallbackPage() {
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
      <OrcidCallbackContent />
    </Suspense>
  );
}
