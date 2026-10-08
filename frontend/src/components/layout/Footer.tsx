import Link from "next/link";
import styles from "./Footer.module.css";

/** Rodapé escuro nos dois temas, no mesmo tom do cabeçalho. */
export default function Footer() {
  return (
    <footer className={styles.footer}>
      <div className={styles.conteudo}>
        <div className={styles.marca}>
          <span className={styles.nome}>UniResu Connect</span>
          <span className={styles.lema}>Conectando a comunidade acadêmica</span>
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
