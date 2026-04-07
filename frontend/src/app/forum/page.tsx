"use client";

import { useState, useEffect } from "react";
import { api } from "@/lib/api";
import { useAuth } from "@/contexts/AuthContext";
import styles from "./forum.module.css";

interface Resposta {
  _id: string;
  conteudo: string;
  autor_email: string;
  data_postagem: string;
}

interface Topico {
  id: string;
  titulo: string;
  conteudo_original?: string;
  descricao?: string;
  autor_email: string;
  data_criacao: string;
  visualizacoes: number;
  respostas: Resposta[];
}

export default function ForumPage() {
  const { token, isAuthenticated } = useAuth();
  const [topicos, setTopicos] = useState<Topico[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [expandido, setExpandido] = useState<string | null>(null);

  // Criar tópico
  const [novoTitulo, setNovoTitulo] = useState("");
  const [novoConteudo, setNovoConteudo] = useState("");
  const [showForm, setShowForm] = useState(false);
  const [criando, setCriando] = useState(false);

  // Responder
  const [respostaTexto, setRespostaTexto] = useState("");
  const [respondendo, setRespondendo] = useState(false);

  useEffect(() => {
    carregarTopicos();
  }, []);

  async function carregarTopicos() {
    setIsLoading(true);
    try {
      const data = await api.get<Topico[]>("/api/forum/topicos");
      setTopicos(data);
    } catch {
      setTopicos([]);
    } finally {
      setIsLoading(false);
    }
  }

  async function criarTopico(e: React.FormEvent) {
    e.preventDefault();
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

  async function responderTopico(topicoId: string) {
    if (!respostaTexto.trim()) return;
    setRespondendo(true);
    try {
      await api.post(
        `/api/forum/topicos/${topicoId}/responder`,
        { conteudo: respostaTexto },
        { token: token || undefined }
      );
      setRespostaTexto("");
      await carregarTopicos();
    } catch {
      alert("Erro ao responder.");
    } finally {
      setRespondendo(false);
    }
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
          {isAuthenticated && (
            <button
              onClick={() => setShowForm(!showForm)}
              className={styles.newTopicButton}
            >
              {showForm ? "Cancelar" : "+ Novo Tópico"}
            </button>
          )}
        </div>
      </div>

      {/* ── Criar Tópico ── */}
      {showForm && (
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

      {/* ── Lista de Tópicos ── */}
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
            <div key={topico.id} className={styles.topicoCard}>
              <button
                className={styles.topicoHeader}
                onClick={() =>
                  setExpandido(expandido === topico.id ? null : topico.id)
                }
              >
                <div className={styles.topicoInfo}>
                  <h3 className={styles.topicoTitulo}>{topico.titulo}</h3>
                  <div className={styles.topicoMeta}>
                    <span>{topico.autor_email}</span>
                    <span>•</span>
                    <span>{formatarData(topico.data_criacao)}</span>
                    <span>•</span>
                    <span>{topico.respostas.length} respostas</span>
                  </div>
                </div>
                <span
                  className={`${styles.chevron} ${expandido === topico.id ? styles.chevronOpen : ""}`}
                >
                  ▼
                </span>
              </button>

              {expandido === topico.id && (
                <div className={styles.topicoBody}>
                  {/* Main Topic Question/Content */}
                  <div className={styles.topicoConteudoOriginal}>
                    <p>{topico.conteudo_original || topico.descricao || "Tópico sem descrição."}</p>
                  </div>
                  <hr className={styles.divider} />

                  {/* Respostas */}
                  {topico.respostas && topico.respostas.length > 0 && (
                    <div className={styles.respostasList}>
                      {topico.respostas.map((resp) => (
                        <div key={resp._id} className={styles.respostaItem}>
                          <div className={styles.respostaAutor}>
                            <div className={styles.respostaAvatar}>
                              {resp.autor_email.charAt(0).toUpperCase()}
                            </div>
                            <div>
                              <span className={styles.respostaEmail}>
                                {resp.autor_email}
                              </span>
                              <span className={styles.respostaData}>
                                {formatarData(resp.data_postagem)}
                              </span>
                            </div>
                          </div>
                          <p className={styles.respostaConteudo}>
                            {resp.conteudo}
                          </p>
                        </div>
                      ))}
                    </div>
                  )}

                  {/* Responder */}
                  {isAuthenticated && (
                    <div className={styles.responderForm}>
                      <textarea
                        value={respostaTexto}
                        onChange={(e) => setRespostaTexto(e.target.value)}
                        placeholder="Escreva sua resposta..."
                        rows={2}
                        className={styles.responderTextarea}
                      />
                      <button
                        onClick={() => responderTopico(topico.id)}
                        disabled={respondendo || !respostaTexto.trim()}
                        className={styles.responderBtn}
                      >
                        {respondendo ? "Enviando..." : "Responder"}
                      </button>
                    </div>
                  )}
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
