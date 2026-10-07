import styles from "@/app/page.module.css";

/**
 * Avatar dos membros da equipe (seção "Quem somos").
 *
 * Ninguém tem foto, então o avatar é o placeholder clássico de perfil (cabeça
 * e busto em silhueta) sobre o mesmo círculo em degradê de antes, com um
 * selo pequeno no canto trazendo o símbolo da função da pessoa naquele
 * card. Tudo em SVG inline, sem dependência nova.
 */
export type FuncaoMembro = "aluno" | "dev" | "cto" | "ceo" | "cmo" | "cso" | "orientador";

const ROTULO_FUNCAO: Record<FuncaoMembro, string> = {
  aluno: "estudante",
  dev: "engenharia de software",
  cto: "tecnologia",
  ceo: "direção executiva",
  cmo: "marketing",
  cso: "ciência",
  orientador: "orientação acadêmica",
};

function IconeFuncao({ funcao }: { funcao: FuncaoMembro }) {
  // Traços no estilo Lucide/Feather (24x24, stroke 2), cor herdada do selo.
  const comum = {
    viewBox: "0 0 24 24",
    fill: "none",
    stroke: "currentColor",
    strokeWidth: 2.2,
    strokeLinecap: "round" as const,
    strokeLinejoin: "round" as const,
    "aria-hidden": true,
    focusable: false,
  };
  switch (funcao) {
    case "aluno": // capelo de formatura
      return (
        <svg {...comum}>
          <path d="M22 10 12 5 2 10l10 5 10-5z" />
          <path d="M6 12v5c3 3 9 3 12 0v-5" />
        </svg>
      );
    case "dev": // código
      return (
        <svg {...comum}>
          <polyline points="16 18 22 12 16 6" />
          <polyline points="8 6 2 12 8 18" />
        </svg>
      );
    case "cto": // processador
      return (
        <svg {...comum}>
          <rect x="5" y="5" width="14" height="14" rx="2" />
          <rect x="9.5" y="9.5" width="5" height="5" />
          <path d="M9 2v3M15 2v3M9 19v3M15 19v3M2 9h3M2 15h3M19 9h3M19 15h3" />
        </svg>
      );
    case "ceo": // maleta
      return (
        <svg {...comum}>
          <rect x="2.5" y="7" width="19" height="13" rx="2" />
          <path d="M16 7V5a2 2 0 0 0-2-2h-4a2 2 0 0 0-2 2v2" />
          <path d="M2.5 13h19" />
        </svg>
      );
    case "cmo": // megafone
      return (
        <svg {...comum}>
          <path d="m3 11 18-5v12L3 14v-3z" />
          <path d="M11.6 16.8a3 3 0 1 1-5.8-1.6" />
        </svg>
      );
    case "cso": // átomo: ciência como método, não bancada de laboratório
      return (
        <svg {...comum} strokeWidth={2}>
          <circle cx="12" cy="12" r="1.6" fill="currentColor" stroke="none" />
          <path d="M20.2 20.2c2.04-2.03.02-7.36-4.5-11.9-4.54-4.52-9.87-6.54-11.9-4.5-2.04 2.03-.02 7.36 4.5 11.9 4.54 4.52 9.87 6.54 11.9 4.5Z" />
          <path d="M15.7 15.7c4.52-4.54 6.54-9.87 4.5-11.9-2.03-2.04-7.36-.02-11.9 4.5-4.52 4.54-6.54 9.87-4.5 11.9 2.03 2.04 7.36.02 11.9-4.5Z" />
        </svg>
      );
    case "orientador": // livro aberto
      return (
        <svg {...comum}>
          <path d="M2 3h6a4 4 0 0 1 4 4v14a3 3 0 0 0-3-3H2z" />
          <path d="M22 3h-6a4 4 0 0 0-4 4v14a3 3 0 0 1 3-3h7z" />
        </svg>
      );
  }
}

export default function AvatarMembro({ nome, funcao }: { nome: string; funcao?: FuncaoMembro }) {
  const descricao = funcao ? `Avatar de ${nome}, ${ROTULO_FUNCAO[funcao]}` : `Avatar de ${nome}`;
  return (
    <div className={styles.avatarWrap} role="img" aria-label={descricao}>
      <div className={styles.avatar}>
        {/* Silhueta de perfil: cabeça e busto, cortados pelo círculo como nos
            placeholders de redes sociais. */}
        <svg className={styles.avatarPessoa} viewBox="0 0 64 64" aria-hidden="true" focusable="false">
          <circle cx="32" cy="25" r="11.5" />
          <path d="M7 68c0-15.5 11-25 25-25s25 9.5 25 25z" />
        </svg>
      </div>
      {funcao && (
        <span className={styles.avatarBadge} title={ROTULO_FUNCAO[funcao]}>
          <IconeFuncao funcao={funcao} />
        </span>
      )}
    </div>
  );
}
