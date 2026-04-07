import type { Metadata } from "next";
import "./globals.css";
import { AuthProvider } from "@/contexts/AuthContext";
import Navbar from "@/components/layout/Navbar";

export const metadata: Metadata = {
  title: "UniResu Connect — Conectando a Comunidade Acadêmica",
  description:
    "Plataforma que conecta alunos, professores e pesquisadores em uma rede de oportunidades, conhecimento e colaboração universitária.",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="pt-BR">
      <body>
        <AuthProvider>
          <Navbar />
          <main>{children}</main>
          <footer style={{
            textAlign: "center",
            padding: "2rem 1rem",
            color: "var(--text-muted)",
            fontSize: "var(--font-size-sm)",
            borderTop: "1px solid var(--border-light)",
            marginTop: "4rem",
          }}>
            © 2026 UniResu Connect — Conectando a Comunidade Acadêmica
          </footer>
        </AuthProvider>
      </body>
    </html>
  );
}
