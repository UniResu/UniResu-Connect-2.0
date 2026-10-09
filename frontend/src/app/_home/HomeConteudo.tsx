"use client";

import { useEffect, useState, type FormEvent, type ReactNode } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import Image from "next/image";
import { Swiper, SwiperSlide } from "swiper/react";
import { Autoplay, EffectFade, Keyboard } from "swiper/modules";
import type { Swiper as SwiperInstancia } from "swiper/types";
import "swiper/css";
import "swiper/css/effect-fade";
import AvatarMembro from "@/components/home/AvatarMembro";
import ProjetoCard from "@/components/projetos/ProjetoCard";
import { IconeLupa, IconeNaveTransmite, IconeSetaDireita, IconeSetaEsquerda } from "@/components/ui/Icones";
import { useMediaQuery } from "@/hooks/useMediaQuery";
import { acordarApi, api } from "@/lib/api";
import type { Projeto } from "@/types/projeto";
import type { Topico } from "@/app/forum/_componentes/forum";
import {
  ROTA_PERGUNTAS,
  ROTA_PROJETOS,
  resumirPergunta,
  resumirProjeto,
  type PerguntaVitrine,
} from "./vitrine";
import styles from "../page.module.css";

/* ── Ícones (SVG inline no estilo Lucide, traço 2) ── */

type NomeIcone = "usuarios" | "alvo" | "megafone";

function Icone({ nome }: { nome: NomeIcone }) {
  const comum = {
    viewBox: "0 0 24 24",
    width: 20,
    height: 20,
    fill: "none",
    stroke: "currentColor",
    strokeWidth: 2,
    strokeLinecap: "round" as const,
    strokeLinejoin: "round" as const,
    "aria-hidden": true,
    focusable: false,
  };
  switch (nome) {
    case "usuarios":
      return (
        <svg {...comum}>
          <path d="M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2" />
          <circle cx="9" cy="7" r="4" />
          <path d="M22 21v-2a4 4 0 0 0-3-3.87" />
          <path d="M16 3.13a4 4 0 0 1 0 7.75" />
        </svg>
      );
    case "alvo":
      return (
        <svg {...comum}>
          <circle cx="12" cy="12" r="10" />
          <circle cx="12" cy="12" r="6" />
          <circle cx="12" cy="12" r="2" />
        </svg>
      );
    case "megafone":
      return (
        <svg {...comum}>
          <path d="m3 11 18-5v12L3 14v-3z" />
          <path d="M11.6 16.8a3 3 0 1 1-5.8-1.6" />
        </svg>
      );
  }
}

/* ── Cabeçalho das seções ── */

/** Rótulo pequeno, título e texto alinhados à esquerda; no desktop, o link
 *  para a página da seção fica à direita (no celular, um botão no fim). */
function CabecalhoSecao({
  id,
  rotulo,
  titulo,
  texto,
  acao,
}: {
  id: string;
  rotulo: string;
  titulo: string;
  texto?: string;
  acao?: { href: string; texto: string };
}) {
  return (
    <header className={styles.secaoCabecalho}>
      <div className={styles.secaoCabecalhoTexto}>
        <p className={styles.secaoRotulo}>{rotulo}</p>
        <h2 id={id} className={styles.secaoTitulo}>
          {titulo}
        </h2>
        {texto && <p className={styles.secaoSubtitulo}>{texto}</p>}
      </div>
      {acao && (
        <Link href={acao.href} className={styles.secaoLink}>
          {acao.texto}
          <IconeSetaDireita tamanho={18} />
        </Link>
      )}
    </header>
  );
}

/* ── Hero: a busca é a primeira coisa da página ── */

function BuscaHero() {
  const router = useRouter();
  const [termo, setTermo] = useState("");

  function buscar(e: FormEvent) {
    e.preventDefault();
    const t = termo.trim();
    router.push(t ? `/projetos?q=${encodeURIComponent(t)}` : "/projetos");
  }

  // action/method: sem JavaScript, o formulário ainda leva à busca.
  return (
    <form className={styles.heroBusca} role="search" action="/projetos" method="get" onSubmit={buscar}>
      <label htmlFor="busca-inicio" className="sr-only">
        Buscar projetos
      </label>
      <span className={styles.heroBuscaIcone} aria-hidden="true">
        <IconeLupa tamanho={20} />
      </span>
      <input
        id="busca-inicio"
        name="q"
        type="search"
        value={termo}
        onChange={(e) => setTermo(e.target.value)}
        placeholder="Busque por tema ou coordenação"
        className={styles.heroBuscaCampo}
        autoComplete="off"
        enterKeyHint="search"
      />
      <button type="submit" className={`ui-btn ${styles.heroBuscaBotao}`}>
        Buscar
      </button>
    </form>
  );
}

/* ── Como funciona ── */

const PASSOS: { titulo: string; texto: string; link?: { href: string; texto: string } }[] = [
  {
    titulo: "Crie sua conta",
    texto:
      "Use o e-mail da sua instituição ou entre com o ORCID. É com a conta que você envia cartas e participa do fórum.",
    link: { href: "/registrar", texto: "Criar conta" },
  },
  {
    titulo: "Encontre um projeto",
    texto: "Busque entre projetos de pesquisa e extensão em andamento, publicados pelas próprias universidades.",
  },
  {
    titulo: "Envie sua carta de intenção",
    texto: "Conte por que quer participar. A carta vai por e-mail para a coordenação, com cópia para você.",
  },
  {
    titulo: "Combine com a coordenação",
    texto:
      "A resposta chega no seu e-mail. Enquanto isso, o fórum ajuda com dúvidas sobre bolsas, carta e rotina de pesquisa.",
  },
];

function ComoFunciona() {
  return (
    <section className={`${styles.secao} ${styles.comoFunciona}`} id="como-funciona" aria-labelledby="titulo-como">
      <div className={styles.container}>
        <CabecalhoSecao id="titulo-como" rotulo="Como funciona" titulo="Da conta à coordenação em quatro passos" />
        <ol className={styles.passos}>
          {PASSOS.map((passo, i) => (
            <li key={passo.titulo} className={styles.passo}>
              <span className={styles.passoNumero} aria-hidden="true">
                {i + 1}
              </span>
              <div className={styles.passoTexto}>
                <h3 className={styles.passoTitulo}>{passo.titulo}</h3>
                <p className={styles.passoCorpo}>{passo.texto}</p>
                {passo.link && (
                  <Link href={passo.link.href} className={styles.passoLink}>
                    {passo.link.texto}
                    <IconeSetaDireita tamanho={16} />
                  </Link>
                )}
              </div>
            </li>
          ))}
        </ol>
      </div>
    </section>
  );
}

/* ── Quem somos: conteúdo ──
   Três slides: os textos institucionais, a equipe (cada pessoa uma vez, com
   o cargo) e a orientação. No celular os três ficam empilhados; no desktop
   viram carrossel com fade. */

const INSTITUCIONAL: { titulo: string; texto: string; icone: NomeIcone }[] = [
  {
    titulo: "A plataforma",
    icone: "usuarios",
    texto:
      "O UniResu Connect é uma plataforma de integração acadêmica que conecta estudantes e professores de diferentes instituições para desenvolvimento científico colaborativo, ampliando acesso a oportunidades de pesquisa e produção acadêmica.",
  },
  {
    titulo: "Objetivos",
    icone: "alvo",
    texto:
      "Nosso objetivo é conectar pessoas, ideias e produções acadêmicas de forma acessível, organizada e contínua, promovendo uma cultura de colaboração e protagonismo universitário.",
  },
  {
    titulo: "O que promovemos",
    icone: "megafone",
    texto:
      "Oferecemos espaços de discussão por áreas temáticas e interesses acadêmicos, além de publicações de eventos e oportunidades acadêmicas. Organizamos projetos, produções e atividades da comunidade, e mantemos abertura para contribuições, desde sugestões até desenvolvimento técnico e editorial.",
  },
];

interface Membro {
  nome: string;
  /** Cargo na plataforma, quando houver (fundadores e desenvolvimento). */
  cargo?: string;
  /** Curso em andamento (estudantes). */
  curso?: string;
  instituicao: string;
}

const JULIANA = {
  nome: "Juliana Gimenes Müller",
  curso: "Análise e Desenvolvimento de Sistemas",
  instituicao: "PUC Minas",
};

// Ordem definida pela equipe: Lucas, Matheus, Maria Eduarda e Juliana.
const FUNDADORES: Membro[] = [
  { nome: "Lucas Eduardo Sanches Cordeiro", cargo: "Co-fundador e CEO", curso: "Medicina", instituicao: "UERJ" },
  { nome: "Matheus Gabriel Ramos de Melo", cargo: "Co-fundador e CSO", curso: "Medicina", instituicao: "UNIR" },
  {
    nome: "Maria Eduarda Siqueira de Medeiros",
    cargo: "Co-fundadora e CMO",
    curso: "Medicina",
    instituicao: "Afya Garanhuns",
  },
  { ...JULIANA, cargo: "Co-fundadora e CTO" },
];

// Juliana também lidera o desenvolvimento, e Matheus coordena o produto desde
// o início (arquitetura, organização e metodologia); os dois aparecem também
// entre os fundadores.
const DESENVOLVIMENTO: Membro[] = [
  { ...JULIANA, cargo: "Head de desenvolvimento" },
  { nome: "Matheus Gabriel Ramos de Melo", cargo: "Coordenador de Produto", curso: "Medicina", instituicao: "UNIR" },
  { nome: "Daniel Pereira Santos da Silva", cargo: "Desenvolvedor", curso: "Ciência da computação", instituicao: "UERJ" },
  { nome: "Pedro de Magalhães Leitão", cargo: "Desenvolvedor", curso: "Ciência da computação", instituicao: "UERJ" },
];

const ORIENTACAO: Membro[] = [
  { nome: "Prof. Dr. Carlos Eduardo Raymundo", instituicao: "UERJ" },
  { nome: "Prof. Dr. Thayse Moraes de Moraes", instituicao: "UEPA" },
];

type SlideQuemSomos =
  | { id: "institucional"; tipo: "institucional"; aba: string }
  | {
      id: "fundadores" | "desenvolvimento" | "orientacao";
      tipo: "pessoas";
      aba: string;
      titulo: string;
      descricao: string;
      membros: Membro[];
    };

const SLIDES_QUEM_SOMOS: SlideQuemSomos[] = [
  { id: "institucional", tipo: "institucional", aba: "A plataforma" },
  {
    id: "fundadores",
    tipo: "pessoas",
    aba: "Equipe fundadora",
    titulo: "Equipe fundadora",
    descricao: "Estudantes que idealizaram o UniResu Connect e conduzem o projeto.",
    membros: FUNDADORES,
  },
  {
    id: "desenvolvimento",
    tipo: "pessoas",
    aba: "Desenvolvimento",
    titulo: "Desenvolvimento",
    descricao: "Quem constrói e mantém a plataforma.",
    membros: DESENVOLVIMENTO,
  },
  {
    id: "orientacao",
    tipo: "pessoas",
    aba: "Orientação",
    titulo: "Orientação",
    descricao: "Professores que orientam o projeto.",
    membros: ORIENTACAO,
  },
];

/** "Medicina, UERJ" para estudantes; só a instituição para a orientação. */
function credencial(membro: Membro) {
  return membro.curso ? `${membro.curso}, ${membro.instituicao}` : membro.instituicao;
}

/** Intervalo do carrossel (ms). */
const INTERVALO_CARROSSEL = 4000;

/** A partir desta largura a seção vira carrossel; até 768px ela fica empilhada. */
const DESKTOP_QUERY = "(min-width: 769px)";

/** Um slide da seção, com o mesmo DOM na versão empilhada e no carrossel. */
function SlideQuemSomosView({ slide }: { slide: SlideQuemSomos }) {
  if (slide.tipo === "institucional") {
    return (
      <div className={styles.institucionalGrid}>
        {INSTITUCIONAL.map((item) => (
          <article key={item.titulo} className={`ui-card ${styles.cardTexto}`}>
            <span className={styles.cardIcone}>
              <Icone nome={item.icone} />
            </span>
            <h3 className={styles.cardTitulo}>{item.titulo}</h3>
            <p className={styles.cardCorpo}>{item.texto}</p>
          </article>
        ))}
      </div>
    );
  }

  return (
    <div className={styles.bloco}>
      <div className={styles.blocoCabecalho}>
        <h3 className={styles.blocoTitulo}>{slide.titulo}</h3>
        <p className={styles.blocoDescricao}>{slide.descricao}</p>
      </div>
      <ul
        className={`${styles.pessoasGrid} ${slide.membros.length === 2 ? styles.pessoasGridDupla : ""} ${
          slide.membros.length === 4 ? styles.pessoasGridQuadrupla : ""
        }`}
      >
        {slide.membros.map((membro) => (
          <li key={membro.nome} className={`ui-card ${styles.pessoa}`}>
            <AvatarMembro nome={membro.nome} />
            <p className={styles.pessoaNome}>{membro.nome}</p>
            {membro.cargo && <span className={`ui-chip ui-chip-primary ${styles.pessoaCargo}`}>{membro.cargo}</span>}
            <p className={styles.pessoaCredencial}>{credencial(membro)}</p>
          </li>
        ))}
      </ul>
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
  const [swiper, setSwiper] = useState<SwiperInstancia | null>(null);
  const [ativo, setAtivo] = useState(0);
  const [pausado, setPausado] = useState(false);

  // Quem clica numa aba ou numa seta assume o controle: o carrossel para de
  // avançar sozinho, para dar tempo de ler.
  function irPara(indice: number) {
    if (!swiper) return;
    swiper.autoplay?.stop();
    setPausado(true);
    swiper.slideTo(indice);
  }

  function alternarPausa() {
    if (!swiper) return;
    if (pausado) swiper.autoplay?.start();
    else swiper.autoplay?.stop();
    setPausado(!pausado);
  }

  const total = SLIDES_QUEM_SOMOS.length;

  return (
    <section className={`${styles.secao} ${styles.secaoClara}`} id="quem-somos" aria-labelledby="titulo-quem-somos">
      <div className={styles.container}>
        <CabecalhoSecao
          id="titulo-quem-somos"
          rotulo="O projeto"
          titulo="Quem somos"
          texto="Quem constrói o UniResu Connect e o que a plataforma propõe."
        />

        {desktop ? (
          <div className={styles.carrosselArea} role="region" aria-roledescription="carrossel" aria-label="Quem somos">
            {/* Abas com nome: cada slide tem um destino claro, em vez de bolinhas. */}
            <div className={styles.abas} role="tablist" aria-label="Seções de Quem somos">
              {SLIDES_QUEM_SOMOS.map((slide, i) => (
                <button
                  key={slide.id}
                  type="button"
                  role="tab"
                  aria-selected={i === ativo}
                  className={`${styles.aba} ${i === ativo ? styles.abaAtiva : ""}`}
                  onClick={() => irPara(i)}
                >
                  {slide.aba}
                </button>
              ))}
            </div>

            <div className={styles.carrosselLinha}>
              <button
                type="button"
                className={styles.seta}
                onClick={() => irPara((ativo - 1 + total) % total)}
                aria-label="Seção anterior"
              >
                <IconeSetaEsquerda tamanho={22} />
              </button>

              <Swiper
                modules={[Autoplay, EffectFade, Keyboard]}
                effect="fade"
                fadeEffect={{ crossFade: true }}
                speed={600}
                slidesPerView={1}
                rewind
                keyboard={{ enabled: true, onlyInViewport: true }}
                autoplay={{ delay: INTERVALO_CARROSSEL, disableOnInteraction: false, pauseOnMouseEnter: true }}
                onSwiper={setSwiper}
                onSlideChange={(s) => setAtivo(s.realIndex)}
                className={styles.carrossel}
              >
                {SLIDES_QUEM_SOMOS.map((slide) => (
                  <SwiperSlide key={slide.id} className={styles.slide}>
                    <SlideQuemSomosView slide={slide} />
                  </SwiperSlide>
                ))}
              </Swiper>

              <button
                type="button"
                className={styles.seta}
                onClick={() => irPara((ativo + 1) % total)}
                aria-label="Próxima seção"
              >
                <IconeSetaDireita tamanho={22} />
              </button>
            </div>

            <div className={styles.carrosselRodape}>
              <span className={styles.contador} aria-live="polite">
                {ativo + 1} de {total}
              </span>
              <button type="button" className={`ui-btn ui-btn-ghost ui-btn-sm`} onClick={alternarPausa}>
                {pausado ? "Retomar passagem automática" : "Pausar passagem automática"}
              </button>
            </div>
          </div>
        ) : (
          <div className={styles.quemSomosLista}>
            {SLIDES_QUEM_SOMOS.map((slide) => (
              <SlideQuemSomosView key={slide.id} slide={slide} />
            ))}
          </div>
        )}
      </div>
    </section>
  );
}

/* ── Projetos acadêmicos ── */

function EsqueletoProjeto() {
  return (
    <div className={`ui-card ${styles.esqueleto}`}>
      <span className={`skeleton ${styles.esqueletoLinha} ${styles.esqueletoCurta}`} />
      <span className={`skeleton ${styles.esqueletoTitulo}`} />
      <span className={`skeleton ${styles.esqueletoTitulo} ${styles.esqueletoMedia}`} />
      <span className={`skeleton ${styles.esqueletoLinha} ${styles.esqueletoMedia}`} />
      <div className={styles.esqueletoChips}>
        <span className={`skeleton ${styles.esqueletoChip}`} />
        <span className={`skeleton ${styles.esqueletoChip}`} />
      </div>
    </div>
  );
}

/**
 * Lista da vitrine: normalmente chega pronta do servidor (ver ../page.tsx).
 * Sem ela (a API não respondeu no build), o navegador busca na API.
 * `mapear` precisa ser uma função estável, definida fora do componente.
 */
function useListaDaVitrine<T, R>(iniciais: R[] | null, rota: string, mapear: (item: T) => R) {
  const [itens, setItens] = useState<R[] | null>(iniciais);
  const [erro, setErro] = useState(false);

  useEffect(() => {
    if (iniciais) return;
    let ativo = true;
    api
      .get<T[]>(rota)
      .then((data) => {
        if (ativo) setItens(Array.isArray(data) ? data.map(mapear) : []);
      })
      .catch(() => {
        if (ativo) setErro(true);
      });
    return () => {
      ativo = false;
    };
  }, [iniciais, rota, mapear]);

  return { itens, erro };
}

/**
 * Três projetos reais da busca. Enquanto o navegador carrega (só quando o
 * servidor não os trouxe), esqueletos; se a API falhar ou não houver
 * projetos, uma frase com link para a busca.
 */
function ProjetosDestaque({ iniciais }: { iniciais: Projeto[] | null }) {
  const { itens: projetos, erro } = useListaDaVitrine<Projeto, Projeto>(iniciais, ROTA_PROJETOS, resumirProjeto);

  const carregando = projetos === null && !erro;

  let conteudo: ReactNode;
  if (erro) {
    conteudo = (
      <p className={styles.aviso}>
        Não foi possível carregar os projetos agora. <Link href="/projetos">Abrir a busca de projetos</Link>
      </p>
    );
  } else if (projetos === null) {
    conteudo = (
      <div className={styles.projetosGrid} aria-hidden="true">
        <EsqueletoProjeto />
        <EsqueletoProjeto />
        <EsqueletoProjeto />
      </div>
    );
  } else if (projetos.length === 0) {
    conteudo = (
      <p className={styles.aviso}>
        Nenhum projeto publicado por enquanto. <Link href="/projetos">Abrir a busca de projetos</Link>
      </p>
    );
  } else {
    conteudo = (
      <div className={styles.projetosGrid}>
        {projetos.map((projeto) => (
          <ProjetoCard
            key={projeto.id}
            projeto={projeto}
            compacto
            href={`/projetos?projeto=${encodeURIComponent(projeto.id)}`}
          />
        ))}
      </div>
    );
  }

  return (
    <section className={`${styles.secao} ${styles.secaoClara}`} id="projetos" aria-labelledby="titulo-projetos">
      <div className={styles.container}>
        <CabecalhoSecao
          id="titulo-projetos"
          rotulo="Projetos acadêmicos"
          titulo="Uma amostra do que está em andamento"
          texto="Projetos de pesquisa e extensão que as universidades publicam em acesso aberto."
          acao={{ href: "/projetos", texto: "Ver todos os projetos" }}
        />

        <p role="status" aria-live="polite" className="sr-only">
          {carregando ? "Carregando projetos" : ""}
        </p>
        {conteudo}

        <div className={styles.secaoAcao}>
          <Link href="/projetos" className="ui-btn ui-btn-primary ui-btn-lg">
            Ver todos os projetos
          </Link>
        </div>
      </div>
    </section>
  );
}

/* ── Fórum ── */

/** As três perguntas mais recentes, cada uma levando à própria página. */
function Forum({ iniciais }: { iniciais: PerguntaVitrine[] | null }) {
  const { itens: perguntas, erro } = useListaDaVitrine<Topico, PerguntaVitrine>(
    iniciais,
    ROTA_PERGUNTAS,
    resumirPergunta
  );

  let conteudo: ReactNode;
  if (erro || (perguntas && perguntas.length === 0)) {
    conteudo = null;
  } else if (perguntas === null) {
    conteudo = (
      <div className={styles.forumGrid} aria-hidden="true">
        <span className={`skeleton ${styles.forumEsqueleto}`} />
        <span className={`skeleton ${styles.forumEsqueleto}`} />
        <span className={`skeleton ${styles.forumEsqueleto}`} />
      </div>
    );
  } else {
    conteudo = (
      <ul className={styles.forumGrid}>
        {perguntas.slice(0, 3).map((p) => (
          <li key={p.id}>
            <Link href={`/forum/${encodeURIComponent(p.id)}`} className={styles.forumCard}>
              <span className={styles.forumCardTopo}>
                <IconeNaveTransmite tamanho={16} />
                {p.respostas === 1 ? "1 resposta" : `${p.respostas} respostas`}
              </span>
              <h3 className={styles.forumCardTitulo}>{p.titulo}</h3>
              {p.resumo && <p className={styles.forumCardTexto}>{p.resumo}</p>}
              <span className={styles.forumCardAutor}>@{p.autor}</span>
            </Link>
          </li>
        ))}
      </ul>
    );
  }

  return (
    <section className={`${styles.secao} ${styles.forum}`} id="forum" aria-labelledby="titulo-forum">
      <div className={styles.ufo} aria-hidden="true">
        {/* PNG estático de /public: sem otimizador e sem lazy loading, para a nave
            aparecer assim que a seção entra na tela. */}
        <Image src="/ufo.png" alt="" width={160} height={160} className={styles.ufoImagem} unoptimized loading="eager" />
      </div>

      <div className={`${styles.container} ${styles.forumConteudo}`}>
        <CabecalhoSecao
          id="titulo-forum"
          rotulo="Fórum"
          titulo="Perguntas recentes da comunidade"
          texto="Dúvidas e respostas sobre pesquisa, extensão e vida universitária."
          acao={{ href: "/forum", texto: "Explorar fórum" }}
        />

        {conteudo}

        <div className={styles.secaoAcao}>
          <Link href="/forum" className={`ui-btn ui-btn-lg ${styles.btnEscuroPrimario}`}>
            Explorar fórum
          </Link>
        </div>
      </div>
    </section>
  );
}

/* ── Página ── */

/** Conteúdo da página inicial. As listas vêm do servidor e são null quando
 *  a API não respondeu a tempo no build. */
export default function HomeConteudo({
  projetosIniciais,
  perguntasIniciais,
  numeros,
}: {
  projetosIniciais: Projeto[] | null;
  perguntasIniciais: PerguntaVitrine[] | null;
  /** "20.258 projetos em andamento em 46 instituições", ou null. */
  numeros: string | null;
}) {
  // Acorda a API enquanto a pessoa lê: o clique num card de projeto ou de
  // pergunta abre a página sem a espera do primeiro acesso.
  useEffect(() => {
    acordarApi();
  }, []);

  return (
    <div className={styles.page}>
      <section className={styles.hero} id="home" aria-labelledby="titulo-hero">
        <div className={`${styles.container} ${styles.heroConteudo} animate-fade-in`}>
          <p className={styles.heroKicker}>Conectando a comunidade acadêmica</p>
          <h1 id="titulo-hero" className={styles.heroTitulo}>
            UniResu <span className={styles.heroDestaque}>Connect</span>
          </h1>
          <p className={styles.heroTexto}>
            Uma plataforma que une alunos, professores e pesquisadores em uma rede de oportunidades,
            conhecimento e colaboração.
          </p>
          <BuscaHero />
          <p className={styles.heroRodape}>
            {numeros && (
              <>
                <span className={styles.heroNumeros}>{numeros}</span>
                <span className={styles.heroSeparador} aria-hidden="true" />
              </>
            )}
            <Link href="/projetos" className={styles.heroLink}>
              Ver todos
            </Link>
            <span className={styles.heroSeparador} aria-hidden="true" />
            <Link href="/registrar" className={styles.heroLink}>
              Criar conta
            </Link>
          </p>
        </div>
      </section>

      <ComoFunciona />
      <ProjetosDestaque iniciais={projetosIniciais} />
      <Forum iniciais={perguntasIniciais} />
      <QuemSomos />
    </div>
  );
}
