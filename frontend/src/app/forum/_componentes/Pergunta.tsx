"use client";

/**
 * Peças da pergunta usadas na lista (/forum) e na página da pergunta
 * (/forum/[id]): linha de meta e controles de voto.
 */

import Link from "next/link";
import type { User } from "@/types/user";
import { dataCompleta, plural, tempoRelativo, votosDe, type TipoVoto, type Topico } from "./forum";
import styles from "../forum.module.css";

// ── Ícones (SVG inline, sem dependências e sem emoji) ─────────────────────

function Seta({ direcao }: { direcao: "cima" | "baixo" }) {
  return (
    <svg
      width="16"
      height="16"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
    >
      {direcao === "cima" ? <path d="M12 19V5M5 12l7-7 7 7" /> : <path d="M12 5v14M19 12l-7 7-7-7" />}
    </svg>
  );
}

// ── Meta: "@username | há 3 dias | 12 visualizações | 4 votos | 2 respostas" ──

export function MetaPergunta({ topico }: { topico: Topico }) {
  return (
    <div className={styles.meta}>
      <span className={`${styles.metaItem} ${styles.metaAutor}`} title={topico.autor_nome || undefined}>
        @{topico.autor_username || "usuario"}
      </span>
      <span className={styles.metaItem} title={dataCompleta(topico.data_criacao)}>
        {tempoRelativo(topico.data_criacao)}
      </span>
      <span className={styles.metaItem}>{plural(topico.visualizacoes, "visualização", "visualizações")}</span>
      <span className={styles.metaItem}>{plural(votosDe(topico), "voto", "votos")}</span>
      <span className={styles.metaItem}>{plural(topico.total_respostas ?? 0, "resposta", "respostas")}</span>
    </div>
  );
}

// ── Votos: setas para quem está logado, total e convite para visitantes ──

interface VotosProps {
  topico: Topico;
  user: User | null;
  votando: boolean;
  onVotar: (tipo: TipoVoto) => void;
}

export function Votos({ topico, user, votando, onVotar }: VotosProps) {
  const total = votosDe(topico);

  if (!user) {
    // Visitante: vê o total, não vota.
    return (
      <span className={styles.dicaLogin}>
        {plural(total, "voto", "votos")}. <Link href="/login">Entre</Link> para votar.
      </span>
    );
  }

  const meuVoto: TipoVoto | null = topico.likes.includes(user.id)
    ? "like"
    : topico.dislikes.includes(user.id)
      ? "dislike"
      : null;

  return (
    <div className={styles.votos}>
      <button
        type="button"
        className={styles.votoBtn}
        onClick={() => onVotar("like")}
        disabled={votando}
        aria-pressed={meuVoto === "like"}
        aria-label="Votar a favor"
        title="Votar a favor"
      >
        <Seta direcao="cima" />
      </button>
      <span className={styles.votosTotal} aria-live="polite">
        {total}
      </span>
      <button
        type="button"
        className={styles.votoBtn}
        onClick={() => onVotar("dislike")}
        disabled={votando}
        aria-pressed={meuVoto === "dislike"}
        aria-label="Votar contra"
        title="Votar contra"
      >
        <Seta direcao="baixo" />
      </button>
      <span className={styles.votosRotulo}>{plural(total, "voto", "votos")}</span>
    </div>
  );
}
