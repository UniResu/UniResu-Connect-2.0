/**
 * Ícones do site, todos SVG inline no mesmo traço (24x24, stroke 2, cantos
 * redondos), herdando a cor do texto. Os primeiros são utilitários; os
 * últimos (Ufo, Planeta, Alien, Estrelas) são a identidade espacial da
 * marca, para usar com parcimônia: estados vazios, cabeçalhos de seção e
 * telas de entrada.
 */

import type { SVGProps } from "react";

type Props = SVGProps<SVGSVGElement> & { tamanho?: number };

function base({ tamanho = 20, ...resto }: Props) {
  return {
    width: tamanho,
    height: tamanho,
    viewBox: "0 0 24 24",
    fill: "none",
    stroke: "currentColor",
    strokeWidth: 2,
    strokeLinecap: "round" as const,
    strokeLinejoin: "round" as const,
    "aria-hidden": true,
    focusable: false,
    ...resto,
  };
}

export function IconeLupa(p: Props) {
  return (
    <svg {...base(p)}>
      <circle cx="11" cy="11" r="7" />
      <path d="m20 20-3.5-3.5" />
    </svg>
  );
}

export function IconeFechar(p: Props) {
  return (
    <svg {...base(p)}>
      <path d="M18 6 6 18M6 6l12 12" />
    </svg>
  );
}

export function IconeSetaEsquerda(p: Props) {
  return (
    <svg {...base(p)}>
      <path d="m15 18-6-6 6-6" />
    </svg>
  );
}

export function IconeSetaDireita(p: Props) {
  return (
    <svg {...base(p)}>
      <path d="m9 18 6-6-6-6" />
    </svg>
  );
}

export function IconeSetaCima(p: Props) {
  return (
    <svg {...base(p)}>
      <path d="m18 15-6-6-6 6" />
    </svg>
  );
}

export function IconeSetaBaixo(p: Props) {
  return (
    <svg {...base(p)}>
      <path d="m6 9 6 6 6-6" />
    </svg>
  );
}

export function IconeCalendario(p: Props) {
  return (
    <svg {...base(p)}>
      <rect x="3" y="5" width="18" height="16" rx="2" />
      <path d="M16 3v4M8 3v4M3 10h18" />
    </svg>
  );
}

export function IconeGlobo(p: Props) {
  return (
    <svg {...base(p)}>
      <circle cx="12" cy="12" r="9" />
      <path d="M3 12h18M12 3a14 14 0 0 1 0 18M12 3a14 14 0 0 0 0 18" />
    </svg>
  );
}

export function IconePin(p: Props) {
  return (
    <svg {...base(p)}>
      <path d="M12 21s-6-5.3-6-11a6 6 0 0 1 12 0c0 5.7-6 11-6 11z" />
      <circle cx="12" cy="10" r="2.5" />
    </svg>
  );
}

export function IconePredio(p: Props) {
  return (
    <svg {...base(p)}>
      <path d="M3 21h18M5 21V7l7-4 7 4v14" />
      <path d="M9 21v-5h6v5M9 11h.01M15 11h.01M9 14h.01M15 14h.01" />
    </svg>
  );
}

export function IconeLivro(p: Props) {
  return (
    <svg {...base(p)}>
      <path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20" />
      <path d="M6.5 2H20v20H6.5A2.5 2.5 0 0 1 4 19.5v-15A2.5 2.5 0 0 1 6.5 2z" />
    </svg>
  );
}

export function IconePessoas(p: Props) {
  return (
    <svg {...base(p)}>
      <path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2" />
      <circle cx="9" cy="7" r="4" />
      <path d="M23 21v-2a4 4 0 0 0-3-3.87M16 3.13a4 4 0 0 1 0 7.75" />
    </svg>
  );
}

export function IconeFrasco(p: Props) {
  return (
    <svg {...base(p)}>
      <path d="M9 3h6M10 3v6.5L4.5 19a1.5 1.5 0 0 0 1.3 2.2h12.4a1.5 1.5 0 0 0 1.3-2.2L14 9.5V3" />
      <path d="M7 16h10" />
    </svg>
  );
}

export function IconeFolha(p: Props) {
  return (
    <svg {...base(p)}>
      <path d="M20 4c-8 0-14 5-14 13 0 1 0 2 .3 3C9 16 12 12 17 10" />
      <path d="M6 20c2-7 7-11 14-16" />
    </svg>
  );
}

export function IconeBroto(p: Props) {
  return (
    <svg {...base(p)}>
      <path d="M12 21v-8" />
      <path d="M12 13c0-4-3-7-7-7 0 4 3 7 7 7z" />
      <path d="M12 10c0-3.5 2.5-6 6-6 0 3.5-2.5 6-6 6z" />
    </svg>
  );
}

export function IconeCoracao(p: Props) {
  return (
    <svg {...base(p)}>
      <path d="M20.8 4.6a5.5 5.5 0 0 0-7.8 0L12 5.6l-1-1a5.5 5.5 0 0 0-7.8 7.8l1 1L12 21l7.8-7.6 1-1a5.5 5.5 0 0 0 0-7.8z" />
    </svg>
  );
}

export function IconeEngrenagem(p: Props) {
  return (
    <svg {...base(p)}>
      <circle cx="12" cy="12" r="3" />
      <path d="M19.4 15a1.7 1.7 0 0 0 .3 1.8l.1.1a2 2 0 1 1-2.8 2.8l-.1-.1a1.7 1.7 0 0 0-1.8-.3 1.7 1.7 0 0 0-1 1.5V21a2 2 0 1 1-4 0v-.1a1.7 1.7 0 0 0-1.1-1.5 1.7 1.7 0 0 0-1.8.3l-.1.1a2 2 0 1 1-2.8-2.8l.1-.1a1.7 1.7 0 0 0 .3-1.8 1.7 1.7 0 0 0-1.5-1H3a2 2 0 1 1 0-4h.1a1.7 1.7 0 0 0 1.5-1.1 1.7 1.7 0 0 0-.3-1.8l-.1-.1a2 2 0 1 1 2.8-2.8l.1.1a1.7 1.7 0 0 0 1.8.3H9a1.7 1.7 0 0 0 1-1.5V3a2 2 0 1 1 4 0v.1a1.7 1.7 0 0 0 1 1.5 1.7 1.7 0 0 0 1.8-.3l.1-.1a2 2 0 1 1 2.8 2.8l-.1.1a1.7 1.7 0 0 0-.3 1.8V9a1.7 1.7 0 0 0 1.5 1H21a2 2 0 1 1 0 4h-.1a1.7 1.7 0 0 0-1.5 1z" />
    </svg>
  );
}

export function IconeBalanca(p: Props) {
  return (
    <svg {...base(p)}>
      <path d="M12 3v18M5 21h14M3 7h18" />
      <path d="M7 7 3.5 14a3.5 3.5 0 0 0 7 0L7 7zM17 7l-3.5 7a3.5 3.5 0 0 0 7 0L17 7z" />
    </svg>
  );
}

export function IconePaleta(p: Props) {
  return (
    <svg {...base(p)}>
      <path d="M12 3a9 9 0 1 0 0 18c1.2 0 2-.9 2-2 0-.6-.2-1-.5-1.4-.3-.4-.5-.8-.5-1.3 0-1 .9-1.8 2-1.8h2.2A4.8 4.8 0 0 0 22 10c0-4-4.5-7-10-7z" />
      <circle cx="7.5" cy="11.5" r="1" /><circle cx="10.5" cy="7.5" r="1" /><circle cx="15" cy="7.5" r="1" />
    </svg>
  );
}

export function IconeGrade(p: Props) {
  return (
    <svg {...base(p)}>
      <rect x="3" y="3" width="7" height="7" rx="1.5" /><rect x="14" y="3" width="7" height="7" rx="1.5" />
      <rect x="3" y="14" width="7" height="7" rx="1.5" /><rect x="14" y="14" width="7" height="7" rx="1.5" />
    </svg>
  );
}

export function IconeLinkExterno(p: Props) {
  return (
    <svg {...base(p)}>
      <path d="M14 4h6v6M20 4l-9 9" />
      <path d="M19 14v5a1 1 0 0 1-1 1H5a1 1 0 0 1-1-1V6a1 1 0 0 1 1-1h5" />
    </svg>
  );
}

export function IconeCheck(p: Props) {
  return (
    <svg {...base(p)}>
      <path d="m5 12 5 5L20 7" />
    </svg>
  );
}

export function IconeInfo(p: Props) {
  return (
    <svg {...base(p)}>
      <circle cx="12" cy="12" r="9" />
      <path d="M12 16v-5M12 8h.01" />
    </svg>
  );
}

export function IconeMensagem(p: Props) {
  return (
    <svg {...base(p)}>
      <path d="M21 12a8 8 0 0 1-8 8H7l-4 3V12a8 8 0 0 1 8-8h2a8 8 0 0 1 8 8z" />
    </svg>
  );
}

export function IconeEnvelope(p: Props) {
  return (
    <svg {...base(p)}>
      <rect x="3" y="5" width="18" height="14" rx="2" />
      <path d="m3 7 9 6 9-6" />
    </svg>
  );
}

/* ── Vínculos (registro de conta) ── */

export function IconeCapelo(p: Props) {
  return (
    <svg {...base(p)}>
      <path d="M22 10 12 5 2 10l10 5 10-5z" />
      <path d="M6 12v5c3 3 9 3 12 0v-5" />
      <path d="M22 10v6" />
    </svg>
  );
}

export function IconeQuadro(p: Props) {
  return (
    <svg {...base(p)}>
      <path d="M3 4h18" />
      <path d="M4 4v10a1 1 0 0 0 1 1h14a1 1 0 0 0 1-1V4" />
      <path d="M8 9h5M8 12h8" />
      <path d="M12 15v3M8 21l4-3 4 3" />
    </svg>
  );
}

export function IconeMicroscopio(p: Props) {
  return (
    <svg {...base(p)}>
      <path d="M6 18h8M3 22h18" />
      <path d="M14 22a7 7 0 1 0 0-14h-1" />
      <path d="M9 14h2" />
      <path d="M9 12a2 2 0 0 1-2-2V6h6v4a2 2 0 0 1-2 2Z" />
      <path d="M12 6V3a1 1 0 0 0-1-1H9a1 1 0 0 0-1 1v3" />
    </svg>
  );
}

export function IconeMaleta(p: Props) {
  return (
    <svg {...base(p)}>
      <rect x="2.5" y="7" width="19" height="13" rx="2" />
      <path d="M16 7V5a2 2 0 0 0-2-2h-4a2 2 0 0 0-2 2v2" />
      <path d="M2.5 13h19M11 13v2h2v-2" />
    </svg>
  );
}

export function IconeDiploma(p: Props) {
  return (
    <svg {...base(p)}>
      <path d="M14 18H5a2 2 0 0 1-2-2V6a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2v5" />
      <path d="M7 8h10M7 11.5h6" />
      <circle cx="18" cy="15" r="2.5" />
      <path d="m16.5 17-.5 4.5 2-1.2 2 1.2-.5-4.5" />
    </svg>
  );
}

/** Ícone do tipo de vínculo (os mesmos valores de `papel` do backend). */
export function IconeVinculo({ papel, ...p }: Props & { papel: string }) {
  switch (papel) {
    case "aluno":
      return <IconeCapelo {...p} />;
    case "professor":
      return <IconeQuadro {...p} />;
    case "pesquisador":
      return <IconeMicroscopio {...p} />;
    case "tecnico":
      return <IconeMaleta {...p} />;
    case "egresso":
      return <IconeDiploma {...p} />;
    default:
      return <IconePessoas {...p} />;
  }
}

/* ── Identidade espacial ── */

export function IconeUfo(p: Props) {
  return (
    <svg {...base(p)}>
      <path d="M8.5 10.5a3.5 3.5 0 0 1 7 0" />
      <ellipse cx="12" cy="13" rx="9" ry="3" />
      <path d="M7 15.5 5.5 19M17 15.5l1.5 3.5M12 16v3" />
      <path d="M9 13h.01M12 13.5h.01M15 13h.01" />
    </svg>
  );
}

/* Variações do disco voador para o fórum: a nave subindo (voto a favor), a
   nave com o feixe descendo (voto contra) e a nave transmitindo (respostas).
   O domo se apoia exatamente na borda de cima do disco, para o desenho não
   embolar em 14 a 22px. */

export function IconeNaveSobe(p: Props) {
  return (
    <svg {...base(p)}>
      <path d="m8.5 6.5 3.5-3.5 3.5 3.5" />
      <path d="M8 14.31a4 4 0 0 1 8 0" />
      <ellipse cx="12" cy="17" rx="9" ry="3" />
      <path d="M8 17.2h.01M12 17.6h.01M16 17.2h.01" />
    </svg>
  );
}

export function IconeNaveDesce(p: Props) {
  return (
    <svg {...base(p)}>
      <path d="M8 4.81a4 4 0 0 1 8 0" />
      <ellipse cx="12" cy="7.5" rx="9" ry="3" />
      <path d="M8.5 11 6.5 17M15.5 11l2 6" />
      <path d="m9.5 16.5 2.5 2.5 2.5-2.5" />
    </svg>
  );
}

export function IconeNaveTransmite(p: Props) {
  return (
    <svg {...base(p)}>
      <path d="M6.5 14.24a3 3 0 0 1 6 0" />
      <ellipse cx="9.5" cy="16.5" rx="7" ry="2.5" />
      <path d="M15.5 9.5a3 3 0 0 1 3 3" />
      <path d="M15.5 5.5a7 7 0 0 1 7 7" />
    </svg>
  );
}

export function IconePlaneta(p: Props) {
  return (
    <svg {...base(p)}>
      <circle cx="12" cy="12" r="5.5" />
      <path d="M4.2 9.6c-2 1.6-2.7 3.2-1.9 4.3 1.3 1.9 7 1 12.7-2s9.4-6.7 8.1-8.6c-.7-1-2.2-1.1-4.2-.5" />
    </svg>
  );
}

export function IconeAlien(p: Props) {
  return (
    <svg {...base(p)}>
      <path d="M12 3c4.4 0 7.5 3.3 7.5 7.5 0 4.6-4 10.5-7.5 10.5S4.5 15.1 4.5 10.5C4.5 6.3 7.6 3 12 3z" />
      <path d="M8 11.5c1.5-.4 2.4.3 2.6 1.8-1.6.4-2.5-.3-2.6-1.8zM16 11.5c-1.5-.4-2.4.3-2.6 1.8 1.6.4 2.5-.3 2.6-1.8z" />
    </svg>
  );
}

export function IconeEstrelas(p: Props) {
  return (
    <svg {...base(p)}>
      <path d="M12 3l1.8 4.6L18.5 9l-4.7 1.5L12 15l-1.8-4.5L5.5 9l4.7-1.4z" />
      <path d="M19 15l.8 2 2 .8-2 .8-.8 2-.8-2-2-.8 2-.8zM5 16l.6 1.4 1.4.6-1.4.6L5 20l-.6-1.4L3 18l1.4-.6z" />
    </svg>
  );
}

export function IconeFoguete(p: Props) {
  return (
    <svg {...base(p)}>
      <path d="M5 15c-1.5 1.5-2 5-2 5s3.5-.5 5-2" />
      <path d="M9 15 5.5 11.5C7 7 11 3 20 3c0 9-4 13-8.5 14.5L9 15z" />
      <path d="M14.5 9.5a1.5 1.5 0 1 0 0 .01" />
    </svg>
  );
}
