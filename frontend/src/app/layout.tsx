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
            © 2026 UniResu Connect — Conectando a Comunidade Acadêmica
          </footer>
        </AuthProvider>
      </body>
    </html>
  );
}
