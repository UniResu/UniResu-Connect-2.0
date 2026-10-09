/** Ícones de traço (24×24, estilo Lucide) usados na busca e no detalhe dos projetos. */

const ICONE = {
  lupa: "M19 11a8 8 0 1 1-16 0 8 8 0 0 1 16 0M21 21l-4.3-4.3",
  x: "M18 6 6 18M6 6l12 12",
  linkExterno: "M15 3h6v6M10 14 21 3M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6",
  check: "M20 6 9 17l-5-5",
  buscaVazia: "M13.5 8.5l-5 5M8.5 8.5l5 5M19 11a8 8 0 1 1-16 0 8 8 0 0 1 16 0M21 21l-4.3-4.3",
  alerta: "m21.73 18-8-14a2 2 0 0 0-3.48 0l-8 14A2 2 0 0 0 4 21h16a2 2 0 0 0 1.73-3M12 9v4M12 17h.01",
  info: "M22 12a10 10 0 1 1-20 0 10 10 0 0 1 20 0M12 16v-4M12 8h.01",
  carregando: "M21 12a9 9 0 1 1-6.22-8.56",
  repetir: "M21 12a9 9 0 1 1-9-9c2.52 0 4.93 1 6.74 2.74L21 8M21 3v5h-5",
  filtros: "M4 21v-7M4 10V3M12 21v-9M12 8V3M20 21v-5M20 12V3M1 14h6M9 8h6M17 16h6",
  seta: "m6 9 6 6 6-6",
};

export function Icone({
  nome,
  tamanho = 20,
  className = "",
}: {
  nome: keyof typeof ICONE;
  tamanho?: number;
  className?: string;
}) {
  return (
    <svg
      width={tamanho}
      height={tamanho}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
      className={className}
    >
      <path d={ICONE[nome]} />
    </svg>
  );
}
