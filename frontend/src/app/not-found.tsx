import Image from "next/image";
import Link from "next/link";
import styles from "./not-found.module.css";

/**
 * Página 404, para endereços que não existem e para quem chama notFound().
 * O disco voador leva uma folha no feixe; o texto fica sóbrio e aponta
 * os dois caminhos mais comuns: a busca de projetos e a página inicial.
 */
export default function NaoEncontrada() {
  return (
    <section className={styles.pagina} aria-labelledby="titulo-404">
      <div className={styles.cena} aria-hidden="true">
        <Image src="/ufo.png" alt="" width={160} height={160} className={styles.nave} unoptimized priority />
        <span className={styles.feixe} />
        <svg className={styles.folha} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round">
          <path d="M14 3H7a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2V8z" />
          <path d="M14 3v5h5M9 13h6M9 17h4" />
        </svg>
      </div>

      <p className={styles.codigo}>Erro 404</p>
      <h1 id="titulo-404" className={styles.titulo}>
        Esta página foi abduzida
      </h1>
      <p className={styles.texto}>
        Não encontramos o endereço que você abriu. Ele pode ter mudado ou estar incorreto.
      </p>

      <div className={styles.acoes}>
        <Link href="/projetos" className="ui-btn ui-btn-primary ui-btn-lg">
          Buscar projetos
        </Link>
        <Link href="/" className="ui-btn ui-btn-secondary ui-btn-lg">
          Ir para o início
        </Link>
      </div>
    </section>
  );
}
