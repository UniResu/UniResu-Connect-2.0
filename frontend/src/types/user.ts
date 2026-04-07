/**
 * Tipos TypeScript para Usuário / Perfil.
 * Espelham os Pydantic models do backend.
 */

export type PapelUsuario = "aluno" | "professor" | "pesquisador";
export type NivelAcademico = "graduacao" | "mestrado" | "doutorado";

export interface DadosAluno {
  nivel: NivelAcademico;
  semestre: number;
  orientador?: string;
  linha_pesquisa?: string;
}

export interface DadosProfessor {
  titulo?: string;
  cargo?: string;
  linhas_pesquisa: string[];
  laboratorio?: string;
}

export interface DadosPesquisador {
  titulo?: string;
  vinculo?: string;
  linhas_pesquisa: string[];
  grupo_pesquisa?: string;
}

export interface OrcidPublicacao {
  titulo: string;
  doi?: string;
  ano?: number;
  tipo?: string;
}

export interface OrcidEducacao {
  instituicao: string;
  grau?: string;
  area?: string;
  inicio?: number;
  fim?: number;
}

export interface OrcidData {
  orcid_id: string;
  nome_orcid?: string;
  afiliacao_orcid?: string;
  perfil_sincronizado_em?: string;
  publicacoes: OrcidPublicacao[];
  educacao: OrcidEducacao[];
}

export interface User {
  id: string;
  email: string;
  nome: string;
  nome_social?: string;
  avatar_url?: string;
  bio?: string;
  papel: PapelUsuario;
  instituicao?: string;
  curso?: string;
  departamento?: string;
  interesses: string[];
  habilidades: string[];
  dados_aluno?: DadosAluno;
  dados_professor?: DadosProfessor;
  dados_pesquisador?: DadosPesquisador;
  orcid?: OrcidData;
  criado_em?: string;
}

export interface LoginResponse {
  access_token: string;
  token_type: string;
  usuario: User;
}
