/**
 * Tipos TypeScript para Usuário / Perfil.
 * Espelham os Pydantic models do backend.
 */

import type { DadosEgresso, DadosTecnico, TipoPerfil } from "@/lib/perfis";

export type { DadosEgresso, DadosTecnico } from "@/lib/perfis";

/** Vínculo institucional (ver `lib/perfis.ts` para os rótulos). */
export type PapelUsuario = TipoPerfil;
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
  /** E-mail institucional informado por uma conta do ORCID e ainda não confirmado pelo link enviado. */
  email_pendente?: string | null;
  /** O e-mail pendente já tem conta por senha: ao confirmar, o ORCID é vinculado a ela. */
  email_pendente_vincula?: boolean;
  aceite_regras?: boolean;
  aceite_dados?: boolean;
  /** Identificador público (ex.: "matheus-gabriel"); é o que o fórum exibe no lugar do e-mail. */
  username?: string;
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
  dados_tecnico?: DadosTecnico;
  dados_egresso?: DadosEgresso;
  orcid?: OrcidData;
  /** False só para contas criadas pelo ORCID que ainda não passaram por /perfil/completar. */
  perfil_completo?: boolean;
  criado_em?: string;
}

export interface LoginResponse {
  access_token: string;
  token_type: string;
  usuario: User;
}
