import styles from "./AvatarMembro.module.css";

/* Partículas e títulos que não entram nas iniciais ("Pedro de Magalhães
   Leitão" vira "PL"; "Prof. Dr. Carlos Eduardo Raymundo" vira "CR"). */
const PARTICULAS = new Set(["de", "da", "do", "das", "dos", "e"]);
const TITULOS = /^(prof|profa|dr|dra|me|ma|msc|phd)\.?$/i;

/** Primeira letra do primeiro e do último nome, sem títulos nem partículas. */
export function iniciaisDoNome(nome: string): string {
  const partes = nome
    .trim()
    .split(/\s+/)
    .filter((parte) => parte && !TITULOS.test(parte) && !PARTICULAS.has(parte.toLowerCase()));
  if (partes.length === 0) return "";
  const primeira = partes[0].charAt(0);
  const ultima = partes.length > 1 ? partes[partes.length - 1].charAt(0) : "";
  return (primeira + ultima).toLocaleUpperCase("pt-BR");
}

/**
 * Avatar dos membros da equipe (seção "Quem somos").
 *
 * Ninguém tem foto, então o avatar mostra as iniciais sobre uma pílula em
 * degradê de marca. É decorativo para leitores de tela: o nome e o cargo já
 * estão no texto logo abaixo, e anunciar o avatar repetiria tudo.
 */
export default function AvatarMembro({ nome }: { nome: string }) {
  return (
    <span className={styles.avatar} aria-hidden="true">
      {iniciaisDoNome(nome)}
    </span>
  );
}
