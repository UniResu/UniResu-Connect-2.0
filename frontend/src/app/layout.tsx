import type { Metadata } from "next";
import { Plus_Jakarta_Sans } from "next/font/google";
import "./globals.css";
import { AuthProvider } from "@/contexts/AuthContext";
import Navbar from "@/components/layout/Navbar";

/**
 * Fonte do site (Plus Jakarta Sans, licença SIL OFL), servida pelo próprio
 * Next a partir do build, sem chamada ao Google no navegador. A versão
 * variável traz o eixo inteiro de pesos (200 a 800) em um único arquivo, o
 * que cobre os pesos 400 a 800 usados na interface. O nome da família fica
 * na variável CSS --font-base, que globals.css lê em --font-family.
 */
const fonteBase = Plus_Jakarta_Sans({
  subsets: ["latin", "latin-ext"],
  display: "swap",
  variable: "--font-base",
});

export const metadata: Metadata = {
  title: "UniResu Connect | Conectando a Comunidade Acadêmica",
  description:
    "Plataforma que conecta alunos, professores e pesquisadores em uma rede de oportunidades, conhecimento e colaboração universitária.",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="pt-BR" className={fonteBase.variable}>
      <body style={{ display: "flex", flexDirection: "column", minHeight: "100vh" }}>
        <AuthProvider>
          <Navbar />
          <main style={{ flex: 1 }}>{children}</main>
          <footer style={{
            textAlign: "center",
            padding: "2rem 1rem",
            color: "#9ca3af",
            fontSize: "0.875rem",
            borderTop: "1px solid rgba(255, 255, 255, 0.1)",
            background: "#0d0014", /* Dark space theme to blend with the bottom of previous sections */
            marginTop: "auto",
          }}>
            © 2026 UniResu Connect. Conectando a Comunidade Acadêmica.
          </footer>
        </AuthProvider>
      </body>
    </html>
  );
}
