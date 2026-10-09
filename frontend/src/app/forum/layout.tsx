import type { Metadata } from "next";

export const metadata: Metadata = {
  // O modelo é repetido aqui: um título simples no layout faria as páginas
  // filhas perderem o "| UniResu Connect" do fim.
  title: { default: "Fórum", template: "%s | UniResu Connect" },
  description: "Perguntas e respostas sobre pesquisa, extensão e vida universitária.",
  alternates: { canonical: "/forum" },
};

export default function LayoutForum({ children }: { children: React.ReactNode }) {
  return children;
}
