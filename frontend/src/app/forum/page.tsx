"use client";

/**
 * ForumPage, v4 (threads, estilo "Stack Overflow ultraminimalista")
 *
 * O fórum é uma lista de perguntas; o objetivo é expor conteúdo, não
 * interatividade. Regras de negócio:
 *  [R1] Editar/Excluir só aparecem para o autor (autoria por `autor_id`).
 *  [R2] Respostas com um único nível: a pergunta aberta mostra até 10, da
 *       mais antiga para a mais nova; com mais de 10, o link "Ver todas as N
 *       respostas" leva para /forum/[id], que mostra todas.
 *  [R3] Votos (a favor/contra) com atualização otimista; votos = likes - dislikes.
 *  [R4] Visitantes leem; logados perguntam, respondem, editam e votam.
 *  [R5] Privacidade: a API não devolve e-mail; o autor aparece como @username.
 *
 * Busca e ordenação são feitas no cliente sobre a lista já carregada.
 */

import { useState, useEffect, useCallback, useMemo } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { api } from "@/lib/api";
import { useAuth } from "@/contexts/AuthContext";
import type { User } from "@/types/user";
import {
  aplicarVotoLocal,
  conteudoDe,
  ehAutor,
  mensagemDeErro,
  parsearData,
  plural,
  votosDe,
  type EstadoRespostas,
  type TipoVoto,
  type Topico,
} from "./_componentes/forum";
import { AcoesAutor, CorpoPergunta, FormPergunta, MetaPergunta, Votos } from "./_componentes/Pergunta";
import { Respostas } from "./_componentes/Respostas";
import styles from "./forum.module.css";

type Ordem = "recentes" | "votadas";

// ── Helpers da lista ──────────────────────────────────────────────────────

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

// ── Linha da lista (fechada: título + resumo; aberta: thread completa) ───

interface LinhaPerguntaProps {
  topico: Topico;
  user: User | null;
  aberta: boolean;
  votando: boolean;
  falhouRespostas: boolean;
  onAbrir: () => void;
  onEditar: (topico: Topico, titulo: string, conteudo: string) => Promise<void>;
  onExcluir: (topicoId: string) => Promise<void>;
  onVotar: (topicoId: string, tipo: TipoVoto) => Promise<void>;
  onMudarRespostas: (topicoId: string, atualizar: (atual: EstadoRespostas) => EstadoRespostas) => void;
  onRecarregarRespostas: (topicoId: string) => void;
}

function LinhaPergunta({
  topico,
  user,
  aberta,
  votando,
  falhouRespostas,
  onAbrir,
  onEditar,
  onExcluir,
  onVotar,
  onMudarRespostas,
  onRecarregarRespostas,
}: LinhaPerguntaProps) {
  const [editando, setEditando] = useState(false);

  const autor = ehAutor(topico, user);
  const conteudo = conteudoDe(topico);
  // As respostas chegam com o GET do tópico, feito ao abrir a pergunta.
  const estadoRespostas: EstadoRespostas | null = topico.respostas
    ? { respostas: topico.respostas, total: topico.total_respostas }
    : null;

  // Se salvar falhar, `onEditar` lança e o formulário continua aberto.
  async function salvarEdicao(titulo: string, novoConteudo: string) {
    await onEditar(topico, titulo, novoConteudo);
    setEditando(false);
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
            <FormPergunta
              titulo={topico.titulo}
              conteudo={conteudo}
              onCancelar={() => setEditando(false)}
              onSalvar={salvarEdicao}
            />
          ) : (
            <>
              <CorpoPergunta topico={topico} />

              <div className={styles.rodape}>
                <Votos topico={topico} user={user} votando={votando} onVotar={(tipo) => onVotar(topico.id, tipo)} />

                <div className={styles.acoesAutor}>
                  {/* Endereço próprio da pergunta, para compartilhar ou ler com todas as respostas */}
                  <Link href={`/forum/${topico.id}`} className={styles.acaoTexto}>
                    Página da pergunta
                  </Link>
                  {/* [R1] Só o autor vê Editar/Excluir */}
                  {autor && <AcoesAutor onEditar={() => setEditando(true)} onExcluir={() => onExcluir(topico.id)} />}
                </div>
              </div>

              {/* [R2] Até 10 respostas e, se houver mais, o link para a página da pergunta */}
              <Respostas
                topicoId={topico.id}
                estado={estadoRespostas}
                modo="thread"
                falhou={falhouRespostas}
                onMudar={(atualizar) => onMudarRespostas(topico.id, atualizar)}
                onRecarregar={() => onRecarregarRespostas(topico.id)}
              />
            </>
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
  // Pergunta cujo GET (com as respostas) falhou ao abrir.
  const [falhaRespostasId, setFalhaRespostasId] = useState<string | null>(null);

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

  /**
   * Mescla a versão do servidor na lista. Votar e editar devolvem o tópico
   * sem `respostas`; a mescla mantém as que já estão na tela.
   */
  const substituir = useCallback((atualizado: Topico) => {
    setTopicos((prev) => prev.map((t) => (t.id === atualizado.id ? { ...t, ...atualizado } : t)));
  }, []);

  // O GET do tópico conta uma visualização e traz as primeiras respostas.
  const carregarDetalhe = useCallback(
    (id: string) => {
      setFalhaRespostasId(null);
      api
        .get<Topico>(`/api/forum/topicos/${id}`)
        .then(substituir)
        .catch(() => setFalhaRespostasId(id));
    },
    [substituir]
  );

  const abrir = useCallback(
    (id: string) => {
      if (abertoId === id) {
        setAbertoId(null);
        return;
      }
      setAbertoId(id);
      carregarDetalhe(id);
    },
    [abertoId, carregarDetalhe]
  );

  const mudarRespostas = useCallback(
    (topicoId: string, atualizar: (atual: EstadoRespostas) => EstadoRespostas) => {
      setTopicos((prev) =>
        prev.map((t) => {
          if (t.id !== topicoId || !t.respostas) return t;
          const novo = atualizar({ respostas: t.respostas, total: t.total_respostas });
          return { ...t, respostas: novo.respostas, total_respostas: novo.total };
        })
      );
    },
    []
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
      // Pergunta nova ainda não tem respostas: abre sem precisar de outro GET.
      setTopicos((prev) => [{ ...criado, respostas: [] }, ...prev]);
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

  // ── Excluir ([R1] só o autor; as respostas vão junto) ──
  const excluir = useCallback(
    async (topicoId: string) => {
      if (!isAuthenticated) return;
      if (!confirm("Excluir esta pergunta e as respostas dela? Esta ação não pode ser desfeita.")) return;
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
            <Link href="/login">Entre</Link> para fazer uma pergunta.
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
            <span className={styles.dicaForm}>Publicada como @{user?.username || "você"}.</span>
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
                  falhouRespostas={falhaRespostasId === topico.id}
                  onAbrir={() => abrir(topico.id)}
                  onEditar={editar}
                  onExcluir={excluir}
                  onVotar={votar}
                  onMudarRespostas={mudarRespostas}
                  onRecarregarRespostas={carregarDetalhe}
                />
              ))}
            </ul>
          )}
        </>
      )}
    </div>
  );
}
