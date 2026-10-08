import type { Metadata, Viewport } from "next";
import { Plus_Jakarta_Sans } from "next/font/google";
import "./globals.css";
import { AuthProvider } from "@/contexts/AuthContext";
import Navbar from "@/components/layout/Navbar";
import Footer from "@/components/layout/Footer";
import { SCRIPT_TEMA } from "@/lib/tema";

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

export const viewport: Viewport = {
  themeColor: [
    { media: "(prefers-color-scheme: light)", color: "#f6f5fa" },
    { media: "(prefers-color-scheme: dark)", color: "#0f0b18" },
  ],
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    // suppressHydrationWarning: o script abaixo define data-theme antes de o
    // React hidratar, e o atributo não existe no HTML gerado pelo servidor.
    <html lang="pt-BR" className={fonteBase.variable} suppressHydrationWarning>
      <body style={{ display: "flex", flexDirection: "column", minHeight: "100vh" }}>
        <script dangerouslySetInnerHTML={{ __html: SCRIPT_TEMA }} />
        <AuthProvider>
          <Navbar />
          <main style={{ flex: 1, display: "flex", flexDirection: "column" }}>{children}</main>
          <Footer />
        </AuthProvider>
      </body>
    </html>
  );
}
