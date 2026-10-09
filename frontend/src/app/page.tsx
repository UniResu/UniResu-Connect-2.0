import HomeConteudo from "./_home/HomeConteudo";
import { projetosDaVitrine } from "./_home/vitrine";

// A página inicial sai pronta do servidor, já com os projetos de exemplo no
// HTML, e é refeita em segundo plano no máximo uma vez por hora. Quem abre o
// site não espera a API acordar; os projetos mudam só no sync semanal.
export const revalidate = 3600;

export default async function HomePage() {
  const projetos = await projetosDaVitrine();
  return <HomeConteudo projetosIniciais={projetos} />;
}
