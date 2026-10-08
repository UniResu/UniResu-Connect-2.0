"use client";

/**
 * Peças da pergunta usadas na lista (/forum) e na página da pergunta
 * (/forum/[id]): ícones, linha de meta, chips de contagem, corpo em
 * parágrafos, controles de voto, ações do autor e o formulário de edição.
 *
 * Botões e campos usam as classes globais ui-* (globals.css); o módulo só
 * acrescenta layout e os estados específicos do fórum.
 */

import { useId, useState } from "react";
import Link from "next/link";
import type { User } from "@/types/user";
import {
  conteudoDe,
  dataCompleta,
  paragrafos,
  plural,
  tempoRelativo,
  votosDe,
  type TipoVoto,
  type Topico,
} from "./forum";
import styles from "../forum.module.css";

// ── Ícones (SVG inline no estilo Lucide: traço 2, sem emoji) ─────────────

type NomeIcone = "busca" | "cima" | "baixo" | "esquerda" | "mais";

const CAMINHOS: Record<NomeIcone, React.ReactNode> = {
  busca: (
    <>
      <circle cx="11" cy="11" r="8" />
      <path d="m21 21-4.3-4.3" />
    </>
  ),
  cima: (
    <>
      <path d="M12 19V5" />
      <path d="m5 12 7-7 7 7" />
    </>
  ),
  baixo: (
    <>
      <path d="M12 5v14" />
      <path d="m19 12-7 7-7-7" />
    </>
  ),
  esquerda: (
    <>
      <path d="m12 19-7-7 7-7" />
      <path d="M19 12H5" />
    </>
  ),
  mais: (
    <>
      <path d="M5 12h14" />
      <path d="M12 5v14" />
    </>
  ),
};

export function Icone({ nome, tamanho = 20 }: { nome: NomeIcone; tamanho?: number }) {
  return (
    <svg
      width={tamanho}
      height={tamanho}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
      focusable="false"
    >
      {CAMINHOS[nome]}
    </svg>
  );
}

// ── Meta: "@username | há 3 dias | 12 visualizações" ─────────────────────

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
    </div>
  );
}

// ── Chips: votos e respostas (o pai decide onde ficam) ───────────────────

export function ChipsPergunta({ topico }: { topico: Topico }) {
  const respostas = topico.total_respostas ?? 0;
  return (
    <>
      <span className="ui-chip">{plural(votosDe(topico), "voto", "votos")}</span>
      <span className={respostas > 0 ? "ui-chip ui-chip-primary" : "ui-chip"}>
        {plural(respostas, "resposta", "respostas")}
      </span>
    </>
  );
}

// ── Corpo: parágrafos separados por linha em branco ───────────────────────

export function CorpoPergunta({ topico }: { topico: Topico }) {
  const conteudo = conteudoDe(topico);
  return (
    <div className={styles.corpo}>
      {conteudo ? paragrafos(conteudo).map((p, i) => <p key={i}>{p}</p>) : <p>Pergunta sem descrição.</p>}
    </div>
  );
}

// ── Ações do autor: Editar e Excluir (a API confere a autoria de novo) ────

interface AcoesAutorProps {
  onEditar: () => void;
  onExcluir: () => void;
}

export function AcoesAutor({ onEditar, onExcluir }: AcoesAutorProps) {
  return (
    <div className={styles.acoes}>
      <button type="button" className="ui-btn ui-btn-ghost ui-btn-sm" onClick={onEditar}>
        Editar
      </button>
      <button type="button" className={`ui-btn ui-btn-ghost ui-btn-sm ${styles.acaoPerigo}`} onClick={onExcluir}>
        Excluir
      </button>
    </div>
  );
}

// ── Edição da pergunta: título e conteúdo ─────────────────────────────────

interface FormPerguntaProps {
  titulo: string;
  conteudo: string;
  onCancelar: () => void;
  /** Deve lançar em caso de falha: o formulário então continua aberto para nova tentativa. */
  onSalvar: (titulo: string, conteudo: string) => Promise<void>;
}

export function FormPergunta({ titulo, conteudo, onCancelar, onSalvar }: FormPerguntaProps) {
  const idBase = useId();
  const [editTitulo, setEditTitulo] = useState(titulo);
  const [editConteudo, setEditConteudo] = useState(conteudo);
  const [salvando, setSalvando] = useState(false);

  async function salvar(e: React.FormEvent) {
    e.preventDefault();
    if (!editTitulo.trim() || !editConteudo.trim()) return;
    setSalvando(true);
    try {
      await onSalvar(editTitulo.trim(), editConteudo.trim());
    } catch {
      // Quem chamou já mostrou o erro; os campos ficam como estavam.
    } finally {
      setSalvando(false);
    }
  }

  return (
    <form className={`ui-card ${styles.formCard} ${styles.formEdicaoPergunta}`} onSubmit={salvar}>
      <div>
        <label htmlFor={`${idBase}-titulo`} className="ui-label">
          Título
        </label>
        <input
          id={`${idBase}-titulo`}
          type="text"
          value={editTitulo}
          onChange={(e) => setEditTitulo(e.target.value)}
          className="ui-field"
          maxLength={200}
          required
        />
      </div>
      <div>
        <label htmlFor={`${idBase}-conteudo`} className="ui-label">
          Conteúdo
        </label>
        <textarea
          id={`${idBase}-conteudo`}
          value={editConteudo}
          onChange={(e) => setEditConteudo(e.target.value)}
          className="ui-field"
          rows={8}
          required
        />
      </div>
      <div className={styles.formAcoes}>
        <button type="button" className="ui-btn ui-btn-ghost" onClick={onCancelar}>
          Cancelar
        </button>
        <button type="submit" className="ui-btn ui-btn-primary" disabled={salvando}>
          {salvando ? "Salvando..." : "Salvar"}
        </button>
      </div>
    </form>
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
        className={`ui-btn ui-btn-ghost ui-btn-sm ${styles.votoBtn}`}
        onClick={() => onVotar("like")}
        disabled={votando}
        aria-pressed={meuVoto === "like"}
        aria-label="Votar a favor"
        title="Votar a favor"
      >
        <Icone nome="cima" tamanho={18} />
      </button>
      <span className={styles.votosTotal} aria-live="polite">
        {total}
      </span>
      <button
        type="button"
        className={`ui-btn ui-btn-ghost ui-btn-sm ${styles.votoBtn}`}
        onClick={() => onVotar("dislike")}
        disabled={votando}
        aria-pressed={meuVoto === "dislike"}
        aria-label="Votar contra"
        title="Votar contra"
      >
        <Icone nome="baixo" tamanho={18} />
      </button>
      <span className={styles.votosRotulo}>{Math.abs(total) === 1 ? "voto" : "votos"}</span>
    </div>
  );
}
