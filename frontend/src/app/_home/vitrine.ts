import { pedirNoServidor } from "@/lib/servidor";
import type { Projeto } from "@/types/projeto";
import { conteudoDe, votosDe, type Topico } from "@/app/forum/_componentes/forum";

/** Pergunta do fórum como a página inicial mostra: só o que cabe no card. */
export interface PerguntaVitrine {
  id: string;
  titulo: string;
  resumo: string;
  autor: string;
  respostas: number;
  votos: number;
  categoria: string | null;
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
    categoria: topico.categoria ?? null,
  };
}

/** Lista vazia conta como erro: a busca de projetos devolve vazio quando o banco falha. */
function buscarNoServidor<T>(rota: string, rotulo: string): Promise<T[] | null> {
  return pedirNoServidor<T[]>(rota, rotulo, (dados) => Array.isArray(dados) && dados.length > 0);
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

interface FiltrosResposta {
  instituicoes?: { externa: boolean; total: number }[];
}

/** "20.258 projetos em andamento em 46 instituições", calculado das opções de
 *  filtro da busca. Formatado aqui para o HTML do servidor e o do navegador
 *  serem iguais. */
export async function numerosDaBase(): Promise<string | null> {
  const dados = await pedirNoServidor<FiltrosResposta>(
    "/api/projetos/filtros",
    "Números da base",
    (d) => Array.isArray(d?.instituicoes) && d.instituicoes.length > 0
  );
  if (!dados?.instituicoes) return null;
  const projetos = dados.instituicoes.reduce((soma, i) => soma + (i.total || 0), 0);
  const instituicoes = dados.instituicoes.filter((i) => i.externa && i.total > 0).length;
  if (projetos === 0) return null;
  const n = new Intl.NumberFormat("pt-BR");
  const deInstituicoes =
    instituicoes > 1 ? ` em ${n.format(instituicoes)} instituições` : instituicoes === 1 ? " em 1 instituição" : "";
  return `${n.format(projetos)} projetos em andamento${deInstituicoes}`;
}
