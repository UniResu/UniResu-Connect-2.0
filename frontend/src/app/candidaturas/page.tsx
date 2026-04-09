"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { api } from "@/lib/api";
import { useAuth } from "@/contexts/AuthContext";
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
  aprovado: "Aprovado",
  recusado: "Recusado",
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

  if (authLoading || (isLoading && !errorMsg)) {
    return (
      <div className={styles.page}>
        <div className={styles.header}>
          <h1 className={styles.title}>Minhas Candidaturas</h1>
          <p className={styles.subtitle}>Carregando suas candidaturas…</p>
        </div>
        <div className={styles.skeletonList}>
          <div className={styles.skeletonCard} />
          <div className={styles.skeletonCard} />
          <div className={styles.skeletonCard} />
        </div>
      </div>
    );
  }

  return (
    <div className={styles.page}>
      <div className={styles.header}>
        <h1 className={styles.title}>Minhas Candidaturas</h1>
        <p className={styles.subtitle}>
          Acompanhe o status das suas candidaturas aos projetos acadêmicos.
        </p>
      </div>

      {errorMsg && <div className={styles.errorBox}>{errorMsg}</div>}

      {!errorMsg && candidaturas.length === 0 ? (
        <div className={styles.emptyState}>
          <div className={styles.emptyIcon}>📋</div>
          <h2 className={styles.emptyTitle}>
            Você ainda não enviou nenhuma candidatura
          </h2>
          <p className={styles.emptyDescription}>
            Explore os projetos acadêmicos disponíveis e candidate-se àqueles
            que combinam com seus interesses de pesquisa.
          </p>
          <Link href="/projetos" className={styles.emptyButton}>
            Ver Projetos Acadêmicos
          </Link>
        </div>
      ) : (
        <ul className={styles.list}>
          {candidaturas.map((c) => {
            const statusClass =
              c.status === "aprovado"
                ? styles.statusAprovado
                : c.status === "recusado"
                  ? styles.statusRecusado
                  : styles.statusPendente;

            return (
              <li key={c.id} className={styles.card}>
                <div className={styles.cardHeader}>
                  <h3 className={styles.cardTitle}>
                    {c.titulo_projeto || "Projeto Acadêmico"}
                  </h3>
                  <span className={`${styles.statusBadge} ${statusClass}`}>
                    {STATUS_LABEL[c.status] ?? c.status}
                  </span>
                </div>

                <div className={styles.cardMeta}>
                  <span className={styles.metaItem}>
                    <strong>Professor(a):</strong>{" "}
                    {c.nome_professor || "Não informado"}
                  </span>
                  <span className={styles.metaItem}>
                    <strong>Candidatura enviada em:</strong>{" "}
                    {formatarData(c.data_candidatura)}
                  </span>
                </div>

                {c.mensagem && (
                  <p className={styles.cardMessage}>{c.mensagem}</p>
                )}
              </li>
            );
          })}
        </ul>
      )}
    </div>
  );
}
