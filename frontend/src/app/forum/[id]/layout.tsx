import type { Metadata } from "next";
import { api } from "@/lib/api";
import { ESPERA_API_MS } from "@/lib/servidor";
import { conteudoDe, type Topico } from "../_componentes/forum";

/**
 * Título, descrição e prévia de link de cada pergunta. A página em si é
 * montada no navegador; os metadados saem do servidor, a partir da lista do
 * fórum (o GET de uma pergunta conta uma visualização, a lista não).
 */
export async function generateMetadata({ params }: { params: Promise<{ id: string }> }): Promise<Metadata> {
  const { id } = await params;
  let topico: Topico | undefined;
  try {
    const lista = await api.get<Topico[]>("/api/forum/topicos?limite=100", {
      signal: AbortSignal.timeout(ESPERA_API_MS),
      next: { revalidate: 3600 },
    });
    topico = lista.find((t) => t.id === id);
  } catch {
    // Sem a API, a pergunta fica com os metadados gerais do fórum.
  }
  if (!topico) return { title: "Pergunta do fórum" };
  const texto = conteudoDe(topico).replace(/\s+/g, " ").trim();
  const descricao = texto.length > 160 ? `${texto.slice(0, 157).trimEnd()}...` : texto;
  const endereco = `/forum/${topico.id}`;
  return {
    title: topico.titulo,
    description: descricao || undefined,
    alternates: { canonical: endereco },
    openGraph: { type: "article", title: topico.titulo, description: descricao || undefined, url: endereco },
  };
}

export default function LayoutPergunta({ children }: { children: React.ReactNode }) {
  return children;
}
