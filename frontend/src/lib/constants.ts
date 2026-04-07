/** Constantes da aplicação. */

export const APP_NAME = "UniResu Connect";
export const APP_DESCRIPTION = "Conectando a Comunidade Acadêmica";

export const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

/** Chave do token no localStorage */
export const TOKEN_KEY = "uniresu_token";

/** Mapear nível acadêmico para label amigável */
export const NIVEL_LABELS: Record<string, string> = {
  graduacao: "Graduando",
  mestrado: "Mestrando",
  doutorado: "Doutorando",
};

/** Mapear papel para label */
export const PAPEL_LABELS: Record<string, string> = {
  aluno: "Aluno",
  professor: "Professor",
  pesquisador: "Pesquisador",
};

/** Cores temáticas por papel */
export const PAPEL_COLORS: Record<string, string> = {
  aluno: "#7c3aed",
  professor: "#059669",
  pesquisador: "#2563eb",
};
