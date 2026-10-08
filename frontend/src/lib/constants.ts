/** Constantes da aplicação. */

export const APP_NAME = "UniResu Connect";
export const APP_DESCRIPTION = "Conectando a Comunidade Acadêmica";

export const API_URL = process.env.NEXT_PUBLIC_API_URL || "https://api.uniresu.org";

/** E-mail de contato e suporte da equipe (aparece no rodapé e no código de conduta). */
export const EMAIL_CONTATO = "uniresuconnect@gmail.com";

/** Chave do token no localStorage */
export const TOKEN_KEY = "uniresu_token";

/** Mapear nível acadêmico para label amigável */
export const NIVEL_LABELS: Record<string, string> = {
  graduacao_incompleta: "Graduação em andamento",
  graduacao_completa: "Graduação completa",
  especializacao: "Especialização ou residência",
  mestrado_incompleto: "Mestrado em andamento",
  mestrado_completo: "Mestrado completo",
  doutorado_incompleto: "Doutorado em andamento",
  doutorado_completo: "Doutorado completo",
  pos_doutorado: "Pós-doutorado",
  // valores da primeira versão, ainda possíveis em contas antigas
  graduacao: "Graduação em andamento",
  mestrado: "Mestrado em andamento",
  doutorado: "Doutorado em andamento",
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
