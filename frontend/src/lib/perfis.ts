/**
 * Tipos de perfil (vínculo institucional) e seus rótulos.
 *
 * Os valores são os gravados no banco (`papel`); "aluno", "professor" e
 * "pesquisador" existem desde a primeira versão, por isso continuam com
 * esses nomes internos mesmo com rótulos novos na interface.
 */

export type TipoPerfil = "aluno" | "professor" | "pesquisador" | "tecnico" | "egresso";

export interface OpcaoPerfil {
  value: TipoPerfil;
  label: string;
  descricao: string;
}

export const PERFIS: OpcaoPerfil[] = [
  { value: "aluno", label: "Discente", descricao: "Graduação ou pós-graduação (mestrado, doutorado)" },
  { value: "professor", label: "Docente", descricao: "Professor(a), orientador(a), coordenador(a) de projeto" },
  { value: "pesquisador", label: "Pesquisador(a)", descricao: "Pós-doc, colaborador(a) ou pesquisador(a) visitante" },
  { value: "tecnico", label: "Técnico(a)-administrativo(a)", descricao: "Servidor(a) técnico(a) com atuação em pesquisa ou extensão" },
  { value: "egresso", label: "Egresso(a)", descricao: "Já concluiu o curso e quer seguir conectado(a)" },
];

export const PERFIL_LABELS: Record<string, string> = Object.fromEntries(
  PERFIS.map((p) => [p.value, p.label])
);

/** Graus de instrução do discente (os mesmos valores do backend). */
export const NIVEIS = [
  { value: "graduacao_incompleta", label: "Graduação em andamento" },
  { value: "graduacao_completa", label: "Graduação completa" },
  { value: "especializacao", label: "Especialização ou residência" },
  { value: "mestrado_incompleto", label: "Mestrado em andamento" },
  { value: "mestrado_completo", label: "Mestrado completo" },
  { value: "doutorado_incompleto", label: "Doutorado em andamento" },
  { value: "doutorado_completo", label: "Doutorado completo" },
  { value: "pos_doutorado", label: "Pós-doutorado" },
];

/** Níveis em andamento: o campo numérico ao lado muda de nome e de limite. */
export const PERIODO_POR_NIVEL: Record<string, { rotulo: string; max: number }> = {
  graduacao_incompleta: { rotulo: "Período", max: 12 },
  mestrado_incompleto: { rotulo: "Semestre", max: 6 },
  doutorado_incompleto: { rotulo: "Semestre", max: 10 },
};

/** Valores da primeira versão convertidos para os atuais. */
const NIVEIS_ANTIGOS: Record<string, string> = {
  graduacao: "graduacao_incompleta",
  mestrado: "mestrado_incompleto",
  doutorado: "doutorado_incompleto",
};

export function nivelAtual(valor?: string | null) {
  if (!valor) return "graduacao_incompleta";
  return NIVEIS_ANTIGOS[valor] ?? valor;
}

/** Texto do grau de instrução com o período ou semestre, quando houver. */
export function descreverNivel(nivel?: string | null, semestre?: number | null) {
  const valor = nivelAtual(nivel);
  const rotulo = NIVEIS.find((n) => n.value === valor)?.label ?? valor;
  const periodo = PERIODO_POR_NIVEL[valor];
  return periodo && semestre ? `${rotulo}, ${semestre}º ${periodo.rotulo.toLowerCase()}` : rotulo;
}

export interface DadosTecnico {
  setor?: string | null;
  cargo?: string | null;
}

export interface DadosEgresso {
  ano_conclusao?: number | null;
  atuacao?: string | null;
}

/** Perfis que coordenam projetos (cadastram vagas e recebem candidaturas). */
export const PERFIS_COORDENADORES: TipoPerfil[] = ["professor", "pesquisador"];

/** E-mail provisório que o login via ORCID cria até a pessoa informar o institucional. */
export function emailProvisorio(email?: string | null) {
  return !!email && email.endsWith("@orcid.placeholder");
}

/** Domínios aceitos no registro (espelha a validação do backend). */
const DOMINIOS_PERMITIDOS = [
  // Federais
  "ufrj.br", "ufmg.br", "unb.br", "ufrgs.br", "ufsc.br", "ufpr.br", "ufpe.br", "ufba.br", "ufg.br",
  "ufrn.br", "ufv.br", "ufscar.br", "unifesp.br", "ufc.br", "ufu.br", "unir.br", "unirio.br",
  // Estaduais
  "usp.br", "unicamp.br", "unesp.br", "uerj.br", "udesc.br", "uems.br", "unemat.br", "uenp.br",
  // PUCs
  "pucminas.br", "puc-rio.br", "pucsp.br", "pucpr.br", "pucrs.br", "puccampinas.edu.br",
  // Privadas e institutos
  "fgv.br", "insper.edu.br", "mackenzie.br", "einstein.br", "fia.com.br", "senai.br", "itajuba.edu.br",
  "ita.br", "ime.eb.mil.br",
];

export function emailInstitucionalValido(email: string) {
  const dominio = email.split("@")[1]?.toLowerCase().trim();
  if (!dominio) return false;
  if (dominio.endsWith(".edu.br") || dominio === "edu.br" || dominio.endsWith(".edu") || dominio === "edu") {
    return true;
  }
  return DOMINIOS_PERMITIDOS.some((alvo) => dominio === alvo || dominio.endsWith("." + alvo));
}
