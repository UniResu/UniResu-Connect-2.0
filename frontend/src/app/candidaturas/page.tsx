"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { api } from "@/lib/api";
import { useAuth } from "@/contexts/AuthContext";
import { IconeFoguete } from "@/components/ui/Icones";
import styles from "./candidaturas.module.css";

interface Candidatura {
  id: string;
  id_projeto: string;
  id_aluno?: string | null;
  email_aluno: string;
  data_candidatura: string;
  status: "pendente" | "aprovado" | "recusado";
  mensagem?: string | null;
  titulo_projeto?: string | null;
  nome_professor?: string | null;
}

const STATUS_LABEL: Record<Candidatura["status"], string> = {
  pendente: "Pendente",
  aprovado: "Aprovada",
  recusado: "Recusada",
};

const STATUS_CHIP: Record<Candidatura["status"], string> = {
  pendente: "ui-chip-warning",
  aprovado: "ui-chip-success",
  recusado: "ui-chip-error",
};

function formatarData(iso: string): string {
  try {
    const d = new Date(iso);
    return d.toLocaleDateString("pt-BR", {
      day: "2-digit",
      month: "long",
      year: "numeric",
    });
  } catch {
    return iso;
  }
}

const svgProps = {
  viewBox: "0 0 24 24",
  fill: "none",
  stroke: "currentColor",
  strokeWidth: 2,
  strokeLinecap: "round" as const,
  strokeLinejoin: "round" as const,
  "aria-hidden": true,
};

function IconeUsuario() {
  return (
    <svg width="16" height="16" {...svgProps}>
      <path d="M19 21v-2a4 4 0 0 0-4-4H9a4 4 0 0 0-4 4v2" />
      <circle cx="12" cy="7" r="4" />
    </svg>
  );
}

function IconeCalendario() {
  return (
    <svg width="16" height="16" {...svgProps}>
      <rect x="3" y="4" width="18" height="18" rx="2" />
      <path d="M16 2v4" />
      <path d="M8 2v4" />
      <path d="M3 10h18" />
    </svg>
  );
}

export default function CandidaturasPage() {
  const { token, isAuthenticated, isLoading: authLoading } = useAuth();
  const router = useRouter();

  const [candidaturas, setCandidaturas] = useState<Candidatura[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [errorMsg, setErrorMsg] = useState("");

  // Redireciona visitantes não autenticados para o login.
  useEffect(() => {
    if (!authLoading && !isAuthenticated) {
      router.push("/login");
    }
  }, [authLoading, isAuthenticated, router]);

  useEffect(() => {
    if (!token) return;

    let cancelled = false;

    async function carregar() {
      setIsLoading(true);
      setErrorMsg("");
      try {
        const data = await api.get<Candidatura[]>("/api/candidaturas/me", {
          token: token || undefined,
        });
        if (!cancelled) setCandidaturas(data);
      } catch (err) {
        if (!cancelled) {
          const detail =
            (err as { detail?: string })?.detail ||
            "Não foi possível carregar suas candidaturas.";
          setErrorMsg(detail);
          setCandidaturas([]);
        }
      } finally {
        if (!cancelled) setIsLoading(false);
      }
    }

    carregar();
    return () => {
      cancelled = true;
    };
  }, [token]);

  const carregando = authLoading || (isLoading && !errorMsg);

  return (
    <div className={styles.pagina}>
      <div className={styles.container}>
        <header className="ui-page-header">
          <h1 className="ui-page-title">Minhas candidaturas</h1>
          <p className="ui-page-subtitle">
            Acompanhe o andamento das candidaturas que você enviou aos projetos acadêmicos.
          </p>
        </header>

        {carregando ? (
          <div className={styles.lista} aria-busy="true" aria-label="Carregando candidaturas">
            {[0, 1, 2].map((i) => (
              <div key={i} className={`skeleton ${styles.esqueleto}`} />
            ))}
          </div>
        ) : errorMsg ? (
          <div className={styles.aviso} role="alert">
            {errorMsg}
          </div>
        ) : candidaturas.length === 0 ? (
          <div className={`ui-card ${styles.vazio}`}>
            <span className={styles.vazioIcone}>
              <IconeFoguete tamanho={28} />
            </span>
            <h2 className={styles.vazioTitulo}>Você ainda não enviou nenhuma candidatura</h2>
            <p className={styles.vazioTexto}>
              Explore os projetos acadêmicos disponíveis e candidate-se àqueles que combinam com seus
              interesses de pesquisa.
            </p>
            <Link href="/projetos" className="ui-btn ui-btn-primary">
              Explorar projetos
            </Link>
          </div>
        ) : (
          <ul className={`${styles.lista} animate-stagger`}>
            {candidaturas.map((c) => (
              <li key={c.id} className={`ui-card ${styles.card}`}>
                <div className={styles.cardTopo}>
                  <h2 className={styles.cardTitulo}>{c.titulo_projeto || "Projeto acadêmico"}</h2>
                  <span className={`ui-chip ${STATUS_CHIP[c.status] ?? ""}`}>
                    {STATUS_LABEL[c.status] ?? c.status}
                  </span>
                </div>

                <div className={styles.meta}>
                  <span className={styles.metaItem}>
                    <IconeUsuario />
                    <span>Docente: {c.nome_professor || "não informado"}</span>
                  </span>
                  <span className={styles.metaItem}>
                    <IconeCalendario />
                    <span>Enviada em {formatarData(c.data_candidatura)}</span>
                  </span>
                </div>

                {c.mensagem && (
                  <div className={styles.mensagem}>
                    <span className={styles.mensagemRotulo}>Sua mensagem</span>
                    <p>{c.mensagem}</p>
                  </div>
                )}
              </li>
            ))}
          </ul>
        )}
      </div>
    </div>
  );
}
