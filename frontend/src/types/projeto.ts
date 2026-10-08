/**
 * Projeto como a API pública devolve em /api/projetos/buscar, mais os
 * ajudantes de apresentação usados pelo card e pelo modal.
 */

export interface Projeto {
  id: string;
  titulo: string;
  descricao?: string;
  instituicao?: string;
  tipo?: string;
  dataPublicacao?: string;
  local?: string;
  area_estudo?: string;
  /** Grande área do CNPq em que o projeto foi classificado. */
  area_conhecimento?: string;
  e_remoto?: boolean;
  modalidade?: string;
  nome_professor?: string;
  /** Extensão no SIGAA: quem assina como responsável pela ação (pode ser discente). */
  responsavel_acao?: string;
  tem_contato: boolean;
  /** Projetos importados de fontes externas (SIGAA das universidades, portais da UNIRIO, dados abertos da UFV). */
  origem?: "sigaa" | "unirio" | "ufv" | "puccamp" | string;
  modulo?: "pesquisa" | "extensao";
  tipo_sigaa?: "pesquisa" | "extensao";
  codigo?: string;
  unidade?: string;
  /** Campus deduzido da unidade (ver backend/services/campi.py). */
  campus?: string;
  situacao?: string;
  ano?: string;
  categoria?: string;
  link_detalhe?: string;
  /** Consulta pública do SIGAA da instituição, quando o projeto não tem página própria (pesquisa). */
  link_consulta?: string;
  periodo_inicio?: string;
  periodo_fim?: string;
  area_tematica?: string;
  palavras_chave?: string[];
  linhas_extensao?: string[];
  grupo_pesquisa?: string;
  financiamento?: string;
}

export type SituacaoTom = "ativa" | "encerrada" | "futura" | "neutra";

export function moduloDoProjeto(projeto: Projeto) {
  return projeto.modulo || projeto.tipo_sigaa;
}

export function formatarData(iso?: string) {
  if (!iso) return "";
  const [ano, mes, dia] = iso.slice(0, 10).split("-");
  return `${dia}/${mes}/${ano}`;
}

/** "EM EXECUÇÃO" vira "Em execução" (os portais publicam tudo em caixa alta). */
export function formatarSituacao(situacao?: string) {
  if (!situacao) return "";
  const s = situacao.trim();
  if (s !== s.toUpperCase()) return s;
  return s.charAt(0) + s.slice(1).toLowerCase();
}

export function tomDaSituacao(situacao?: string): SituacaoTom {
  const s = (situacao || "").toUpperCase();
  if (!s) return "neutra";
  if (s.includes("EXECU") || s.includes("ANDAMENTO")) return "ativa";
  if (s.includes("NÃO INICIADO") || s.includes("NAO INICIADO")) return "futura";
  if (s.includes("FINALIZ") || s.includes("CONCLU") || s.includes("ENCERR")) return "encerrada";
  return "neutra";
}
