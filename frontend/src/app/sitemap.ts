import type { MetadataRoute } from "next";
import { SITE_URL } from "@/lib/constants";
import { pedirNoServidor } from "@/lib/servidor";
import type { Topico } from "@/app/forum/_componentes/forum";

/**
 * Sitemap do site (/sitemap.xml): as páginas principais, a página de cada
 * projeto visível e cada pergunta do fórum. Refeito a cada hora (o do build
 * pode sair só com as páginas fixas, se a API ainda não respondeu); se a API
 * falhar na renovação, o Next mantém o último sitemap bom.
 */

export const revalidate = 3600;

/** Projetos por pedido à API (a lista inteira passa de 20 mil). */
const POR_PAGINA = 5000;

interface IndiceProjetos {
  total: number;
  itens: { id: string; atualizado_em?: string | null }[];
}

async function todosOsProjetos() {
  const itens: IndiceProjetos["itens"] = [];
  for (let pular = 0; ; pular += POR_PAGINA) {
    const pagina = await pedirNoServidor<IndiceProjetos>(
      `/api/projetos/indice?pular=${pular}&limite=${POR_PAGINA}`,
      "Índice de projetos",
      (dados) => Array.isArray(dados?.itens)
    );
    if (!pagina) break;
    itens.push(...pagina.itens);
    if (pagina.itens.length < POR_PAGINA || itens.length >= pagina.total) break;
  }
  return itens;
}

async function perguntasDoForum() {
  const lista = await pedirNoServidor<Topico[]>("/api/forum/topicos?limite=100", "Perguntas do fórum", Array.isArray);
  return lista ?? [];
}

export default async function sitemap(): Promise<MetadataRoute.Sitemap> {
  const [projetos, perguntas] = await Promise.all([todosOsProjetos(), perguntasDoForum()]);
  return [
    { url: `${SITE_URL}/`, changeFrequency: "daily", priority: 1 },
    { url: `${SITE_URL}/projetos`, changeFrequency: "daily", priority: 0.9 },
    { url: `${SITE_URL}/forum`, changeFrequency: "daily", priority: 0.7 },
    ...projetos.map((p) => ({
      url: `${SITE_URL}/projetos/${p.id}`,
      lastModified: p.atualizado_em ? new Date(p.atualizado_em) : undefined,
      changeFrequency: "weekly" as const,
      priority: 0.8,
    })),
    ...perguntas.map((t) => ({
      url: `${SITE_URL}/forum/${t.id}`,
      lastModified: t.data_criacao ? new Date(t.data_criacao) : undefined,
      changeFrequency: "weekly" as const,
      priority: 0.6,
    })),
  ];
}
