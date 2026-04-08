"use client";
import styles from "./page.module.css";
import Link from "next/link";
import { Swiper, SwiperSlide } from "swiper/react";
import { Pagination, Autoplay } from "swiper/modules";
import "swiper/css";
import "swiper/css/pagination";

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

          {/* Slide 2 - Equipe de Alunos */}
          <SwiperSlide className={styles.swiperSlideCustom}>
            <div className={styles.card} style={{ maxWidth: '800px' }}>
              <h3>Equipe de Alunos</h3>
              <div className={styles.avatarGrid}>
                <div className={styles.teamMember}>
                  <div className={styles.avatar}>DP</div>
                  <div className={styles.memberInfo}>
                    <p className={styles.memberName}>Daniel Pereira Santos da Silva</p>
                  </div>
                </div>
                <div className={styles.teamMember}>
                  <div className={styles.avatar}>JG</div>
                  <div className={styles.memberInfo}>
                    <p className={styles.memberName}>Juliana Gimenes Müller</p>
                  </div>
                </div>
                <div className={styles.teamMember}>
                  <div className={styles.avatar}>LC</div>
                  <div className={styles.memberInfo}>
                    <p className={styles.memberName}>Lucas Eduardo Sanches Cordeiro</p>
                  </div>
                </div>
                <div className={styles.teamMember}>
                  <div className={styles.avatar}>ME</div>
                  <div className={styles.memberInfo}>
                    <p className={styles.memberName}>Maria Eduarda Siqueira de Medeiros</p>
                  </div>
                </div>
                <div className={styles.teamMember}>
                  <div className={styles.avatar}>MG</div>
                  <div className={styles.memberInfo}>
                    <p className={styles.memberName}>Matheus Gabriel Ramos de Melo</p>
                  </div>
                </div>
                <div className={styles.teamMember}>
                  <div className={styles.avatar}>PM</div>
                  <div className={styles.memberInfo}>
                    <p className={styles.memberName}>Pedro de Magalhães Leitão</p>
                  </div>
                </div>
              </div>
            </div>
          </SwiperSlide>

          {/* Slide 3 - Equipe de Desenvolvimento */}
          <SwiperSlide className={styles.swiperSlideCustom}>
            <div className={styles.card} style={{ maxWidth: '800px' }}>
              <h3>Equipe de Desenvolvimento</h3>
              <div className={styles.avatarGrid}>
                <div className={styles.teamMember}>
                  <div className={styles.avatar}>DP</div>
                  <div className={styles.memberInfo}>
                    <p className={styles.memberName}>Daniel Pereira Santos da Silva</p>
                    <p className={styles.memberRole}>Engenheiro de Software</p>
                  </div>
                </div>
                <div className={styles.teamMember}>
                  <div className={styles.avatar}>JG</div>
                  <div className={styles.memberInfo}>
                    <p className={styles.memberName}>Juliana Gimenes Müller</p>
                    <p className={styles.memberRole}>Tech Lead, Arquiteta de Soluções & Engenheira de Software</p>
                  </div>
                </div>
                <div className={styles.teamMember}>
                  <div className={styles.avatar}>PM</div>
                  <div className={styles.memberInfo}>
                    <p className={styles.memberName}>Pedro de Magalhães Leitão</p>
                    <p className={styles.memberRole}>Engenheiro de Software</p>
                  </div>
                </div>
              </div>
            </div>
          </SwiperSlide>
          
          {/* Slide 4 - Equipe de Gerenciamento */}
          <SwiperSlide className={styles.swiperSlideCustom}>
            <div className={styles.card} style={{ maxWidth: '800px' }}>
              <h3>Equipe de Gerenciamento</h3>
              <div className={styles.avatarGrid}>
                <div className={styles.teamMember}>
                  <div className={styles.avatar}>LC</div>
                  <div className={styles.memberInfo}>
                    <p className={styles.memberName}>Lucas Eduardo Sanches Cordeiro</p>
                    <p className={styles.memberRole}>Co-fundador & CEO</p>
                  </div>
                </div>
                <div className={styles.teamMember}>
                  <div className={styles.avatar}>ME</div>
                  <div className={styles.memberInfo}>
                    <p className={styles.memberName}>Maria Eduarda Siqueira de Medeiros</p>
                    <p className={styles.memberRole}>Co-fundadora & COO</p>
                  </div>
                </div>
                <div className={styles.teamMember}>
                  <div className={styles.avatar}>MG</div>
                  <div className={styles.memberInfo}>
                    <p className={styles.memberName}>Matheus Gabriel Ramos de Melo</p>
                    <p className={styles.memberRole}>Co-fundador, CTO & Consultor Estratégico</p>
                  </div>
                </div>
              </div>
            </div>
          </SwiperSlide>

          {/* Slide 5 - Orientadores */}
          <SwiperSlide className={styles.swiperSlideCustom}>
            <div className={styles.card} style={{ maxWidth: '800px' }}>
              <h3>Orientadores</h3>
              <div className={styles.avatarGrid}>
                <div className={styles.teamMember}>
                  <div className={styles.avatar}>CR</div>
                  <div className={styles.memberInfo}>
                    <p className={styles.memberName}>Prof. Dr. Carlos Eduardo Raymundo</p>
                  </div>
                </div>
                <div className={styles.teamMember}>
                  <div className={styles.avatar}>TM</div>
                  <div className={styles.memberInfo}>
                    <p className={styles.memberName}>Prof. Dr. Thayse Moraes de Moraes</p>
                  </div>
                </div>
              </div>
            </div>
          </SwiperSlide>
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
