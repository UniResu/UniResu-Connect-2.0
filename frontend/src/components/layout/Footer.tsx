import Image from "next/image";
import Link from "next/link";
import { IconeEnvelope, IconePlaneta } from "@/components/ui/Icones";
import { EMAIL_CONTATO } from "@/lib/constants";
import styles from "./Footer.module.css";

/** Rodapé escuro nos dois temas, no mesmo tom do cabeçalho. */
export default function Footer() {
  return (
    <footer className={styles.footer}>
      {/* O alienígena da marca espia por cima do rodapé: só a cabeça até os
          olhos aparece, o resto fica atrás da borda. */}
      <div className={styles.espiao} aria-hidden="true">
        <Image src="/uniresulogo.png" alt="" width={52} height={70} className={styles.espiaoImagem} unoptimized />
      </div>
      <div className={styles.conteudo}>
        <div className={styles.marca}>
          <span className={styles.nome}>
            <IconePlaneta tamanho={22} />
            UniResu Connect
          </span>
          <span className={styles.lema}>Conectando a comunidade acadêmica</span>
          <a href={`mailto:${EMAIL_CONTATO}`} className={styles.email}>
            <IconeEnvelope tamanho={16} />
            {EMAIL_CONTATO}
          </a>
        </div>
        <nav className={styles.links} aria-label="Rodapé">
          <Link href="/projetos">Projetos acadêmicos</Link>
          <Link href="/forum">Fórum</Link>
          <Link href="/#quem-somos">Quem somos</Link>
          <a href="https://uniresu.org" target="_blank" rel="noopener noreferrer">uniresu.org</a>
        </nav>
      </div>
      <p className={styles.copy}>© 2026 UniResu Connect</p>
    </footer>
  );
}
