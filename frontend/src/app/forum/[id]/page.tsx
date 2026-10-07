"use client";

/**
 * Página de uma pergunta (/forum/[id]): a pergunta completa, todas as
 * respostas em blocos de RESPOSTAS_POR_PAGINA (botão "Carregar mais") e o
 * formulário de resposta no fim.
 *
 * O GET do tópico já traz o primeiro bloco de respostas, então a página
 * abre com uma requisição só; o mesmo GET conta uma visualização. Votar,
 * editar e excluir a pergunta seguem as regras da lista (/forum): só o
 * autor edita e exclui, e a API confere a autoria de novo.
 *
 * `params` é uma Promise no App Router: em um componente de cliente ela é
 * lida com `use` (ver node_modules/next/dist/docs, file-conventions/page).
 */

import { use, useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { api } from "@/lib/api";
import { useAuth } from "@/contexts/AuthContext";
import {
  RESPOSTAS_POR_PAGINA,
  aplicarVotoLocal,
  conteudoDe,
  ehAutor,
  mensagemDeErro,
  statusDoErro,
  type EstadoRespostas,
  type TipoVoto,
  type Topico,
} from "../_componentes/forum";
import { AcoesAutor, CorpoPergunta, FormPergunta, MetaPergunta, Votos } from "../_componentes/Pergunta";
import { Respostas } from "../_componentes/Respostas";
import styles from "../forum.module.css";

export default function PaginaPergunta({ params }: { params: Promise<{ id: string }> }) {
  const { id } = use(params);
  const { token, user, isAuthenticated } = useAuth();
  const router = useRouter();

  const [topico, setTopico] = useState<Topico | null>(null);
  const [carregando, setCarregando] = useState(true);
  const [naoEncontrada, setNaoEncontrada] = useState(false);
  const [erro, setErro] = useState("");
  const [editando, setEditando] = useState(false);
  const [votando, setVotando] = useState(false);

  const carregar = useCallback(async () => {
    setCarregando(true);
    setNaoEncontrada(false);
    setErro("");
    try {
      const data = await api.get<Topico>(`/api/forum/topicos/${id}?limite_respostas=${RESPOSTAS_POR_PAGINA}`);
      setTopico(data);
    } catch (err) {
      // 400 é um id fora do formato; 404, uma pergunta que não existe mais.
      const status = statusDoErro(err);
      if (status === 400 || status === 404) {
        setNaoEncontrada(true);
      } else {
        setErro("Não foi possível carregar a pergunta. Tente novamente em instantes.");
      }
    } finally {
      setCarregando(false);
    }
  }, [id]);

  useEffect(() => {
    carregar();
  }, [carregar]);

  // O título da aba passa a ser o da pergunta enquanto a página está aberta.
  const titulo = topico?.titulo;
  useEffect(() => {
    if (!titulo) return;
    const anterior = document.title;
    document.title = `${titulo} | Fórum UniResu Connect`;
    return () => {
      document.title = anterior;
    };
  }, [titulo]);

  /**
   * Mescla a versão do servidor na pergunta em tela. Votar e editar devolvem
   * o tópico sem `respostas`; a mescla mantém as que já foram carregadas.
   */
  const mesclar = useCallback((atualizado: Topico) => {
    setTopico((atual) => (atual ? { ...atual, ...atualizado } : atualizado));
  }, []);

  const estadoRespostas: EstadoRespostas | null = topico
    ? { respostas: topico.respostas ?? [], total: topico.total_respostas }
    : null;

  const mudarRespostas = useCallback((atualizar: (atual: EstadoRespostas) => EstadoRespostas) => {
    setTopico((atual) => {
      if (!atual) return atual;
      const novo = atualizar({ respostas: atual.respostas ?? [], total: atual.total_respostas });
      return { ...atual, respostas: novo.respostas, total_respostas: novo.total };
    });
  }, []);

  // ── Votar (otimista; só likes e dislikes voltam atrás se a API falhar) ──
  async function votar(tipo: TipoVoto) {
    if (!isAuthenticated || !user || !topico || votando) return;
    setVotando(true);
    const { likes, dislikes } = topico;
    setTopico(aplicarVotoLocal(topico, user.id, tipo));
    try {
      const atualizado = await api.post<Topico>(
        `/api/forum/topicos/${topico.id}/reagir`,
        { tipo },
        { token: token || undefined }
      );
      mesclar(atualizado);
      setErro("");
    } catch (err) {
      setTopico((atual) => (atual ? { ...atual, likes, dislikes } : atual));
      setErro(mensagemDeErro(err, "Não foi possível registrar o voto."));
    } finally {
      setVotando(false);
    }
  }

  // ── Editar (só o autor; se falhar, lança e o formulário continua aberto) ──
  async function editar(novoTitulo: string, novoConteudo: string) {
    if (!topico || !isAuthenticated || !ehAutor(topico, user)) return;
    try {
      const atualizado = await api.patch<Topico>(
        `/api/forum/topicos/${topico.id}`,
        { titulo: novoTitulo, conteudo: novoConteudo },
        { token: token || undefined }
      );
      mesclar(atualizado);
      setErro("");
      setEditando(false);
    } catch (err) {
      setErro(mensagemDeErro(err, "Não foi possível salvar a edição."));
      throw err;
    }
  }

  // ── Excluir (só o autor; as respostas vão junto) ──
  async function excluir() {
    if (!topico || !isAuthenticated) return;
    if (!confirm("Excluir esta pergunta e as respostas dela? Esta ação não pode ser desfeita.")) return;
    try {
      await api.delete(`/api/forum/topicos/${topico.id}`, { token: token || undefined });
      router.push("/forum");
    } catch (err) {
      setErro(mensagemDeErro(err, "Não foi possível excluir a pergunta."));
    }
  }

  // ── Render ──
  return (
    <div className={styles.page}>
      <Link href="/forum" className={styles.voltar}>
        Voltar ao fórum
      </Link>

      {carregando ? (
        <div aria-busy="true">
          <div className={styles.esqueleto} />
          <div className={styles.esqueleto} />
          <div className={styles.esqueleto} />
        </div>
      ) : naoEncontrada ? (
        <section className={styles.naoEncontrada}>
          <h1>Pergunta não encontrada</h1>
          <p>
            Ela pode ter sido excluída pelo autor ou o endereço está incompleto. As demais perguntas continuam
            no <Link href="/forum">fórum</Link>.
          </p>
        </section>
      ) : !topico ? (
        <p className={styles.erro} role="alert">
          {erro}{" "}
          <button type="button" className={styles.btnSecundario} onClick={() => carregar()}>
            Tentar novamente
          </button>
        </p>
      ) : (
        <article>
          {editando ? (
            <FormPergunta
              titulo={topico.titulo}
              conteudo={conteudoDe(topico)}
              onCancelar={() => setEditando(false)}
              onSalvar={editar}
            />
          ) : (
            <>
              <h1 className={styles.perguntaTitulo}>{topico.titulo}</h1>
              <MetaPergunta topico={topico} />
              <CorpoPergunta topico={topico} />
              <div className={styles.rodape}>
                <Votos topico={topico} user={user} votando={votando} onVotar={votar} />
                {ehAutor(topico, user) && <AcoesAutor onEditar={() => setEditando(true)} onExcluir={excluir} />}
              </div>
            </>
          )}

          {erro && (
            <p className={styles.erro} role="alert">
              {erro}
            </p>
          )}

          <div className={styles.secaoRespostas}>
            <Respostas topicoId={topico.id} estado={estadoRespostas} modo="pagina" onMudar={mudarRespostas} />
          </div>
        </article>
      )}
    </div>
  );
}
