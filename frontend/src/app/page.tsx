"use client";
import styles from "./page.module.css";
import AvatarMembro, { type FuncaoMembro } from "@/components/home/AvatarMembro";
import { useMediaQuery } from "@/hooks/useMediaQuery";
import Link from "next/link";
import { Swiper, SwiperSlide } from "swiper/react";
import { Pagination, Autoplay, EffectFade } from "swiper/modules";
import "swiper/css";
import "swiper/css/pagination";
import "swiper/css/effect-fade";

/* ── Quem somos: conteúdo dos blocos ──
   Uma única lista alimenta as duas apresentações da seção: empilhada no
   celular (e na renderização do servidor) e em carrossel com fade no
   desktop. Cada bloco vira um card ou uma fileira de cards. */

interface Membro {
  nome: string;
  funcao: FuncaoMembro;
  cargo?: string;
}

type BlocoQuemSomos =
  | { id: string; tipo: "institucional"; itens: { titulo: string; texto: string }[] }
  | { id: string; tipo: "equipe"; titulo: string; membros: Membro[] };

const BLOCOS_QUEM_SOMOS: BlocoQuemSomos[] = [
  {
    id: "institucional",
    tipo: "institucional",
    itens: [
      {
        titulo: "Quem somos",
        texto:
          "O UniResu Connect é uma plataforma de integração acadêmica que conecta estudantes e professores de diferentes instituições para desenvolvimento científico colaborativo, ampliando acesso a oportunidades de pesquisa e produção acadêmica.",
      },
      {
        titulo: "Objetivos",
        texto:
          "Nosso objetivo é conectar pessoas, ideias e produções acadêmicas de forma acessível, organizada e contínua, promovendo uma cultura de colaboração e protagonismo universitário.",
      },
      {
        titulo: "O que promovemos",
        texto:
          "Oferecemos espaços de discussão por áreas temáticas e interesses acadêmicos, além de publicações de eventos e oportunidades acadêmicas. Organizamos projetos, produções e atividades da comunidade, e mantemos abertura para contribuições, desde sugestões até desenvolvimento técnico e editorial.",
      },
    ],
  },
  {
    id: "alunos",
    tipo: "equipe",
    titulo: "Equipe de Alunos",
    membros: [
      { nome: "Daniel Pereira Santos da Silva", funcao: "aluno" },
      { nome: "Juliana Gimenes Müller", funcao: "aluno" },
      { nome: "Lucas Eduardo Sanches Cordeiro", funcao: "aluno" },
      { nome: "Maria Eduarda Siqueira de Medeiros", funcao: "aluno" },
      { nome: "Matheus Gabriel Ramos de Melo", funcao: "aluno" },
      { nome: "Pedro de Magalhães Leitão", funcao: "aluno" },
    ],
  },
  {
    id: "desenvolvimento",
    tipo: "equipe",
    titulo: "Equipe de Desenvolvimento",
    membros: [
      { nome: "Daniel Pereira Santos da Silva", funcao: "dev", cargo: "Engenheiro de Software" },
      { nome: "Juliana Gimenes Müller", funcao: "cto", cargo: "Co-fundadora & CTO" },
      { nome: "Pedro de Magalhães Leitão", funcao: "dev", cargo: "Engenheiro de Software" },
    ],
  },
  {
    id: "gerenciamento",
    tipo: "equipe",
    titulo: "Equipe de Gerenciamento",
    membros: [
      { nome: "Lucas Eduardo Sanches Cordeiro", funcao: "ceo", cargo: "Co-fundador & CEO" },
      { nome: "Maria Eduarda Siqueira de Medeiros", funcao: "cmo", cargo: "Co-fundadora & CMO" },
      { nome: "Matheus Gabriel Ramos de Melo", funcao: "cso", cargo: "Co-fundador & CSO" },
    ],
  },
  {
    id: "orientadores",
    tipo: "equipe",
    titulo: "Orientadores",
    membros: [
      { nome: "Prof. Dr. Carlos Eduardo Raymundo", funcao: "orientador" },
      { nome: "Prof. Dr. Thayse Moraes de Moraes", funcao: "orientador" },
    ],
  },
];

/** A partir desta largura a seção vira carrossel; até 768px ela fica empilhada. */
const DESKTOP_QUERY = "(min-width: 769px)";

/** Um bloco da seção, com o mesmo DOM na versão empilhada e no carrossel. */
function BlocoQuemSomosView({ bloco }: { bloco: BlocoQuemSomos }) {
  if (bloco.tipo === "institucional") {
    return (
      <div className={styles.institutionalGrid}>
        {bloco.itens.map((item) => (
          <div key={item.titulo} className={styles.card}>
            <h3>{item.titulo}</h3>
            <p>{item.texto}</p>
          </div>
        ))}
      </div>
    );
  }

  return (
    <div className={`${styles.card} ${styles.cardEquipe}`}>
      <h3>{bloco.titulo}</h3>
      <div className={styles.avatarGrid}>
        {bloco.membros.map((membro) => (
          <div key={membro.nome} className={styles.teamMember}>
            <AvatarMembro nome={membro.nome} funcao={membro.funcao} />
            <div className={styles.memberInfo}>
              <p className={styles.memberName}>{membro.nome}</p>
              {membro.cargo && <p className={styles.memberRole}>{membro.cargo}</p>}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

/**
 * Seção "Quem somos". O servidor sempre gera a versão empilhada; o cliente
 * troca para o carrossel só depois de hidratar e confirmar que a tela é de
 * desktop, o que evita diferença entre o HTML do servidor e o do cliente.
 */
function QuemSomos() {
  const desktop = useMediaQuery(DESKTOP_QUERY);

  return (
    <section className={styles.quemSomosSection} id="quem-somos">
      <h2 className={styles.sectionTitle}>Quem somos</h2>

      {desktop ? (
        <Swiper
          modules={[Pagination, Autoplay, EffectFade]}
          effect="fade"
          fadeEffect={{ crossFade: true }}
          speed={700}
          slidesPerView={1}
          pagination={{ clickable: true }}
          autoplay={{ delay: 4000, disableOnInteraction: false, pauseOnMouseEnter: true }}
          className={styles.swiperContainer}
        >
          {BLOCOS_QUEM_SOMOS.map((bloco) => (
            <SwiperSlide key={bloco.id} className={styles.swiperSlideCustom}>
              <BlocoQuemSomosView bloco={bloco} />
            </SwiperSlide>
          ))}
        </Swiper>
      ) : (
        <div className={styles.quemSomosLista}>
          {BLOCOS_QUEM_SOMOS.map((bloco) => (
            <BlocoQuemSomosView key={bloco.id} bloco={bloco} />
          ))}
        </div>
      )}
    </section>
  );
}

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

      <QuemSomos />

      {/* ── Projetos ── */}
      <section className={styles.projetosSection} id="projetos">
        <h2 className={styles.sectionTitle}>Projetos Acadêmicos</h2>
        <p className={styles.sectionSubtitle}>
          Esses são os exemplos de projetos que você vai encontrar aqui. Descubra, contribua e candidate-se.
          Clique em &quot;Explorar Projetos&quot; para ver tudo.
        </p>
        <div className={styles.cardsContainerCol}>
          <div className={styles.projetoCard}>
            <div className={styles.projetoInfo}>
              <h3>Diagnóstico e Tratamento de sepse por bacilos Gram-negativos em Centros de Tratamento Intensivo do Rio de Janeiro</h3>
              <p>Diagnóstico e Tratamento de sepse por bacilos Gram-negativos em Centros de Tratamento Intensivo do Rio de Janeiro</p>
            </div>
            <div className={styles.projetoDetalhes}>
              <span>UERJ</span>
              <span className={styles.tipo}>Projeto Institucional <strong>(Exclusivo)</strong></span>
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
