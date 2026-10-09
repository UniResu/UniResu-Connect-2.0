import { cache } from "react";
import type { Metadata } from "next";
import Link from "next/link";
import { notFound } from "next/navigation";
import { api } from "@/lib/api";
import { APP_NAME, SITE_URL } from "@/lib/constants";
import { ESPERA_API_MS } from "@/lib/servidor";
import { moduloDoProjeto, type Projeto } from "@/types/projeto";
import { IconeSetaEsquerda } from "@/components/ui/Icones";
import { DetalheProjeto } from "../_componentes/DetalheProjeto";
import styles from "../projetos.module.css";
import local from "./projeto.module.css";

/**
 * Página própria de cada projeto: o mesmo conteúdo do modal da busca, num
 * endereço que os buscadores indexam e que mostra o nome do projeto na
 * prévia de link (WhatsApp, redes). Gerada na primeira visita e guardada em
 * cache por um dia: o Google não depende de a API estar acordada.
 */

export const revalidate = 86400;

/** Nenhuma página no build; cada uma é gerada na primeira visita. */
export function generateStaticParams() {
  return [];
}

const carregarProjeto = cache(async (id: string): Promise<Projeto | null> => {
  if (!/^[a-f0-9]{24}$/i.test(id)) return null;
  try {
    return await api.get<Projeto>(`/api/projetos/${id}`, {
      signal: AbortSignal.timeout(ESPERA_API_MS),
      next: { revalidate },
    });
  } catch (erro) {
    if ((erro as { status?: number }).status === 404) return null;
    // Outra falha (API dormindo, rede): lança, e o Next mantém a última
    // versão boa da página em vez de responder "não encontrado".
    throw erro;
  }
});

/** "Projeto de pesquisa, UNIR", acima do título. */
function rotuloDeOrigem(p: Projeto) {
  const modulo = moduloDoProjeto(p);
  const tipo = modulo === "pesquisa" ? "Projeto de pesquisa" : modulo === "extensao" ? "Projeto de extensão" : "Projeto";
  return p.instituicao ? `${tipo}, ${p.instituicao}` : tipo;
}

/** Descrição curta para buscadores e prévias: o começo do resumo ou, sem
 *  ele, a origem e a coordenação. */
function descricaoCurta(p: Projeto) {
  const texto = (p.descricao || "").replace(/\s+/g, " ").trim();
  if (texto) return texto.length > 160 ? `${texto.slice(0, 157).trimEnd()}...` : texto;
  const partes = [`${rotuloDeOrigem(p)}.`];
  if (p.unidade) partes.push(`${p.unidade}.`);
  if (p.nome_professor) partes.push(`Coordenação: ${p.nome_professor}.`);
  return partes.join(" ");
}

/** Dados estruturados (schema.org) para os buscadores. */
function dadosEstruturados(p: Projeto) {
  const dados: Record<string, unknown> = {
    "@context": "https://schema.org",
    "@type": moduloDoProjeto(p) === "pesquisa" ? "ResearchProject" : "Project",
    name: p.titulo,
    description: (p.descricao || descricaoCurta(p)).slice(0, 1000),
    url: `${SITE_URL}/projetos/${p.id}`,
  };
  if (p.link_detalhe) dados.sameAs = p.link_detalhe;
  if (p.instituicao) dados.parentOrganization = { "@type": "CollegeOrUniversity", name: p.instituicao };
  if (p.nome_professor) dados.member = { "@type": "Person", name: p.nome_professor };
  if (p.area_conhecimento) dados.knowsAbout = p.area_conhecimento;
  if (p.palavras_chave && p.palavras_chave.length > 0) dados.keywords = p.palavras_chave.join(", ");
  // "<" escapado: o texto vem das universidades e vai dentro de um <script>.
  return JSON.stringify(dados).replace(/</g, "\\u003c");
}

export async function generateMetadata({ params }: { params: Promise<{ id: string }> }): Promise<Metadata> {
  const { id } = await params;
  const p = await carregarProjeto(id);
  if (!p) return { title: "Projeto não encontrado" };
  const descricao = descricaoCurta(p);
  const endereco = `/projetos/${p.id}`;
  return {
    title: p.titulo,
    description: descricao,
    alternates: { canonical: endereco },
    openGraph: {
      type: "article",
      title: p.titulo,
      description: descricao,
      url: endereco,
      siteName: APP_NAME,
      locale: "pt_BR",
    },
  };
}

export default async function PaginaProjeto({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  const p = await carregarProjeto(id);
  if (!p) notFound();

  return (
    <div className={styles.pagina}>
      <div className={`${styles.container} ${local.container}`}>
        <Link href="/projetos" className={`ui-btn ui-btn-ghost ui-btn-sm ${local.voltar}`}>
          <IconeSetaEsquerda tamanho={16} />
          Todos os projetos
        </Link>
        <header className={local.cabecalho}>
          <p className={local.origem}>{rotuloDeOrigem(p)}</p>
          <h1 className={local.titulo}>{p.titulo}</h1>
        </header>
        <DetalheProjeto projeto={p} naPagina />
      </div>
      <script type="application/ld+json" dangerouslySetInnerHTML={{ __html: dadosEstruturados(p) }} />
    </div>
  );
}
