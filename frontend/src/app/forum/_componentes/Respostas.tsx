"use client";

/**
 * Respostas de uma pergunta, com um único nível (não há resposta de resposta).
 *
 * Dois modos:
 *  - "thread" (pergunta aberta em /forum): mostra no máximo 10 respostas e,
 *    se houver mais, o link "Ver todas as N respostas" para /forum/[id];
 *    o formulário abre pelo botão "Responder".
 *  - "pagina" (/forum/[id]): mostra todas as respostas carregadas, com o botão
 *    "Carregar mais respostas" em blocos de 50, e o formulário já aberto.
 *
 * O estado (respostas carregadas e total) fica com o componente pai, que o
 * recebe em `estado` e o atualiza por `onMudar`: assim o contador da linha de
 * meta acompanha o que acontece aqui.
 *
 * Só quem está logado com o perfil completo responde (a API devolve 403 nos
 * outros casos). Visitantes veem o convite para entrar; quem ainda não
 * completou o perfil vê o link para /perfil/completar. Se a API recusar
 * mesmo assim (sessão expirada ou perfil que ficou incompleto), a mensagem
 * de erro traz o link para resolver.
 */

import { useId, useState } from "react";
import Link from "next/link";
import { api } from "@/lib/api";
import { useAuth } from "@/contexts/AuthContext";
import {
  RESPOSTA_MAX_CARACTERES,
  RESPOSTAS_NA_THREAD,
  RESPOSTAS_POR_PAGINA,
  dataCompleta,
  ehAutor,
  inicialDe,
  juntarRespostas,
  mensagemDeErro,
  plural,
  statusDoErro,
  tempoRelativo,
  type EstadoRespostas,
  type PaginaRespostas,
  type Resposta,
} from "./forum";
import { AcoesAutor } from "./Pergunta";
import { IconeNaveTransmite } from "@/components/ui/Icones";
import styles from "../forum.module.css";

/** Erro mostrado na seção; `acao` acrescenta o link que resolve o problema. */
interface ErroAcao {
  mensagem: string;
  acao?: "entrar" | "completar";
}

/**
 * 401: o token venceu, então a pessoa precisa entrar de novo. 403 ao
 * publicar só acontece com perfil incompleto (editar e excluir também dão
 * 403 quando a resposta é de outra pessoa, por isso `podeSerPerfil`).
 */
function erroDaApi(err: unknown, padrao: string, podeSerPerfil = false): ErroAcao {
  const status = statusDoErro(err);
  if (status === 401) return { mensagem: "Sua sessão expirou.", acao: "entrar" };
  if (status === 403 && podeSerPerfil) return { mensagem: mensagemDeErro(err, padrao), acao: "completar" };
  return { mensagem: mensagemDeErro(err, padrao) };
}

// ── Uma resposta ──────────────────────────────────────────────────────────

interface ItemRespostaProps {
  resposta: Resposta;
  autor: boolean;
  onEditar: (resposta: Resposta, conteudo: string) => Promise<void>;
  onExcluir: (resposta: Resposta) => void;
}

function ItemResposta({ resposta, autor, onEditar, onExcluir }: ItemRespostaProps) {
  const idCampo = useId();
  const [editando, setEditando] = useState(false);
  const [texto, setTexto] = useState(resposta.conteudo);
  const [salvando, setSalvando] = useState(false);

  function iniciarEdicao() {
    setTexto(resposta.conteudo);
    setEditando(true);
  }

  async function salvar(e: React.FormEvent) {
    e.preventDefault();
    if (!texto.trim()) return;
    setSalvando(true);
    try {
      await onEditar(resposta, texto.trim());
      setEditando(false);
    } catch {
      // A seção já mostrou o erro; o formulário fica aberto para nova tentativa.
    } finally {
      setSalvando(false);
    }
  }

  return (
    <li className={styles.resposta}>
      {/* [R5] Avatar com a inicial e o @username; o e-mail nunca aparece. */}
      <span className={styles.avatar} aria-hidden="true">
        {inicialDe(resposta.autor_nome, resposta.autor_username)}
      </span>

      <div className={styles.respostaCabecalho}>
        <div className={`${styles.meta} ${styles.respostaMeta}`}>
          <span className={`${styles.metaItem} ${styles.respostaAutor}`} title={resposta.autor_nome || undefined}>
            @{resposta.autor_username || "usuario"}
          </span>
          <span className={styles.metaItem} title={dataCompleta(resposta.data_criacao)}>
            {tempoRelativo(resposta.data_criacao)}
          </span>
          {resposta.editado_em && (
            <span className={styles.metaItem} title={`Editada em ${dataCompleta(resposta.editado_em)}`}>
              editada
            </span>
          )}
        </div>
        {autor && !editando && <AcoesAutor onEditar={iniciarEdicao} onExcluir={() => onExcluir(resposta)} />}
      </div>

      {editando ? (
        <form className={styles.formEdicao} onSubmit={salvar}>
          <label htmlFor={idCampo} className="sr-only">
            Texto da resposta
          </label>
          <textarea
            id={idCampo}
            value={texto}
            onChange={(e) => setTexto(e.target.value)}
            className="ui-field"
            rows={4}
            maxLength={RESPOSTA_MAX_CARACTERES}
            required
          />
          <div className={styles.formAcoes}>
            <button type="button" className="ui-btn ui-btn-ghost ui-btn-sm" onClick={() => setEditando(false)}>
              Cancelar
            </button>
            <button type="submit" className="ui-btn ui-btn-primary ui-btn-sm" disabled={salvando || !texto.trim()}>
              {salvando ? "Salvando..." : "Salvar"}
            </button>
          </div>
        </form>
      ) : (
        <div className={styles.respostaTexto}>{resposta.conteudo}</div>
      )}
    </li>
  );
}

// ── Seção de respostas ────────────────────────────────────────────────────

interface RespostasProps {
  topicoId: string;
  /** null enquanto as respostas ainda não chegaram. */
  estado: EstadoRespostas | null;
  modo: "thread" | "pagina";
  onMudar: (atualizar: (atual: EstadoRespostas) => EstadoRespostas) => void;
  /** O carregamento inicial falhou: mostra o aviso e, se houver, o botão de nova tentativa. */
  falhou?: boolean;
  onRecarregar?: () => void;
}

export function Respostas({ topicoId, estado, modo, onMudar, falhou, onRecarregar }: RespostasProps) {
  const { token, user, isAuthenticated, isLoading } = useAuth();
  const idCampo = useId();

  const [formAberto, setFormAberto] = useState(modo === "pagina");
  const [texto, setTexto] = useState("");
  const [enviando, setEnviando] = useState(false);
  const [carregandoMais, setCarregandoMais] = useState(false);
  const [erro, setErro] = useState<ErroAcao | null>(null);
  // A resposta nova ficou depois das que estão na tela (thread cheia ou lista ainda incompleta).
  const [publicadaForaDaTela, setPublicadaForaDaTela] = useState(false);

  const respostas = estado?.respostas ?? [];
  const total = estado?.total ?? 0;
  const limite = modo === "thread" ? RESPOSTAS_NA_THREAD : Infinity;
  const visiveis = respostas.slice(0, limite);
  const urlRespostas = `/api/forum/topicos/${topicoId}/respostas`;
  const perfilIncompleto = user?.perfil_completo === false;
  // Na lista o título da pergunta é <h2>; na página da pergunta, <h1>.
  const Titulo = modo === "thread" ? "h3" : "h2";

  async function publicar(e: React.FormEvent) {
    e.preventDefault();
    const conteudo = texto.trim();
    if (!isAuthenticated || perfilIncompleto || !estado || !conteudo) return;
    // Só entra na tela se todas as respostas já estão nela e ainda cabe uma:
    // a nova é a mais recente, então vai para o fim da lista.
    const entraNaTela = respostas.length >= total && respostas.length < limite;
    setEnviando(true);
    try {
      const nova = await api.post<Resposta>(urlRespostas, { conteudo }, { token: token || undefined });
      onMudar((atual) => ({
        respostas: entraNaTela ? juntarRespostas(atual.respostas, [nova]) : atual.respostas,
        total: atual.total + 1,
      }));
      setTexto("");
      setErro(null);
      setPublicadaForaDaTela(!entraNaTela);
      if (modo === "thread") setFormAberto(false);
    } catch (err) {
      setErro(erroDaApi(err, "Não foi possível publicar a resposta.", true));
    } finally {
      setEnviando(false);
    }
  }

  async function editar(resposta: Resposta, conteudo: string) {
    try {
      const atualizada = await api.patch<Resposta>(
        `/api/forum/respostas/${resposta.id}`,
        { conteudo },
        { token: token || undefined }
      );
      onMudar((atual) => ({
        ...atual,
        respostas: atual.respostas.map((r) => (r.id === atualizada.id ? atualizada : r)),
      }));
      setErro(null);
    } catch (err) {
      setErro(erroDaApi(err, "Não foi possível salvar a edição."));
      throw err; // o item mantém o formulário aberto
    }
  }

  async function excluir(resposta: Resposta) {
    if (!confirm("Excluir esta resposta? Esta ação não pode ser desfeita.")) return;
    // Na thread, se havia respostas além das 10 da tela, a 11ª sobe para o lugar.
    const haviaOcultas = modo === "thread" && total > visiveis.length;
    try {
      await api.delete(`/api/forum/respostas/${resposta.id}`, { token: token || undefined });
      onMudar((atual) => ({
        respostas: atual.respostas.filter((r) => r.id !== resposta.id),
        total: Math.max(0, atual.total - 1),
      }));
      setErro(null);
      if (haviaOcultas) {
        const pagina = await api.get<PaginaRespostas>(`${urlRespostas}?limite=${RESPOSTAS_NA_THREAD}`);
        onMudar(() => ({ respostas: pagina.respostas, total: pagina.total }));
      }
    } catch (err) {
      setErro(erroDaApi(err, "Não foi possível excluir a resposta."));
    }
  }

  async function carregarMais() {
    if (!estado || carregandoMais) return;
    setCarregandoMais(true);
    try {
      const pagina = await api.get<PaginaRespostas>(
        `${urlRespostas}?limite=${RESPOSTAS_POR_PAGINA}&pular=${respostas.length}`
      );
      onMudar((atual) => ({
        respostas: juntarRespostas(atual.respostas, pagina.respostas),
        total: pagina.total,
      }));
      setErro(null);
      setPublicadaForaDaTela(false);
    } catch (err) {
      setErro({ mensagem: mensagemDeErro(err, "Não foi possível carregar mais respostas.") });
    } finally {
      setCarregandoMais(false);
    }
  }

  return (
    <section className={styles.respostas} aria-label="Respostas">
      {estado === null ? (
        falhou ? (
          <p className={styles.erro} role="alert">
            Não foi possível carregar as respostas.{" "}
            {onRecarregar && (
              <button type="button" className="ui-btn ui-btn-secondary ui-btn-sm" onClick={onRecarregar}>
                Tentar novamente
              </button>
            )}
          </p>
        ) : (
          <p className={styles.respostasAviso} aria-busy="true">
            Carregando respostas...
          </p>
        )
      ) : (
        <>
          {total > 0 && (
            <Titulo className={styles.respostasTitulo}>
              <IconeNaveTransmite tamanho={18} />
              {plural(total, "resposta", "respostas")}
            </Titulo>
          )}

          {visiveis.length > 0 && (
            <ol className={styles.listaRespostas}>
              {visiveis.map((r) => (
                <ItemResposta
                  key={r.id}
                  resposta={r}
                  autor={ehAutor(r, user)}
                  onEditar={editar}
                  onExcluir={excluir}
                />
              ))}
            </ol>
          )}

          {modo === "thread" && total > RESPOSTAS_NA_THREAD && (
            <div className={styles.respostasRodape}>
              <Link href={`/forum/${topicoId}`} className="ui-btn ui-btn-ghost ui-btn-sm">
                Ver todas as {total} respostas
              </Link>
            </div>
          )}

          {modo === "pagina" && respostas.length < total && (
            <div className={styles.respostasRodape}>
              <button
                type="button"
                className="ui-btn ui-btn-secondary"
                onClick={carregarMais}
                disabled={carregandoMais}
              >
                {carregandoMais ? "Carregando..." : "Carregar mais respostas"}
              </button>
            </div>
          )}
        </>
      )}

      {erro && (
        <p className={styles.erro} role="alert">
          {erro.mensagem}
          {erro.acao === "entrar" && (
            <>
              {" "}
              <Link href="/login">Entre de novo</Link> para continuar.
            </>
          )}
          {erro.acao === "completar" && (
            <>
              {" "}
              <Link href="/perfil/completar">Completar o perfil</Link>
            </>
          )}
        </p>
      )}

      {publicadaForaDaTela && (
        <p className={styles.aviso} role="status">
          {modo === "thread" ? (
            <>
              Sua resposta foi publicada no fim da lista. Para vê-la,{" "}
              <Link href={`/forum/${topicoId}`}>abra a página da pergunta</Link>.
            </>
          ) : (
            "Sua resposta foi publicada no fim da lista. Carregue as respostas restantes para vê-la."
          )}
        </p>
      )}

      {/* Enquanto a sessão carrega, não mostra nem o convite nem o formulário. */}
      {estado !== null && !isLoading && (
        !isAuthenticated ? (
          <p className={`${styles.dicaLogin} ${styles.respostasRodape}`}>
            <Link href="/login">Entre</Link> para responder.
          </p>
        ) : perfilIncompleto ? (
          // A API devolveria 403: em vez de deixar tentar, aponta o caminho.
          <p className={`${styles.dicaLogin} ${styles.respostasRodape}`}>
            Para responder, <Link href="/perfil/completar">complete seu perfil</Link> com o vínculo
            institucional, o e-mail e os aceites.
          </p>
        ) : formAberto ? (
          <form className={`ui-card ${styles.formCard} ${styles.formResposta}`} onSubmit={publicar}>
            <div>
              <label htmlFor={idCampo} className="ui-label">
                Sua resposta
              </label>
              <textarea
                id={idCampo}
                value={texto}
                onChange={(e) => setTexto(e.target.value)}
                placeholder="Escreva sua resposta. Separe parágrafos com uma linha em branco."
                className="ui-field"
                rows={4}
                maxLength={RESPOSTA_MAX_CARACTERES}
                required
                autoFocus={modo === "thread"}
              />
            </div>
            <div className={styles.formAcoes}>
              <span className={styles.dicaForm}>Publicada como @{user?.username || "você"}.</span>
              {modo === "thread" && (
                <button type="button" className="ui-btn ui-btn-ghost" onClick={() => setFormAberto(false)}>
                  Cancelar
                </button>
              )}
              <button type="submit" className="ui-btn ui-btn-primary" disabled={enviando || !texto.trim()}>
                {enviando ? "Publicando..." : "Publicar resposta"}
              </button>
            </div>
          </form>
        ) : (
          <div className={styles.respostasRodape}>
            <button type="button" className="ui-btn ui-btn-secondary ui-btn-sm" onClick={() => setFormAberto(true)}>
              Responder
            </button>
          </div>
        )
      )}
    </section>
  );
}
