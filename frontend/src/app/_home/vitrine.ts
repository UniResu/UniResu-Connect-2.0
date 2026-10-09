import { api } from "@/lib/api";
import type { Projeto } from "@/types/projeto";
import { conteudoDe, votosDe, type Topico } from "@/app/forum/_componentes/forum";

/** Quanto o servidor espera a API, que pode estar acordando no Render.
 *  A espera acontece no build ou em segundo plano, nunca na frente de alguém. */
const ESPERA_API_MS = 60_000;

/** Pergunta do fórum como a página inicial mostra: só o que cabe no card. */
export interface PerguntaVitrine {
  id: string;
  titulo: string;
  resumo: string;
  autor: string;
  respostas: number;
  votos: number;
}

export const ROTA_PROJETOS = "/api/projetos/buscar?page_size=3";
export const ROTA_PERGUNTAS = "/api/forum/topicos?limite=3";

/** O card compacto não mostra a descrição; ela só pesaria no HTML. */
export function resumirProjeto(projeto: Projeto): Projeto {
  return { ...projeto, descricao: undefined };
}

export function resumirPergunta(topico: Topico): PerguntaVitrine {
  const texto = conteudoDe(topico).replace(/\s+/g, " ").trim();
  return {
    id: topico.id,
    titulo: topico.titulo,
    resumo: texto.length > 180 ? `${texto.slice(0, 177).trimEnd()}...` : texto,
    autor: topico.autor_username || "usuario",
    respostas: topico.total_respostas ?? 0,
    votos: votosDe(topico),
  };
}

/**
 * Busca uma lista da API pelo servidor.
 *
 * No build, se a API não responder, devolve null e o navegador busca a lista
 * como antes. Fora do build (a renovação em segundo plano), lança o erro:
 * assim o Next continua servindo a última versão boa da página em vez de
 * trocá-la por uma sem conteúdo. Lista vazia conta como erro, porque a busca
 * de projetos devolve vazio quando o banco falha.
 */
async function buscarNoServidor<T>(rota: string, rotulo: string): Promise<T[] | null> {
  try {
    const dados = await api.get<T[]>(rota, { signal: AbortSignal.timeout(ESPERA_API_MS) });
    if (!Array.isArray(dados) || dados.length === 0) {
      throw new Error("a API não devolveu itens");
    }
    return dados;
  } catch (erro) {
    if (process.env.NEXT_PHASE === "phase-production-build") return null;
    const detalhe = erro instanceof Error ? erro.message : JSON.stringify(erro);
    throw new Error(`${rotulo}: ${detalhe}`);
  }
}

/** Os três projetos de exemplo da página inicial. */
export async function projetosDaVitrine(): Promise<Projeto[] | null> {
  const dados = await buscarNoServidor<Projeto>(ROTA_PROJETOS, "Vitrine de projetos");
  return dados && dados.map(resumirProjeto);
}

/** As três perguntas mais recentes do fórum. */
export async function perguntasDaVitrine(): Promise<PerguntaVitrine[] | null> {
  const dados = await buscarNoServidor<Topico>(ROTA_PERGUNTAS, "Perguntas do fórum");
  // slice: uma API anterior ao parâmetro `limite` devolve a lista inteira.
  return dados && dados.slice(0, 3).map(resumirPergunta);
}
