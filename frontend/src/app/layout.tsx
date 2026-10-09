import type { Metadata, Viewport } from "next";
import { Plus_Jakarta_Sans } from "next/font/google";
import "./globals.css";
import { AuthProvider } from "@/contexts/AuthContext";
import Navbar from "@/components/layout/Navbar";
import Footer from "@/components/layout/Footer";
import { SITE_URL } from "@/lib/constants";
import { COR_TEMA, SCRIPT_TEMA } from "@/lib/tema";

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

const DESCRICAO_SITE =
  "Plataforma que conecta alunos, professores e pesquisadores em uma rede de oportunidades, conhecimento e colaboração universitária.";

// metadataBase: os links canônicos e das prévias (Open Graph) das páginas
// saem com o endereço completo do site. O modelo de título vale para as
// páginas que definem o próprio título ("Fórum | UniResu Connect").
export const metadata: Metadata = {
  metadataBase: new URL(SITE_URL),
  title: {
    default: "UniResu Connect | Conectando a Comunidade Acadêmica",
    template: "%s | UniResu Connect",
  },
  description: DESCRICAO_SITE,
  openGraph: {
    type: "website",
    siteName: "UniResu Connect",
    locale: "pt_BR",
    title: "UniResu Connect | Conectando a Comunidade Acadêmica",
    description: DESCRICAO_SITE,
  },
};

// Uma única meta theme-color: o script do tema troca o valor junto com o
// atributo data-theme, para a barra do navegador acompanhar a escolha salva.
export const viewport: Viewport = {
  themeColor: COR_TEMA.light,
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
