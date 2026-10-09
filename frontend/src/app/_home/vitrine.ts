import { api } from "@/lib/api";
import type { Projeto } from "@/types/projeto";

/** Quanto o servidor espera a API, que pode estar acordando no Render.
 *  A espera acontece no build ou em segundo plano, nunca na frente de alguém. */
const ESPERA_API_MS = 60_000;

/**
 * Os três projetos de exemplo da página inicial, buscados pelo servidor.
 *
 * No build, se a API não responder, devolve null e o navegador busca os
 * projetos como antes. Fora do build (a renovação em segundo plano), lança o
 * erro: assim o Next continua servindo a última versão boa da página em vez
 * de trocá-la por uma sem projetos.
 */
export async function projetosDaVitrine(): Promise<Projeto[] | null> {
  try {
    const dados = await api.get<Projeto[]>("/api/projetos/buscar?page_size=3", {
      signal: AbortSignal.timeout(ESPERA_API_MS),
    });
    // A busca devolve lista vazia quando o banco falha; com milhares de
    // projetos na base, vazio aqui é sempre erro.
    if (!Array.isArray(dados) || dados.length === 0) {
      throw new Error("a busca não devolveu projetos");
    }
    // O card compacto não mostra a descrição; ela só pesaria no HTML.
    return dados.map((projeto) => ({ ...projeto, descricao: undefined }));
  } catch (erro) {
    if (process.env.NEXT_PHASE === "phase-production-build") return null;
    const detalhe = erro instanceof Error ? erro.message : JSON.stringify(erro);
    throw new Error(`Vitrine de projetos: ${detalhe}`);
  }
}
