import { api } from "@/lib/api";

/** Quanto o servidor espera a API, que pode estar acordando no Render. A
 *  espera acontece no build ou na renovação em segundo plano das páginas em
 *  cache, quase nunca na frente de alguém. */
export const ESPERA_API_MS = 60_000;

/** Verdadeiro durante o `next build`. */
export function emBuild() {
  return process.env.NEXT_PHASE === "phase-production-build";
}

/**
 * Pede uma rota da API pelo servidor.
 *
 * No build, se a API não responder, devolve null e a página segue sem esse
 * dado. Fora do build (a renovação em segundo plano), lança o erro: assim o
 * Next continua servindo a última versão boa da página em vez de trocá-la
 * por uma sem conteúdo.
 */
export async function pedirNoServidor<T>(
  rota: string,
  rotulo: string,
  valido: (dados: T) => boolean
): Promise<T | null> {
  try {
    const dados = await api.get<T>(rota, { signal: AbortSignal.timeout(ESPERA_API_MS) });
    if (!valido(dados)) throw new Error("resposta vazia ou inesperada");
    return dados;
  } catch (erro) {
    if (emBuild()) return null;
    const detalhe = erro instanceof Error ? erro.message : JSON.stringify(erro);
    throw new Error(`${rotulo}: ${detalhe}`);
  }
}
