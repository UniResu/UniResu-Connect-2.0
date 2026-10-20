import { pedirNoServidor } from "@/lib/servidor";
import type { Projeto } from "@/types/projeto";
import BuscaProjetos from "./_componentes/BuscaProjetos";
import { PARAMS_PRIMEIRA_PAGINA } from "./_componentes/busca";

// A primeira página da busca sai pronta do servidor e é refeita em segundo
// plano no máximo uma vez por hora, como a página inicial: quem abre a busca
// vê os projetos na hora, mesmo com a API acordando no Render. Os filtros, a
// busca por texto e o "Carregar mais" continuam pedindo à API pelo navegador.
export const revalidate = 3600;

export default async function ProjetosPage() {
  // Lista vazia conta como erro: a busca devolve vazio quando o banco falha.
  const projetos = await pedirNoServidor<Projeto[]>(
    `/api/projetos/buscar?${PARAMS_PRIMEIRA_PAGINA}`,
    "Primeira página da busca",
    (dados) => Array.isArray(dados) && dados.length > 0
  );
  return <BuscaProjetos projetosIniciais={projetos} />;
}
