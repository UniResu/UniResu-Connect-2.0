"use client";
import styles from "./page.module.css";
import Link from "next/link";
import { Swiper, SwiperSlide } from "swiper/react";
import { Pagination, Autoplay } from "swiper/modules";
import "swiper/css";
import "swiper/css/pagination";

/**
 * Avatares simbólicos: ninguém da equipe tem foto, então cada pessoa recebe
 * um ícone ligado à sua função (ciência, tecnologia, marketing, liderança,
 * engenharia, orientação), com um gradiente próprio por função.
 */
type Simbolo = "ciencia" | "tecnologia" | "marketing" | "lideranca" | "engenharia" | "orientacao";

const ICONES: Record<Simbolo, React.ReactNode> = {
  // Erlenmeyer com bolhas
  ciencia: (
    <>
      <path d="M9.5 3h5" />
      <path d="M10 3v6.2L4.6 18a2 2 0 0 0 1.7 3h11.4a2 2 0 0 0 1.7-3L14 9.2V3" />
      <path d="M7.2 15.5h9.6" />
      <circle cx="10.5" cy="18.3" r="0.9" fill="currentColor" stroke="none" />
      <circle cx="13.6" cy="17.4" r="0.7" fill="currentColor" stroke="none" />
    </>
  ),
  // Chaves de código </>
  tecnologia: (
    <>
      <path d="M8 7l-5 5 5 5" />
      <path d="M16 7l5 5-5 5" />
      <path d="M14 4l-4 16" />
    </>
  ),
  // Megafone
  marketing: (
    <>
      <path d="M3 10.5v3a1 1 0 0 0 1 1h3l8 4.5V5L7 9.5H4a1 1 0 0 0-1 1z" />
      <path d="M18.5 9.5a3.5 3.5 0 0 1 0 5" />
      <path d="M8 15v4.5" />
    </>
  ),
  // Foguete
  lideranca: (
    <>
      <path d="M12 2.5c3 2.2 4.8 5.6 4.8 9.8l2.7 2.7-2.6 1-1 2.6-2.4-2.4H10.5l-2.4 2.4-1-2.6-2.6-1 2.7-2.7c0-4.2 1.8-7.6 4.8-9.8z" />
      <circle cx="12" cy="10" r="1.6" />
      <path d="M10.5 18.5c0 1.5.5 2.5 1.5 3 1-.5 1.5-1.5 1.5-3" />
    </>
  ),
  // Terminal
  engenharia: (
    <>
      <rect x="3" y="4.5" width="18" height="15" rx="2" />
      <path d="M7 9.5l3 2.5-3 2.5" />
      <path d="M12.5 14.5H17" />
    </>
  ),
  // Capelo
  orientacao: (
    <>
      <path d="M2.5 9.5L12 5l9.5 4.5L12 14z" />
      <path d="M6.5 11.8v4c0 1.4 2.5 2.7 5.5 2.7s5.5-1.3 5.5-2.7v-4" />
      <path d="M21.5 9.5v5.5" />
    </>
  ),
};

function Avatar({ simbolo, nome }: { simbolo: Simbolo; nome: string }) {
  return (
    <div className={`${styles.avatar} ${styles[`avatar_${simbolo}`]}`} role="img" aria-label={nome}>
      <svg
        className={styles.avatarIcon}
        viewBox="0 0 24 24"
        fill="none"
        stroke="currentColor"
        strokeWidth="1.7"
        strokeLinecap="round"
        strokeLinejoin="round"
        aria-hidden="true"
        focusable="false"
      >
        {ICONES[simbolo]}
      </svg>
    </div>
  );
}

interface Pessoa {
  nome: string;
  simbolo: Simbolo;
  cargo?: string;
}

const PESSOAS = {
  daniel: { nome: "Daniel Pereira Santos da Silva", simbolo: "engenharia" },
  juliana: { nome: "Juliana Gimenes Müller", simbolo: "tecnologia" },
  lucas: { nome: "Lucas Eduardo Sanches Cordeiro", simbolo: "lideranca" },
  mariaEduarda: { nome: "Maria Eduarda Siqueira de Medeiros", simbolo: "marketing" },
  matheus: { nome: "Matheus Gabriel Ramos de Melo", simbolo: "ciencia" },
  pedro: { nome: "Pedro de Magalhães Leitão", simbolo: "engenharia" },
  carlos: { nome: "Prof. Dr. Carlos Eduardo Raymundo", simbolo: "orientacao" },
  thayse: { nome: "Prof. Dr. Thayse Moraes de Moraes", simbolo: "orientacao" },
} satisfies Record<string, Pessoa>;

const EQUIPES: { titulo: string; pessoas: Pessoa[] }[] = [
  {
    titulo: "Equipe de Alunos",
    pessoas: [PESSOAS.daniel, PESSOAS.juliana, PESSOAS.lucas, PESSOAS.mariaEduarda, PESSOAS.matheus, PESSOAS.pedro],
  },
  {
    titulo: "Equipe de Desenvolvimento",
    pessoas: [
      { ...PESSOAS.daniel, cargo: "Engenheiro de Software" },
      { ...PESSOAS.juliana, cargo: "CTO (Technology) & Tech Lead" },
      { ...PESSOAS.pedro, cargo: "Engenheiro de Software" },
    ],
  },
  {
    titulo: "Equipe de Gerenciamento",
    pessoas: [
      { ...PESSOAS.lucas, cargo: "Co-fundador & CEO" },
      { ...PESSOAS.matheus, cargo: "Co-fundador & CSO (Science)" },
      { ...PESSOAS.juliana, cargo: "CTO (Technology)" },
      { ...PESSOAS.mariaEduarda, cargo: "Co-fundadora & CMO (Marketing)" },
    ],
  },
  {
    titulo: "Orientadores",
    pessoas: [PESSOAS.carlos, PESSOAS.thayse],
  },
];

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
        
        <Swiper
          modules={[Pagination, Autoplay]}
          spaceBetween={30}
          slidesPerView={1}
          pagination={{ clickable: true }}
          autoplay={{ delay: 8000, disableOnInteraction: false }}
          className={styles.swiperContainer}
        >
          {/* Slide 1 - Textos Institucionais */}
          <SwiperSlide className={styles.swiperSlideCustom}>
            <div className={styles.institutionalGrid}>
              <div className={styles.card}>
                <h3>Quem Somos</h3>
                <p>O UniResu Connect é uma plataforma de integração acadêmica que conecta estudantes e professores de diferentes instituições para desenvolvimento científico colaborativo, ampliando acesso a oportunidades de pesquisa e produção acadêmica.</p>
              </div>
              <div className={styles.card}>
                <h3>Objetivos</h3>
                <p>Nosso objetivo é conectar pessoas, ideias e produções acadêmicas de forma acessível, organizada e contínua, promovendo uma cultura de colaboração e protagonismo universitário.</p>
              </div>
              <div className={styles.card}>
                <h3>O que promovemos</h3>
                <p>Oferecemos espaços de discussão por áreas temáticas e interesses acadêmicos, além de publicações de eventos e oportunidades acadêmicas. Organizamos projetos, produções e atividades da comunidade, e mantemos abertura para contribuições, desde sugestões até desenvolvimento técnico e editorial.</p>
              </div>
            </div>
          </SwiperSlide>

          {/* Slides 2 a 5 - Equipes (alunos, desenvolvimento, gerenciamento, orientadores) */}
          {EQUIPES.map((equipe) => (
            <SwiperSlide key={equipe.titulo} className={styles.swiperSlideCustom}>
              <div className={styles.card} style={{ maxWidth: '800px' }}>
                <h3>{equipe.titulo}</h3>
                <div className={styles.avatarGrid}>
                  {equipe.pessoas.map((pessoa) => (
                    <div key={pessoa.nome} className={styles.teamMember}>
                      <Avatar simbolo={pessoa.simbolo} nome={pessoa.nome} />
                      <div className={styles.memberInfo}>
                        <p className={styles.memberName}>{pessoa.nome}</p>
                        {pessoa.cargo && <p className={styles.memberRole}>{pessoa.cargo}</p>}
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            </SwiperSlide>
          ))}
        </Swiper>
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
        <div className={styles.ufoContainer}>
          <img src="/ufo.png" alt="Nave Espacial Flutuante" className={styles.ufoImage} />
        </div>
        
        <h2 className={`${styles.sectionTitle} ${styles.forumTitle}`}>Forum</h2>
        <p className={styles.forumSubtitle}>Embarque na nossa rede de conhecimento e descubra um universo de novas oportunidades de integração!</p>

        <div className={styles.cardsContainer}>
          <div className={styles.forumCard}>
            <h3>Conecte-se com a Comunidade</h3>
            <p>Fique por dentro das novidades! Visualize Artigos, Eventos, Seminários e muito mais na plataforma.</p>
          </div>
          <div className={styles.forumCard}>
            <h3>Vida Universitária</h3>
            <p>Saiba como aproveitar ao máximo seus anos na faculdade e se engajar ativamente em projetos!</p>
          </div>
          <div className={styles.forumCard}>
            <h3>Histórias de Sucesso</h3>
            <p>Inspire-se com as trajetórias de nossos alunos brilhantes e pesquisadores do campus.</p>
          </div>
        </div>
        <Link href="/forum" className={styles.btnForum}>Explorar Fórum</Link>
      </section>
    </div>
  );
}
