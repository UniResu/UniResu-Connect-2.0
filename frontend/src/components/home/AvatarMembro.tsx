import { useId } from "react";
import styles from "./AvatarMembro.module.css";

/** Símbolo da função de cada pessoa, em verde no canto do avatar. */
export type SimboloFuncao = "maleta" | "atomo" | "megafone" | "processador" | "codigo" | "camadas" | "livro";

/* Traços no estilo Lucide (24×24, traço 2), como os outros ícones do site. */
const SIMBOLOS: Record<SimboloFuncao, React.ReactNode> = {
  // CEO
  maleta: (
    <>
      <rect x="2.5" y="7" width="19" height="13" rx="2" />
      <path d="M16 7V5a2 2 0 0 0-2-2h-4a2 2 0 0 0-2 2v2" />
      <path d="M2.5 13h19" />
    </>
  ),
  // CSO: o átomo, para a ciência não ser lida como laboratório de bancada
  atomo: (
    <>
      <circle cx="12" cy="12" r="1" />
      <path d="M20.2 20.2c2.04-2.03.02-7.36-4.5-11.9-4.54-4.52-9.87-6.54-11.9-4.5-2.04 2.03-.02 7.36 4.5 11.9 4.54 4.52 9.87 6.54 11.9 4.5Z" />
      <path d="M15.7 15.7c4.52-4.54 6.54-9.87 4.5-11.9-2.03-2.04-7.36-.02-11.9 4.5-4.52 4.54-6.54 9.87-4.5 11.9 2.03 2.04 7.36.02 11.9-4.5Z" />
    </>
  ),
  // CMO
  megafone: (
    <>
      <path d="m3 11 18-5v12L3 14v-3z" />
      <path d="M11.6 16.8a3 3 0 1 1-5.8-1.6" />
    </>
  ),
  // CTO
  processador: (
    <>
      <rect x="5" y="5" width="14" height="14" rx="2" />
      <rect x="9" y="9" width="6" height="6" />
      <path d="M9 2v3M15 2v3M9 19v3M15 19v3M2 9h3M2 15h3M19 9h3M19 15h3" />
    </>
  ),
  // Desenvolvimento
  codigo: (
    <>
      <path d="m16 18 6-6-6-6" />
      <path d="m8 6-6 6 6 6" />
    </>
  ),
  // Coordenação de produto: arquitetura e organização em camadas
  camadas: (
    <>
      <path d="m12 2 10 5-10 5L2 7l10-5z" />
      <path d="m2 17 10 5 10-5" />
      <path d="m2 12 10 5 10-5" />
    </>
  ),
  // Orientação
  livro: (
    <>
      <path d="M2 4h6a4 4 0 0 1 4 4v13a3 3 0 0 0-3-3H2z" />
      <path d="M22 4h-6a4 4 0 0 0-4 4v13a3 3 0 0 1 3-3h7z" />
    </>
  ),
};

/**
 * Avatar dos membros da equipe (seção "Quem somos").
 *
 * Ninguém tem foto: o avatar é a cabeça do alienígena da marca (o mesmo
 * degradê lilás do logo, com as órbitas dos olhos e as antenas) e, no canto,
 * o símbolo da função em verde, solto, sem moldura. É decorativo para
 * leitores de tela: o nome e o cargo já estão no texto logo abaixo.
 */
export default function AvatarMembro({ simbolo }: { simbolo: SimboloFuncao }) {
  // Id próprio do degradê em cada avatar: vários na mesma página não podem
  // repetir o mesmo id.
  const degrade = `alien-${useId().replace(/[^a-zA-Z0-9]/g, "")}`;
  return (
    <span className={styles.avatar} aria-hidden="true">
      <svg className={styles.alien} viewBox="0 0 64 64">
        <defs>
          <linearGradient id={degrade} x1="0" y1="0" x2="0" y2="1">
            <stop offset="0" stopColor="#9a6fe0" />
            <stop offset="1" stopColor="#e6a0dc" />
          </linearGradient>
        </defs>
        <g className={styles.antenas}>
          <path
            d="M25.5 16C24.5 10.5 21.8 7 18.5 5.5M38.5 16C39.5 10.5 42.2 7 45.5 5.5"
            fill="none"
            stroke="currentColor"
            strokeWidth="2.4"
            strokeLinecap="round"
          />
          <circle cx="18.2" cy="5.4" r="2" fill="currentColor" />
          <circle cx="45.8" cy="5.4" r="2" fill="currentColor" />
        </g>
        <path
          d="M32 14c11.2 0 19.5 7.7 19.5 17.6C51.5 43.3 40.7 56 32 56S12.5 43.3 12.5 31.6C12.5 21.7 20.8 14 32 14z"
          fill={`url(#${degrade})`}
        />
        <ellipse cx="24.3" cy="35" rx="6.6" ry="4.1" transform="rotate(28 24.3 35)" fill="#2b0a3d" />
        <ellipse cx="39.7" cy="35" rx="6.6" ry="4.1" transform="rotate(-28 39.7 35)" fill="#2b0a3d" />
      </svg>
      <svg
        className={styles.simbolo}
        viewBox="0 0 24 24"
        fill="none"
        stroke="currentColor"
        strokeWidth="2.2"
        strokeLinecap="round"
        strokeLinejoin="round"
      >
        {SIMBOLOS[simbolo]}
      </svg>
    </span>
  );
}
