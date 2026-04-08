"use client";

/**
 * ForumPage — v2.2 (Refatorada)
 *
 * Regras de negócio aplicadas:
 *  [R1] Botões Editar/Excluir só existem no DOM para o autor do tópico.
 *  [R2] Nenhum input/lista/handler de comentários — apenas o corpo do tópico.
 *  [R3] Reações Like/Dislike com contadores e optimistic UI update.
 *  [R4] Auth guards: visitantes leem; logados criam/editam/reagem.
 *
 * Separação de responsabilidades:
 *  - `ForumPage`  → container, fetch, criação e orquestração de callbacks.
 *  - `TopicoCard` → card isolado com estado local de edição + UI memoizada.
 */

import { useState, useEffect, useCallback, useMemo } from "react";
import { api } from "@/lib/api";
import { useAuth } from "@/contexts/AuthContext";
import type { User } from "@/types/user";
import styles from "./forum.module.css";

// ── Tipos ─────────────────────────────────────────────────────────────────

interface Topico {
  id: string;
  titulo: string;
  conteudo_original?: string;
  descricao?: string; // campo legado — fallback de leitura apenas
  autor_email: string;
  autor_id?: string;
  data_criacao: string;
  visualizacoes: number;
  likes: string[];    // array de IDs de usuários
  dislikes: string[]; // array de IDs de usuários
}

type ReactionType = "like" | "dislike";

// ── Helpers puros (fora do componente p/ não recriar em cada render) ─────

/** [R1] Autoria: checa por id (novo) e email (fallback p/ docs legados). */
function verificarAutoria(topico: Topico, user: User | null): boolean {
  if (!user) return false;
  if (topico.autor_id && topico.autor_id === user.id) return true;
  return topico.autor_email === user.email;
}

/**
 * [R3] Aplica no cliente a mesma lógica de toggle que o backend executa,
 * permitindo atualização otimista antes do round-trip da API.
 *  - Mesmo tipo já presente → remove (toggle off).
 *  - Tipo oposto presente   → troca.
 *  - Nada presente          → adiciona.
 */
function aplicarReacaoLocal(
  topico: Topico,
  usuarioId: string,
  tipo: ReactionType
): Topico {
  const tinhaLike = topico.likes.includes(usuarioId);
  const tinhaDislike = topico.dislikes.includes(usuarioId);

  // Remove o usuário de ambos e reinsere só se for um toggle "on"
  const likes = topico.likes.filter((id) => id !== usuarioId);
  const dislikes = topico.dislikes.filter((id) => id !== usuarioId);

  if (tipo === "like" && !tinhaLike) likes.push(usuarioId);
  if (tipo === "dislike" && !tinhaDislike) dislikes.push(usuarioId);

  return { ...topico, likes, dislikes };
}

function formatarData(iso: string) {
  try {
    return new Date(iso).toLocaleDateString("pt-BR", {
      day: "2-digit",
      month: "short",
      year: "numeric",
    });
  } catch {
    return "";
  }
}

// ── TopicoCard ────────────────────────────────────────────────────────────

interface TopicoCardProps {
  topico: Topico;
  user: User | null;
  isAuthenticated: boolean;
  expandido: boolean;
  reagindo: boolean;
  onToggleExpandido: () => void;
  onEditar: (topico: Topico, titulo: string, conteudo: string) => Promise<void>;
  onExcluir: (topicoId: string) => Promise<void>;
  onReagir: (topicoId: string, tipo: ReactionType) => Promise<void>;
}

function TopicoCard({
  topico,
  user,
  isAuthenticated,
  expandido,
  reagindo,
  onToggleExpandido,
  onEditar,
  onExcluir,
  onReagir,
}: TopicoCardProps) {
  const [modoEdicao, setModoEdicao] = useState(false);
  const [editTitulo, setEditTitulo] = useState(topico.titulo);
  const [editConteudo, setEditConteudo] = useState(
    topico.conteudo_original || topico.descricao || ""
  );
  const [salvando, setSalvando] = useState(false);

  // [R1] Flag de autoria memoizada — só recalcula quando topico/user mudam.
  const ehAutor = useMemo(
    () => verificarAutoria(topico, user),
    [topico, user]
  );

  // [R3] Estado local da reação do usuário logado — deriva dos arrays.
  const minhaReacao = useMemo<ReactionType | null>(() => {
    if (!user) return null;
    if (topico.likes.includes(user.id)) return "like";
    if (topico.dislikes.includes(user.id)) return "dislike";
    return null;
  }, [topico.likes, topico.dislikes, user]);

  const totalLikes = topico.likes.length;
  const totalDislikes = topico.dislikes.length;

  function iniciarEdicao() {
    setEditTitulo(topico.titulo);
    setEditConteudo(topico.conteudo_original || topico.descricao || "");
    setModoEdicao(true);
  }

  function cancelarEdicao() {
    setModoEdicao(false);
  }

  async function salvarEdicao() {
    if (!editTitulo.trim() || !editConteudo.trim()) return;
    setSalvando(true);
    try {
      await onEditar(topico, editTitulo, editConteudo);
      setModoEdicao(false);
    } catch {
      // onEditar já exibe erro; mantemos o form aberto p/ o usuário tentar de novo.
    } finally {
      setSalvando(false);
    }
  }

  return (
    <div className={styles.topicoCard}>
      <button
        type="button"
        className={styles.topicoHeader}
        onClick={onToggleExpandido}
      >
        <div className={styles.topicoInfo}>
          <h3 className={styles.topicoTitulo}>{topico.titulo}</h3>
          <div className={styles.topicoMeta}>
            <span>{topico.autor_email}</span>
            <span>•</span>
            <span>{formatarData(topico.data_criacao)}</span>
            <span>•</span>
            <span>{topico.visualizacoes} visualizações</span>
          </div>
        </div>
        <span
          className={`${styles.chevron} ${expandido ? styles.chevronOpen : ""}`}
        >
          ▼
        </span>
      </button>

      {expandido && (
        <div className={styles.topicoBody}>
          {/* [R1] Botões Editar/Excluir — renderizados SOMENTE se for o autor */}
          {ehAutor && !modoEdicao && (
            <div className={styles.autorActions}>
              <button
                type="button"
                onClick={iniciarEdicao}
                className={styles.editBtn}
                title="Editar tópico"
              >
                ✏️ Editar
              </button>
              <button
                type="button"
                onClick={() => onExcluir(topico.id)}
                className={styles.deleteBtn}
                title="Excluir tópico"
              >
                🗑️ Excluir
              </button>
            </div>
          )}

          {modoEdicao ? (
            <div className={styles.editForm}>
              <input
                type="text"
                value={editTitulo}
                onChange={(e) => setEditTitulo(e.target.value)}
                className={styles.formInput}
                placeholder="Título"
              />
              <textarea
                value={editConteudo}
                onChange={(e) => setEditConteudo(e.target.value)}
                className={styles.formTextarea}
                rows={5}
                placeholder="Conteúdo"
              />
              <div className={styles.editFormActions}>
                <button
                  type="button"
                  onClick={cancelarEdicao}
                  className={styles.cancelEditBtn}
                >
                  Cancelar
                </button>
                <button
                  type="button"
                  onClick={salvarEdicao}
                  disabled={salvando}
                  className={styles.submitBtn}
                >
                  {salvando ? "Salvando..." : "Salvar Alterações"}
                </button>
              </div>
            </div>
          ) : (
            <div className={styles.topicoConteudoOriginal}>
              <p>
                {topico.conteudo_original ||
                  topico.descricao ||
                  "Tópico sem descrição."}
              </p>
            </div>
          )}

          <hr className={styles.divider} />

          {/* [R3] Barra de reações Like / Dislike */}
          <div className={styles.reactionBar}>
            {isAuthenticated ? (
              <>
                <button
                  type="button"
                  onClick={() => onReagir(topico.id, "like")}
                  disabled={reagindo}
                  aria-pressed={minhaReacao === "like"}
                  className={`${styles.reactionBtn} ${
                    minhaReacao === "like" ? styles.reactionActive : ""
                  }`}
                  title="Curtir"
                >
                  👍{" "}
                  <span className={styles.reactionCount}>{totalLikes}</span>
                </button>

                <button
                  type="button"
                  onClick={() => onReagir(topico.id, "dislike")}
                  disabled={reagindo}
                  aria-pressed={minhaReacao === "dislike"}
                  className={`${styles.reactionBtn} ${
                    minhaReacao === "dislike" ? styles.reactionActiveNeg : ""
                  }`}
                  title="Não curtir"
                >
                  👎{" "}
                  <span className={styles.reactionCount}>{totalDislikes}</span>
                </button>
              </>
            ) : (
              // [R4] Visitante: vê contadores, mas não interage.
              <div className={styles.reactionReadOnly}>
                <span className={styles.reactionBtnDisabled}>
                  👍 <span>{totalLikes}</span>
                </span>
                <span className={styles.reactionBtnDisabled}>
                  👎 <span>{totalDislikes}</span>
                </span>
                <span className={styles.loginHintSmall}>
                  <a href="/login">Entre</a> para reagir
                </span>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}

// ── ForumPage (container) ─────────────────────────────────────────────────

export default function ForumPage() {
  const { token, user, isAuthenticated } = useAuth();

  const [topicos, setTopicos] = useState<Topico[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [expandidoId, setExpandidoId] = useState<string | null>(null);
  const [reagindoId, setReagindoId] = useState<string | null>(null);

  // Criar tópico
  const [novoTitulo, setNovoTitulo] = useState("");
  const [novoConteudo, setNovoConteudo] = useState("");
  const [showForm, setShowForm] = useState(false);
  const [criando, setCriando] = useState(false);

  // ── Data fetching ──
  const carregarTopicos = useCallback(async () => {
    setIsLoading(true);
    try {
      const data = await api.get<Topico[]>("/api/forum/topicos");
      setTopicos(data);
    } catch {
      setTopicos([]);
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    carregarTopicos();
  }, [carregarTopicos]);

  // ── Criar tópico ([R4] só autenticados) ──
  async function criarTopico(e: React.FormEvent) {
    e.preventDefault();
    if (!isAuthenticated) return;
    if (!novoTitulo.trim() || !novoConteudo.trim()) return;
    setCriando(true);
    try {
      await api.post(
        "/api/forum/topicos",
        { titulo: novoTitulo, conteudo: novoConteudo },
        { token: token || undefined }
      );
      setNovoTitulo("");
      setNovoConteudo("");
      setShowForm(false);
      await carregarTopicos();
    } catch {
      alert("Erro ao criar tópico.");
    } finally {
      setCriando(false);
    }
  }

  // ── Editar ([R1] só o autor; backend valida de novo) ──
  const editarTopico = useCallback(
    async (topico: Topico, titulo: string, conteudo: string) => {
      if (!isAuthenticated || !verificarAutoria(topico, user)) return;
      try {
        const atualizado = await api.patch<Topico>(
          `/api/forum/topicos/${topico.id}`,
          { titulo, conteudo },
          { token: token || undefined }
        );
        setTopicos((prev) =>
          prev.map((t) => (t.id === topico.id ? atualizado : t))
        );
      } catch (err) {
        alert("Erro ao salvar edição.");
        throw err; // propaga p/ o TopicoCard manter o form aberto
      }
    },
    [isAuthenticated, token, user]
  );

  // ── Excluir ([R1] só o autor) ──
  const excluirTopico = useCallback(
    async (topicoId: string) => {
      if (!isAuthenticated) return;
      if (
        !confirm(
          "Tem certeza que deseja excluir este tópico? Esta ação é irreversível."
        )
      )
        return;
      try {
        await api.delete(`/api/forum/topicos/${topicoId}`, {
          token: token || undefined,
        });
        setTopicos((prev) => prev.filter((t) => t.id !== topicoId));
        setExpandidoId((curr) => (curr === topicoId ? null : curr));
      } catch {
        alert("Erro ao excluir tópico.");
      }
    },
    [isAuthenticated, token]
  );

  // ── Reagir ([R3] optimistic update com rollback) ──
  const reagirTopico = useCallback(
    async (topicoId: string, tipo: ReactionType) => {
      if (!isAuthenticated || !user) return;
      if (reagindoId) return; // evita double-click

      setReagindoId(topicoId);

      // Snapshot p/ rollback em caso de falha.
      let snapshot: Topico[] = [];
      setTopicos((prev) => {
        snapshot = prev;
        return prev.map((t) =>
          t.id === topicoId ? aplicarReacaoLocal(t, user.id, tipo) : t
        );
      });

      try {
        const atualizado = await api.post<Topico>(
          `/api/forum/topicos/${topicoId}/reagir`,
          { tipo },
          { token: token || undefined }
        );
        // Reconcilia com a resposta autoritativa do servidor.
        setTopicos((prev) =>
          prev.map((t) => (t.id === topicoId ? atualizado : t))
        );
      } catch {
        setTopicos(snapshot);
        alert("Erro ao registrar reação.");
      } finally {
        setReagindoId(null);
      }
    },
    [isAuthenticated, user, token, reagindoId]
  );

  const toggleExpandido = useCallback((id: string) => {
    setExpandidoId((curr) => (curr === id ? null : id));
  }, []);

  // ── Render ──
  return (
    <div className={styles.page}>
      <div className={styles.header}>
        <div className={styles.headerTop}>
          <div>
            <h1 className={styles.title}>💬 Fórum Acadêmico</h1>
            <p className={styles.subtitle}>
              Discussões, dúvidas e conhecimento compartilhado
            </p>
          </div>

          {/* [R4] Visitantes não veem o botão de criar tópico */}
          {isAuthenticated ? (
            <button
              type="button"
              onClick={() => setShowForm((v) => !v)}
              className={styles.newTopicButton}
            >
              {showForm ? "Cancelar" : "+ Novo Tópico"}
            </button>
          ) : (
            <p className={styles.loginHint}>
              <a href="/login">Entre</a> para publicar um tópico
            </p>
          )}
        </div>
      </div>

      {/* [R4] Formulário de criação — exclusivo para autenticados */}
      {isAuthenticated && showForm && (
        <form onSubmit={criarTopico} className={styles.createForm}>
          <input
            type="text"
            value={novoTitulo}
            onChange={(e) => setNovoTitulo(e.target.value)}
            placeholder="Título do tópico"
            required
            className={styles.formInput}
          />
          <textarea
            value={novoConteudo}
            onChange={(e) => setNovoConteudo(e.target.value)}
            placeholder="Escreva o conteúdo do seu tópico..."
            required
            rows={4}
            className={styles.formTextarea}
          />
          <button type="submit" disabled={criando} className={styles.submitBtn}>
            {criando ? "Publicando..." : "Publicar Tópico"}
          </button>
        </form>
      )}

      {isLoading ? (
        <div className={styles.loadingList}>
          {[1, 2, 3, 4].map((i) => (
            <div key={i} className={styles.skeletonRow} />
          ))}
        </div>
      ) : topicos.length === 0 ? (
        <div className={styles.emptyState}>
          <span className={styles.emptyIcon}>🗣️</span>
          <h3>Nenhum tópico ainda</h3>
          <p>Seja o primeiro a iniciar uma discussão!</p>
        </div>
      ) : (
        <div className={styles.topicosList}>
          {topicos.map((topico) => (
            <TopicoCard
              key={topico.id}
              topico={topico}
              user={user}
              isAuthenticated={isAuthenticated}
              expandido={expandidoId === topico.id}
              reagindo={reagindoId === topico.id}
              onToggleExpandido={() => toggleExpandido(topico.id)}
              onEditar={editarTopico}
              onExcluir={excluirTopico}
              onReagir={reagirTopico}
            />
          ))}
        </div>
      )}
    </div>
  );
}
