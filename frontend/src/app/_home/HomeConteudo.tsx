"use client";

import { useEffect, useState, type CSSProperties, type FormEvent, type ReactNode } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import Image from "next/image";
import { Swiper, SwiperSlide } from "swiper/react";
import { Autoplay, EffectFade, Keyboard } from "swiper/modules";
import type { Swiper as SwiperInstancia } from "swiper/types";
import "swiper/css";
import "swiper/css/effect-fade";
import AvatarMembro, { type SimboloFuncao } from "@/components/home/AvatarMembro";
import ProjetoCard from "@/components/projetos/ProjetoCard";
import { IconeLupa, IconeNaveTransmite, IconeSetaDireita, IconeSetaEsquerda } from "@/components/ui/Icones";
import { useMediaQuery } from "@/hooks/useMediaQuery";
import { acordarApi, api } from "@/lib/api";
import type { Projeto } from "@/types/projeto";
import { ChipCategoria } from "@/app/forum/_componentes/Categoria";
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

/* Constelação atrás do título: estrelas ligadas por linhas, o "Connect"
   desenhado. Cada estrela é [x, y, raio], com x e y em frações da área do
   desenho; como as posições viram porcentagens, o desenho acompanha a largura
   da tela sem deformar as estrelas. As da metade direita ficam no verde do
   "Connect". Algumas estrelas cintilam devagar, cada uma no seu tempo
   (CINTILANTES: índice da estrela e atraso em segundos); quem pede menos
   movimento no sistema vê o desenho parado. */
const ESTRELAS: [number, number, number][] = [
  [0.02, 0.62, 2.6], [0.1, 0.3, 2], [0.19, 0.74, 2.2], [0.27, 0.14, 2.8], [0.36, 0.5, 1.8],
  [0.46, 0.06, 2.4], [0.55, 0.92, 2], [0.63, 0.38, 2.6], [0.72, 0.12, 2.2], [0.8, 0.72, 2],
  [0.89, 0.3, 2.8], [0.98, 0.58, 2.2], [0.32, 0.95, 1.8],
];
const LIGACOES: [number, number][] = [
  [0, 1], [1, 3], [3, 5], [5, 8], [8, 10], [10, 11], [0, 2], [2, 4],
  [4, 7], [7, 9], [9, 11], [2, 12], [12, 6], [6, 9], [3, 4], [7, 8],
];
const CINTILANTES: Record<number, number> = { 3: 0, 12: -1.7, 7: -3.1, 5: -4.4, 10: -5.6 };
const ehVerde = (i: number) => ESTRELAS[i][0] > 0.5;
const pct = (fracao: number) => `${fracao * 100}%`;

function Constelacao() {
  return (
    <svg className={styles.constelacao} aria-hidden="true" focusable="false">
      {LIGACOES.map(([a, b]) => (
        <line
          key={`${a}-${b}`}
          x1={pct(ESTRELAS[a][0])}
          y1={pct(ESTRELAS[a][1])}
          x2={pct(ESTRELAS[b][0])}
          y2={pct(ESTRELAS[b][1])}
          className={ehVerde(a) && ehVerde(b) ? styles.ligacaoVerde : styles.ligacao}
        />
      ))}
      {ESTRELAS.map(([x, y, raio], i) => (
        <g
          key={i}
          className={`${ehVerde(i) ? styles.estrelaVerde : styles.estrela} ${i in CINTILANTES ? styles.cintila : ""}`}
          style={i in CINTILANTES ? ({ "--atraso": `${CINTILANTES[i]}s` } as CSSProperties) : undefined}
        >
          <circle cx={pct(x)} cy={pct(y)} r={raio * 3.2} className={styles.estrelaHalo} />
          <circle cx={pct(x)} cy={pct(y)} r={raio} />
        </g>
      ))}
    </svg>
  );
}

function BuscaHero() {
  const router = useRouter();
  const [termo, setTermo] = useState("");
  // Em celulares o texto inteiro não cabe ao lado do botão e aparecia cortado.
  const estreito = useMediaQuery("(max-width: 480px)");

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
        placeholder={estreito ? "Tema ou coordenação" : "Busque por tema ou coordenação"}
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

/* Os passos formam uma constelação: cada número é uma estrela, e o caminho
   até o próximo passa por uma estrela menor fora da linha reta, como num mapa
   do céu. O último trecho e o passo 4 ficam no verde do "Connect". Os números
   saem um pouco do alinhamento (na vertical no desktop, na horizontal na
   lista empilhada), e os trechos partem dessas mesmas posições, em px. */
const DESVIO_Y = [12, -16, 8, -12];
const DESVIO_X = [0, 5, 0, 5];
const LADO_Y = [-22, 20, -18];
const LADO_X = [-11, 9, -11];
/** Meia altura (desktop) ou meia largura (lista) do desenho de cada trecho. */
const MEIO = 40;

function TrechoDaConstelacao({ indice: i }: { indice: number }) {
  const verde = i === PASSOS.length - 2;
  const classe = (orientacao: string) => `${styles.trecho} ${orientacao} ${verde ? styles.trechoVerde : ""}`;
  const y0 = MEIO + DESVIO_Y[i];
  const y1 = MEIO + DESVIO_Y[i + 1];
  const yMeio = (y0 + y1) / 2;
  const x0 = MEIO + DESVIO_X[i];
  const x1 = MEIO + DESVIO_X[i + 1];
  const xMeio = (x0 + x1) / 2 + LADO_X[i];

  return (
    <>
      {/* Desktop: da estrela deste passo à do próximo, na horizontal. */}
      <svg className={classe(styles.trechoHorizontal)} aria-hidden="true" focusable="false">
        <line x1="0" y1={y0} x2="50%" y2={yMeio + LADO_Y[i]} />
        <line x1="50%" y1={yMeio + LADO_Y[i]} x2="100%" y2={y1} />
        <circle cx="50%" cy={yMeio + LADO_Y[i]} r={7.8} className={styles.trechoHalo} />
        <circle cx="50%" cy={yMeio + LADO_Y[i]} r={2.6} className={styles.trechoEstrela} />
        <circle cx="50%" cy={yMeio - LADO_Y[i] * 1.4} r={1.6} transform="translate(40 0)" className={styles.trechoSolta} />
      </svg>
      {/* Lista empilhada: o mesmo trecho, na vertical. */}
      <svg className={classe(styles.trechoVertical)} aria-hidden="true" focusable="false">
        <line x1={x0} y1="0" x2={xMeio} y2="50%" />
        <line x1={xMeio} y1="50%" x2={x1} y2="100%" />
        <circle cx={xMeio} cy="50%" r={7.8} className={styles.trechoHalo} />
        <circle cx={xMeio} cy="50%" r={2.6} className={styles.trechoEstrela} />
      </svg>
    </>
  );
}

function ComoFunciona() {
  return (
    <section className={`${styles.secao} ${styles.comoFunciona}`} id="como-funciona" aria-labelledby="titulo-como">
      <div className={styles.container}>
        <CabecalhoSecao id="titulo-como" rotulo="Como funciona" titulo="Da conta à coordenação em quatro passos" />
        <ol className={styles.passos}>
          {PASSOS.map((passo, i) => (
            <li
              key={passo.titulo}
              className={styles.passo}
              style={{ "--desvio-x": `${DESVIO_X[i]}px`, "--desvio-y": `${DESVIO_Y[i]}px` } as CSSProperties}
            >
              <span className={styles.passoNumero} aria-hidden="true">
                {i + 1}
              </span>
              {i < PASSOS.length - 1 && <TrechoDaConstelacao indice={i} />}
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
  /** Símbolo da função no selo do avatar (o da função mostrada naquele slide). */
  simbolo: SimboloFuncao;
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
  {
    nome: "Lucas Eduardo Sanches Cordeiro",
    cargo: "Co-fundador e CEO",
    simbolo: "maleta",
    curso: "Medicina",
    instituicao: "UERJ",
  },
  {
    nome: "Matheus Gabriel Ramos de Melo",
    cargo: "Co-fundador e CSO",
    simbolo: "atomo",
    curso: "Medicina",
    instituicao: "UNIR",
  },
  {
    nome: "Maria Eduarda Siqueira de Medeiros",
    cargo: "Co-fundadora e CMO",
    simbolo: "megafone",
    curso: "Medicina",
    instituicao: "Afya Garanhuns",
  },
  { ...JULIANA, cargo: "Co-fundadora e CTO", simbolo: "processador" },
];

// Juliana também lidera o desenvolvimento, e Matheus coordena o produto desde
// o início (arquitetura, organização e metodologia); os dois aparecem também
// entre os fundadores.
const DESENVOLVIMENTO: Membro[] = [
  { ...JULIANA, cargo: "Head de Desenvolvimento", simbolo: "codigo" },
  {
    nome: "Matheus Gabriel Ramos de Melo",
    cargo: "Coordenador de Produto",
    simbolo: "camadas",
    curso: "Medicina",
    instituicao: "UNIR",
  },
  {
    nome: "Daniel Pereira Santos da Silva",
    cargo: "Desenvolvedor",
    simbolo: "codigo",
    curso: "Ciência da Computação",
    instituicao: "UERJ",
  },
  {
    nome: "Pedro de Magalhães Leitão",
    cargo: "Desenvolvedor",
    simbolo: "codigo",
    curso: "Ciência da Computação",
    instituicao: "UERJ",
  },
];

const ORIENTACAO: Membro[] = [
  { nome: "Prof. Dr. Carlos Eduardo Raymundo", simbolo: "livro", instituicao: "UERJ" },
  { nome: "Profa. Dra. Thayse Moraes de Moraes", simbolo: "livro", instituicao: "UEPA" },
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
            <AvatarMembro simbolo={membro.simbolo} />
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
              <ChipCategoria categoria={p.categoria} className={styles.forumCardCategoria} />
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
          <div className={styles.heroMarca}>
            <Constelacao />
            <h1 id="titulo-hero" className={styles.heroTitulo}>
              UniResu <span className={styles.heroDestaque}>Connect</span>
            </h1>
          </div>
          <p className={styles.heroTexto}>
            Uma plataforma que une alunos, professores e pesquisadores em uma rede de oportunidades,
            conhecimento e colaboração.
          </p>
          <BuscaHero />
          <p className={styles.heroRodape}>
            {numeros && (
              <>
                <span className={styles.heroNumeros}>{numeros}</span>
                <span className={`${styles.heroSeparador} ${styles.heroSeparadorNumeros}`} aria-hidden="true" />
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
