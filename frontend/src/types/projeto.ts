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
  /** Extensão no SIGAA: "Nº Bolsas Concedidas" da ação (só o número, nada sobre quem recebe). */
  bolsas_alunos?: number | null;
  /** Extensão no SIGAA: FINANCIAMENTO INTERNO, FINANCIAMENTO EXTERNO ou AÇÃO AUTO-FINANCIADA. */
  fonte_financiamento?: string | null;
  /** Quem financia: "capes", "cnpq", "fap", "fap:<SIGLA>" e "instituicao". */
  financiadores?: string[] | null;
}

/** Opções do filtro "Projetos financiados", na ordem em que aparecem. */
export const ROTULOS_FINANCIAMENTO: Record<string, string> = {
  bolsa: "Bolsa para alunos",
  capes: "CAPES",
  cnpq: "CNPq",
  fap: "FAP",
  instituicao: "Própria universidade",
};

export const PREFIXO_FAP = "fap:";

export function rotuloFinanciamento(valor: string) {
  return valor.startsWith(PREFIXO_FAP) ? valor.slice(PREFIXO_FAP.length) : ROTULOS_FINANCIAMENTO[valor] ?? valor;
}

/** Quem financia o projeto, para exibir: as FAPs pelo nome, no lugar de "FAP". */
export function financiadoresDoProjeto(projeto: Projeto): string[] {
  const lista = projeto.financiadores || [];
  const ordem = ["capes", "cnpq", "instituicao", "fap"];
  const faps = lista.filter((v) => v.startsWith(PREFIXO_FAP)).sort();
  const rotulos: string[] = [];
  for (const valor of ordem) {
    if (!lista.includes(valor)) continue;
    if (valor === "fap" && faps.length > 0) rotulos.push(...faps.map(rotuloFinanciamento));
    else rotulos.push(rotuloFinanciamento(valor));
  }
  return rotulos;
}

/** "3 bolsas para alunos" (ou nada, quando a fonte não informa bolsa concedida). */
export function textoBolsas(projeto: Projeto) {
  const n = projeto.bolsas_alunos ?? 0;
  if (n <= 0) return "";
  return n === 1 ? "1 bolsa para alunos" : `${n} bolsas para alunos`;
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
