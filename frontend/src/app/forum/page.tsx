"use client";

/**
 * ForumPage — v3 (threads, estilo "Stack Overflow ultraminimalista")
 *
 * O fórum é uma lista de perguntas; o objetivo é expor conteúdo, não
 * interatividade. Regras de negócio:
 *  [R1] Editar/Excluir só aparecem para o autor (autoria por `autor_id`).
 *  [R2] Sem comentários/respostas: cada pergunta é um texto completo.
 *  [R3] Votos (a favor/contra) com atualização otimista; votos = likes - dislikes.
 *  [R4] Visitantes leem; logados perguntam, editam e votam.
 *  [R5] Privacidade: a API não devolve e-mail; o autor aparece como @username.
 *
 * Busca e ordenação são feitas no cliente sobre a lista já carregada.
 */

import { useState, useEffect, useCallback, useMemo } from "react";
import { useRouter } from "next/navigation";
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
  autor_id?: string | null;
  autor_username?: string | null;
  autor_nome?: string | null;
  data_criacao: string;
  visualizacoes: number;
  likes: string[]; // IDs de usuários
  dislikes: string[]; // IDs de usuários
}

type TipoVoto = "like" | "dislike";
type Ordem = "recentes" | "votadas";

// ── Helpers puros ─────────────────────────────────────────────────────────

function conteudoDe(topico: Topico) {
  return topico.conteudo_original || topico.descricao || "";
}

function votosDe(topico: Topico) {
  return topico.likes.length - topico.dislikes.length;
}

/** [R1] Autoria somente por id: o e-mail não existe mais na resposta. */
function ehAutor(topico: Topico, user: User | null) {
  return !!user && !!topico.autor_id && topico.autor_id === user.id;
}

/** Datas sem fuso vêm do Mongo em UTC; sem o "Z" o navegador leria como hora local. */
function parsearData(iso: string) {
  const temFuso = /(Z|[+-]\d{2}:?\d{2})$/.test(iso);
  return new Date(temFuso ? iso : `${iso}Z`);
}

function plural(n: number, singular: string, pluralForm: string) {
  return `${n} ${Math.abs(n) === 1 ? singular : pluralForm}`;
}

function tempoRelativo(iso: string, agora = Date.now()) {
  const t = parsearData(iso).getTime();
  if (Number.isNaN(t)) return "";
  const seg = Math.max(0, Math.round((agora - t) / 1000));
  if (seg < 60) return "agora";
  const min = Math.round(seg / 60);
  if (min < 60) return `há ${min} min`;
  const h = Math.round(min / 60);
  if (h < 24) return `há ${h} h`;
  const d = Math.round(h / 24);
  if (d < 30) return `há ${plural(d, "dia", "dias")}`;
  const m = Math.round(d / 30);
  if (m < 12) return `há ${plural(m, "mês", "meses")}`;
  return `há ${plural(Math.round(d / 365), "ano", "anos")}`;
}

function dataCompleta(iso: string) {
  const d = parsearData(iso);
  if (Number.isNaN(d.getTime())) return "";
  return d.toLocaleString("pt-BR", { dateStyle: "long", timeStyle: "short" });
}

/** Primeiras ~180 letras do conteúdo, cortadas em palavra inteira. */
function resumo(texto: string, max = 180) {
  const limpo = texto.replace(/\s+/g, " ").trim();
  if (limpo.length <= max) return limpo;
  const corte = limpo.lastIndexOf(" ", max);
  return `${limpo.slice(0, corte > max / 2 ? corte : max)}…`;
}

/** Busca sem acentos e sem caixa ("extensao" encontra "Extensão"). */
function normalizar(texto: string) {
  return texto.normalize("NFD").replace(/[̀-ͯ]/g, "").toLowerCase();
}

/** Parágrafos separados por linha em branco; quebras simples ficam dentro do <p>. */
function paragrafos(texto: string) {
  return texto
    .split(/\n\s*\n/)
    .map((p) => p.trim())
    .filter(Boolean);
}

/**
 * [R3] Mesma lógica de toggle do backend, aplicada localmente para a
 * atualização otimista: repetir o voto remove; votar o oposto troca.
 */
function aplicarVotoLocal(topico: Topico, usuarioId: string, tipo: TipoVoto): Topico {
  const tinhaLike = topico.likes.includes(usuarioId);
  const tinhaDislike = topico.dislikes.includes(usuarioId);
  const likes = topico.likes.filter((id) => id !== usuarioId);
  const dislikes = topico.dislikes.filter((id) => id !== usuarioId);
  if (tipo === "like" && !tinhaLike) likes.push(usuarioId);
  if (tipo === "dislike" && !tinhaDislike) dislikes.push(usuarioId);
  return { ...topico, likes, dislikes };
}

function mensagemDeErro(err: unknown, padrao: string) {
  const detail = (err as { detail?: unknown })?.detail;
  return typeof detail === "string" && detail ? detail : padrao;
}

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

// ── Meta: "@username | há 3 dias | 12 visualizações | 4 votos" ───────────

function MetaPergunta({ topico }: { topico: Topico }) {
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
    </div>
  );
}

// ── Linha da lista (fechada: título + resumo; aberta: thread completa) ───

interface LinhaPerguntaProps {
  topico: Topico;
  user: User | null;
  aberta: boolean;
  votando: boolean;
  onAbrir: () => void;
  onEditar: (topico: Topico, titulo: string, conteudo: string) => Promise<void>;
  onExcluir: (topicoId: string) => Promise<void>;
  onVotar: (topicoId: string, tipo: TipoVoto) => Promise<void>;
}

function LinhaPergunta({ topico, user, aberta, votando, onAbrir, onEditar, onExcluir, onVotar }: LinhaPerguntaProps) {
  const [editando, setEditando] = useState(false);
  const [editTitulo, setEditTitulo] = useState(topico.titulo);
  const [editConteudo, setEditConteudo] = useState(conteudoDe(topico));
  const [salvando, setSalvando] = useState(false);

  const autor = ehAutor(topico, user);
  const conteudo = conteudoDe(topico);

  const meuVoto = useMemo<TipoVoto | null>(() => {
    if (!user) return null;
    if (topico.likes.includes(user.id)) return "like";
    if (topico.dislikes.includes(user.id)) return "dislike";
    return null;
  }, [topico.likes, topico.dislikes, user]);

  function iniciarEdicao() {
    setEditTitulo(topico.titulo);
    setEditConteudo(conteudo);
    setEditando(true);
  }

  async function salvarEdicao(e: React.FormEvent) {
    e.preventDefault();
    if (!editTitulo.trim() || !editConteudo.trim()) return;
    setSalvando(true);
    try {
      await onEditar(topico, editTitulo.trim(), editConteudo.trim());
      setEditando(false);
    } catch {
      // O container já mostrou o erro; o formulário fica aberto para nova tentativa.
    } finally {
      setSalvando(false);
    }
  }

  return (
    <li className={`${styles.linha} ${aberta ? styles.linhaAberta : ""}`}>
      {/* O <button> dentro do <h2> é o controle acessível; o clique no cabeçalho inteiro também abre. */}
      <div className={styles.linhaCabecalho} onClick={onAbrir}>
        <h2 className={styles.linhaTitulo}>
          <button type="button" className={styles.linhaTituloBtn} aria-expanded={aberta}>
            {topico.titulo}
          </button>
        </h2>
        {!aberta && conteudo && <p className={styles.resumo}>{resumo(conteudo)}</p>}
        <MetaPergunta topico={topico} />
      </div>

      {aberta && (
        <div className={styles.thread}>
          {editando ? (
            <form className={styles.formPergunta} onSubmit={salvarEdicao}>
              <input
                type="text"
                value={editTitulo}
                onChange={(e) => setEditTitulo(e.target.value)}
                className={styles.campo}
                maxLength={200}
                required
                aria-label="Título"
              />
              <textarea
                value={editConteudo}
                onChange={(e) => setEditConteudo(e.target.value)}
                className={styles.campo}
                rows={8}
                required
                aria-label="Conteúdo"
              />
              <div className={styles.formAcoes}>
                <button type="button" className={styles.acaoTexto} onClick={() => setEditando(false)}>
                  Cancelar
                </button>
                <button type="submit" className={styles.btnPrimario} disabled={salvando}>
                  {salvando ? "Salvando..." : "Salvar"}
                </button>
              </div>
            </form>
          ) : (
            <div className={styles.corpo}>
              {conteudo ? paragrafos(conteudo).map((p, i) => <p key={i}>{p}</p>) : <p>Pergunta sem descrição.</p>}
            </div>
          )}

          {!editando && (
            <div className={styles.rodape}>
              {user ? (
                <div className={styles.votos}>
                  <button
                    type="button"
                    className={styles.votoBtn}
                    onClick={() => onVotar(topico.id, "like")}
                    disabled={votando}
                    aria-pressed={meuVoto === "like"}
                    aria-label="Votar a favor"
                    title="Votar a favor"
                  >
                    <Seta direcao="cima" />
                  </button>
                  <span className={styles.votosTotal} aria-live="polite">
                    {votosDe(topico)}
                  </span>
                  <button
                    type="button"
                    className={styles.votoBtn}
                    onClick={() => onVotar(topico.id, "dislike")}
                    disabled={votando}
                    aria-pressed={meuVoto === "dislike"}
                    aria-label="Votar contra"
                    title="Votar contra"
                  >
                    <Seta direcao="baixo" />
                  </button>
                  <span className={styles.votosRotulo}>{plural(votosDe(topico), "voto", "votos")}</span>
                </div>
              ) : (
                // [R4] Visitante: vê o total, não vota.
                <span className={styles.dicaLogin}>
                  {plural(votosDe(topico), "voto", "votos")}. <a href="/login">Entre</a> para votar.
                </span>
              )}

              {/* [R1] Só o autor vê Editar/Excluir */}
              {autor && (
                <div className={styles.acoesAutor}>
                  <button type="button" className={styles.acaoTexto} onClick={iniciarEdicao}>
                    Editar
                  </button>
                  <button
                    type="button"
                    className={`${styles.acaoTexto} ${styles.acaoPerigo}`}
                    onClick={() => onExcluir(topico.id)}
                  >
                    Excluir
                  </button>
                </div>
              )}
            </div>
          )}
        </div>
      )}
    </li>
  );
}

// ── ForumPage (container) ─────────────────────────────────────────────────

export default function ForumPage() {
  const { token, user, isAuthenticated } = useAuth();
  const router = useRouter();

  const [topicos, setTopicos] = useState<Topico[]>([]);
  const [carregando, setCarregando] = useState(true);
  const [erro, setErro] = useState("");
  const [abertoId, setAbertoId] = useState<string | null>(null);
  const [votandoId, setVotandoId] = useState<string | null>(null);

  // Busca e ordenação (no cliente)
  const [busca, setBusca] = useState("");
  const [ordem, setOrdem] = useState<Ordem>("recentes");

  // Nova pergunta
  const [mostrarForm, setMostrarForm] = useState(false);
  const [novoTitulo, setNovoTitulo] = useState("");
  const [novoConteudo, setNovoConteudo] = useState("");
  const [publicando, setPublicando] = useState(false);

  const carregar = useCallback(async () => {
    setCarregando(true);
    try {
      const data = await api.get<Topico[]>("/api/forum/topicos");
      setTopicos(data);
      setErro("");
    } catch {
      setTopicos([]);
      setErro("Não foi possível carregar as perguntas. Tente novamente em instantes.");
    } finally {
      setCarregando(false);
    }
  }, []);

  useEffect(() => {
    carregar();
  }, [carregar]);

  const visiveis = useMemo(() => {
    const termo = normalizar(busca.trim());
    const filtrados = termo
      ? topicos.filter((t) => normalizar(`${t.titulo} ${conteudoDe(t)}`).includes(termo))
      : topicos.slice();
    const porData = (a: Topico, b: Topico) =>
      parsearData(b.data_criacao).getTime() - parsearData(a.data_criacao).getTime();
    if (ordem === "votadas") {
      filtrados.sort((a, b) => votosDe(b) - votosDe(a) || b.visualizacoes - a.visualizacoes || porData(a, b));
    } else {
      filtrados.sort(porData);
    }
    return filtrados;
  }, [topicos, busca, ordem]);

  const substituir = useCallback((atualizado: Topico) => {
    setTopicos((prev) => prev.map((t) => (t.id === atualizado.id ? atualizado : t)));
  }, []);

  // Abrir conta uma visualização no servidor; a lista é atualizada com a resposta.
  const abrir = useCallback(
    (id: string) => {
      if (abertoId === id) {
        setAbertoId(null);
        return;
      }
      setAbertoId(id);
      api
        .get<Topico>(`/api/forum/topicos/${id}`)
        .then(substituir)
        .catch(() => {
          // Contagem de visualização é cosmética: falha silenciosa.
        });
    },
    [abertoId, substituir]
  );

  // ── Perguntar ([R4] só autenticados) ──
  async function publicar(e: React.FormEvent) {
    e.preventDefault();
    if (!isAuthenticated || !novoTitulo.trim() || !novoConteudo.trim()) return;
    if (user?.perfil_completo === false) {
      // A API exige o perfil concluído (vínculo e aceites) para publicar.
      router.push("/perfil/completar");
      return;
    }
    setPublicando(true);
    try {
      const criado = await api.post<Topico>(
        "/api/forum/topicos",
        { titulo: novoTitulo.trim(), conteudo: novoConteudo.trim() },
        { token: token || undefined }
      );
      setTopicos((prev) => [criado, ...prev]);
      setNovoTitulo("");
      setNovoConteudo("");
      setMostrarForm(false);
      setErro("");
      // Garante que a pergunta nova apareça (no topo) e já aberta.
      setBusca("");
      setOrdem("recentes");
      setAbertoId(criado.id);
    } catch (err) {
      setErro(mensagemDeErro(err, "Não foi possível publicar a pergunta."));
    } finally {
      setPublicando(false);
    }
  }

  // ── Editar ([R1] só o autor; o backend valida de novo) ──
  const editar = useCallback(
    async (topico: Topico, titulo: string, conteudo: string) => {
      if (!isAuthenticated || !ehAutor(topico, user)) return;
      try {
        const atualizado = await api.patch<Topico>(
          `/api/forum/topicos/${topico.id}`,
          { titulo, conteudo },
          { token: token || undefined }
        );
        substituir(atualizado);
        setErro("");
      } catch (err) {
        setErro(mensagemDeErro(err, "Não foi possível salvar a edição."));
        throw err; // a linha mantém o formulário aberto
      }
    },
    [isAuthenticated, token, user, substituir]
  );

  // ── Excluir ([R1] só o autor) ──
  const excluir = useCallback(
    async (topicoId: string) => {
      if (!isAuthenticated) return;
      if (!confirm("Excluir esta pergunta? Esta ação não pode ser desfeita.")) return;
      try {
        await api.delete(`/api/forum/topicos/${topicoId}`, { token: token || undefined });
        setTopicos((prev) => prev.filter((t) => t.id !== topicoId));
        setAbertoId((atual) => (atual === topicoId ? null : atual));
        setErro("");
      } catch (err) {
        setErro(mensagemDeErro(err, "Não foi possível excluir a pergunta."));
      }
    },
    [isAuthenticated, token]
  );

  // ── Votar ([R3] otimista, com rollback) ──
  const votar = useCallback(
    async (topicoId: string, tipo: TipoVoto) => {
      if (!isAuthenticated || !user || votandoId) return;
      setVotandoId(topicoId);

      let anterior: Topico[] = [];
      setTopicos((prev) => {
        anterior = prev;
        return prev.map((t) => (t.id === topicoId ? aplicarVotoLocal(t, user.id, tipo) : t));
      });

      try {
        const atualizado = await api.post<Topico>(
          `/api/forum/topicos/${topicoId}/reagir`,
          { tipo },
          { token: token || undefined }
        );
        substituir(atualizado);
      } catch (err) {
        setTopicos(anterior);
        setErro(mensagemDeErro(err, "Não foi possível registrar o voto."));
      } finally {
        setVotandoId(null);
      }
    },
    [isAuthenticated, user, token, votandoId, substituir]
  );

  const totalFiltrado =
    visiveis.length === topicos.length
      ? plural(topicos.length, "pergunta", "perguntas")
      : `${visiveis.length} de ${plural(topicos.length, "pergunta", "perguntas")}`;

  // ── Render ──
  return (
    <div className={styles.page}>
      <header className={styles.cabecalho}>
        <div>
          <h1 className={styles.titulo}>Fórum Acadêmico</h1>
          <p className={styles.subtitulo}>Perguntas sobre pesquisa, extensão e vida universitária.</p>
        </div>

        {/* [R4] Visitantes veem a lista e a dica para entrar */}
        {isAuthenticated ? (
          <button type="button" className={styles.btnPrimario} onClick={() => setMostrarForm((v) => !v)}>
            {mostrarForm ? "Cancelar" : "Fazer uma pergunta"}
          </button>
        ) : (
          <p className={styles.dicaLogin}>
            <a href="/login">Entre</a> para fazer uma pergunta.
          </p>
        )}
      </header>

      {isAuthenticated && mostrarForm && (
        <form onSubmit={publicar} className={styles.formPergunta}>
          <input
            type="text"
            value={novoTitulo}
            onChange={(e) => setNovoTitulo(e.target.value)}
            placeholder="Título: resuma a dúvida em uma frase"
            className={styles.campo}
            maxLength={200}
            required
            autoFocus
            aria-label="Título da pergunta"
          />
          <textarea
            value={novoConteudo}
            onChange={(e) => setNovoConteudo(e.target.value)}
            placeholder="Dê contexto: curso, o que você já tentou e o que precisa saber. Separe parágrafos com uma linha em branco."
            className={styles.campo}
            rows={6}
            required
            aria-label="Conteúdo da pergunta"
          />
          <div className={styles.formAcoes}>
            <span className={styles.dicaForm}>Publicada como @{user?.username || "você"}. Não há respostas: escreva a pergunta completa.</span>
            <button type="submit" className={styles.btnPrimario} disabled={publicando}>
              {publicando ? "Publicando..." : "Publicar pergunta"}
            </button>
          </div>
        </form>
      )}

      <div className={styles.barra}>
        <input
          type="search"
          value={busca}
          onChange={(e) => setBusca(e.target.value)}
          placeholder="Buscar nas perguntas"
          className={styles.busca}
          aria-label="Buscar nas perguntas"
        />
        <div className={styles.ordem} role="group" aria-label="Ordenar">
          <button
            type="button"
            className={styles.ordemBtn}
            aria-pressed={ordem === "recentes"}
            onClick={() => setOrdem("recentes")}
          >
            Recentes
          </button>
          <button
            type="button"
            className={styles.ordemBtn}
            aria-pressed={ordem === "votadas"}
            onClick={() => setOrdem("votadas")}
          >
            Mais votadas
          </button>
        </div>
      </div>

      {erro && (
        <p className={styles.erro} role="alert">
          {erro}{" "}
          {topicos.length === 0 && !carregando && (
            <button type="button" className={styles.btnSecundario} onClick={() => carregar()}>
              Tentar novamente
            </button>
          )}
        </p>
      )}

      {carregando ? (
        <div aria-busy="true">
          {[1, 2, 3, 4, 5].map((i) => (
            <div key={i} className={styles.esqueleto} />
          ))}
        </div>
      ) : erro && topicos.length === 0 ? null : (
        <>
          <p className={styles.contagem}>{totalFiltrado}</p>
          {visiveis.length === 0 ? (
            <p className={styles.vazio}>
              {topicos.length === 0 ? "Nenhuma pergunta ainda." : "Nenhuma pergunta corresponde à busca."}
            </p>
          ) : (
            <ul className={styles.lista}>
              {visiveis.map((topico) => (
                <LinhaPergunta
                  key={topico.id}
                  topico={topico}
                  user={user}
                  aberta={abertoId === topico.id}
                  votando={votandoId === topico.id}
                  onAbrir={() => abrir(topico.id)}
                  onEditar={editar}
                  onExcluir={excluir}
                  onVotar={votar}
                />
              ))}
            </ul>
          )}
        </>
      )}
    </div>
  );
}
