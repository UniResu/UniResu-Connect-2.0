import styles from "./page.module.css";
import Link from "next/link";

export default function HomePage() {
  return (
    <div className={styles.page}>
      {/* ── Hero Section ── */}
      <section className={styles.hero} id="home">
        <div className={styles.heroContent}>
          <h1 className={styles.heroTitle}>UniResu <span className={styles.highlightConnect}>Connect</span></h1>
          <h2 className={styles.heroSubtitle}>Conectando a Comunidade Acadêmica</h2>
          <p className={styles.heroDescription}>
            Uma plataforma que une alunos, professores e pesquisadores em uma rede de oportunidades, conhecimento e colaboração!
          </p>
          <div className={styles.heroCta}>
            <Link href="/login" className={styles.btnPrimary}>Login</Link>
          </div>
        </div>
      </section>

      {/* ── Quem Somos ── */}
      <section className={styles.quemSomosSection} id="quem-somos">
        <h2 className={styles.sectionTitle}>Quem Somos</h2>
        <div className={styles.cardsContainer}>
          <div className={styles.card}>
            <h3>Quem Somos</h3>
            <p>Somos estudantes, docentes e colaboradores que acreditam na autonomia, na colaboração e na circulação aberta do saber, buscando formas práticas de integrar essas ideias à vida universitária.</p>
          </div>
          <div className={styles.card}>
            <h3>Objetivos</h3>
            <p>Conectar pessoas, ideias e produções acadêmicas de forma acessível, organizada e contínua, promovendo uma cultura de colaboração e protagonismo universitário.</p>
          </div>
          <div className={styles.card}>
            <h3>O que promovemos</h3>
            <ul>
              <li>Espaços de discussão por áreas temáticas e interesses acadêmicos;</li>
              <li>Publicações de eventos, chamadas e oportunidades;</li>
              <li>Organização de projetos, produções e atividades da comunidade;</li>
              <li>Abertura para contribuições — desde sugestões até desenvolvimento técnico e editorial.</li>
            </ul>
          </div>
        </div>
      </section>

      {/* ── Projetos ── */}
      <section className={styles.projetosSection} id="projetos">
        <h2 className={styles.sectionTitle}>Projetos Acadêmicos</h2>
        <p className={styles.sectionSubtitle}>Descubra, contribua e candidate-se.</p>
        <div className={styles.cardsContainerCol}>
          <div className={styles.projetoCard}>
            <div className={styles.projetoInfo}>
              <h3>Diagnóstico e Tratamento de sepse por bacilos Gram-negativos em Centros de Tratamento Intensivo do Rio de Janeiro</h3>
              <p>Diagnóstico e Tratamento de sepse por bacilos Gram-negativos em Centros de Tratamento Intensivo do Rio de Janeiro</p>
            </div>
            <div className={styles.projetoDetalhes}>
              <span>UERJ</span>
              <span className={styles.tipo}>Projeto Institucional <strong>(Exclusivo)</strong></span>
              <span>Publicado 3 semanas atrás</span>
            </div>
          </div>
          <div className={styles.projetoCard}>
            <div className={styles.projetoInfo}>
              <h3>Aplicação do programa R para estudos epidemiológicos: capacitação para alunos de graduação e pós-graduação em saúde</h3>
              <p>Aplicação do programa R para estudos epidemiológicos: capacitação para alunos de graduação e pós-graduação em saúde</p>
            </div>
            <div className={styles.projetoDetalhes}>
              <span>Belém, Pará</span>
              <span className={styles.tipo}>Projeto Institucional <strong>(Exclusivo)</strong></span>
              <span>Publicado 2 meses atrás</span>
            </div>
          </div>
          <div className={styles.projetoCard}>
            <div className={styles.projetoInfo}>
              <h3>[PROJETO FICTÍCIO] Cytogen: Rede Colaborativa em Bioinformática Aplicada à Oncologia</h3>
              <p>Departamento de genética (UFMG)</p>
            </div>
            <div className={styles.projetoDetalhes}>
              <span>Universidade Federal de Minas Gerais (UFMG) <em>(Remoto)</em></span>
              <span className={styles.tipo}>Projeto Institucional <strong>(Aberto)</strong></span>
              <span>Publicado 2 meses atrás</span>
            </div>
          </div>
        </div>
        <Link href="/projetos" className={styles.btnSecondary}>Explorar Projetos</Link>
      </section>

      {/* ── Fórum ── */}
      <section className={styles.forumSection} id="forum">
        <h2 className={styles.sectionTitle}>Forum</h2>
        <div className={styles.cardsContainer}>
          <div className={styles.card}>
            <h3>Conecte-se com a Comunidade</h3>
            <p>Fique por dentro das novidades! Visualize Artigos, Eventos, Seminários e muito mais!</p>
            <Link href="/forum" className={styles.linkAccent}>Leia mais</Link>
          </div>
          <div className={styles.card}>
            <h3>Vida Universitária</h3>
            <p>Saiba como aproveitar ao máximo seus anos na faculdade!</p>
            <Link href="/forum" className={styles.linkAccent}>Leia mais</Link>
          </div>
          <div className={styles.card}>
            <h3>Histórias de Sucesso</h3>
            <p>Inspire-se com as trajetórias de nossos alunos.</p>
            <Link href="/forum" className={styles.linkAccent}>Leia mais</Link>
          </div>
        </div>
        <Link href="/forum" className={styles.btnSecondary}>Ir para o Fórum</Link>
      </section>
    </div>
  );
}
