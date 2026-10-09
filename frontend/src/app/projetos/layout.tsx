import type { Metadata } from "next";

export const metadata: Metadata = {
  // O modelo é repetido aqui: um título simples no layout faria as páginas
  // filhas perderem o "| UniResu Connect" do fim.
  title: { default: "Projetos acadêmicos", template: "%s | UniResu Connect" },
  description:
    "Projetos de pesquisa e extensão das universidades, em um só lugar. Encontre o seu e envie uma carta de intenção à coordenação.",
  alternates: { canonical: "/projetos" },
};

export default function LayoutProjetos({ children }: { children: React.ReactNode }) {
  return children;
}
