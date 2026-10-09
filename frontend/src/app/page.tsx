import HomeConteudo from "./_home/HomeConteudo";
import { numerosDaBase, perguntasDaVitrine, projetosDaVitrine } from "./_home/vitrine";

// A página inicial sai pronta do servidor, já com os números da base, os
// projetos de exemplo e as perguntas recentes do fórum no HTML, e é refeita
// em segundo plano no máximo uma vez por hora. Quem abre o site não espera a
// API acordar.
export const revalidate = 3600;

export default async function HomePage() {
  const [projetos, perguntas, numeros] = await Promise.all([
    projetosDaVitrine(),
    perguntasDaVitrine(),
    numerosDaBase(),
  ]);
  return <HomeConteudo projetosIniciais={projetos} perguntasIniciais={perguntas} numeros={numeros} />;
}
