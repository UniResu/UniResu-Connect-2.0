/**
 * Tipos e funções puras do fórum, usados pela lista (/forum) e pela página
 * de cada pergunta (/forum/[id]). A pasta começa com "_" para ficar fora do
 * roteamento do App Router.
 */

import type { User } from "@/types/user";

// ── Tipos ─────────────────────────────────────────────────────────────────

export interface Resposta {
  id: string;
  topico_id: string;
  conteudo: string;
  autor_id?: string | null;
  autor_username?: string | null;
  autor_nome?: string | null;
  data_criacao: string;
  editado_em?: string | null;
}

export interface Topico {
  id: string;
  titulo: string;
  conteudo_original?: string;
  descricao?: string; // campo legado: fallback de leitura apenas
  autor_id?: string | null;
  autor_username?: string | null;
  autor_nome?: string | null;
  data_criacao: string;
  visualizacoes: number;
  likes: string[]; // IDs de usuários
  dislikes: string[]; // IDs de usuários
  total_respostas: number;
  /** Primeira pergunta de quem escreveu: mostra o selo "Primeiro contato". */
  primeira_do_autor?: boolean;
  /** Só no GET de um tópico: as primeiras respostas, da mais antiga para a mais nova. */
  respostas?: Resposta[];
}

/** Uma página de GET /api/forum/topicos/{id}/respostas. */
export interface PaginaRespostas {
  total: number;
  respostas: Resposta[];
}

/** Respostas carregadas de um tópico e o total que existe no servidor. */
export interface EstadoRespostas {
  respostas: Resposta[];
  total: number;
}

export type TipoVoto = "like" | "dislike";

/** A thread aberta em /forum mostra no máximo estas respostas. */
export const RESPOSTAS_NA_THREAD = 10;
/** A página da pergunta carrega as respostas em blocos deste tamanho. */
export const RESPOSTAS_POR_PAGINA = 50;
/** Mesmo limite do backend (contado depois de tirar os espaços das pontas). */
export const RESPOSTA_MAX_CARACTERES = 5000;

// ── Funções puras ─────────────────────────────────────────────────────────

export function conteudoDe(topico: Topico) {
  return topico.conteudo_original || topico.descricao || "";
}

export function votosDe(topico: Topico) {
  return topico.likes.length - topico.dislikes.length;
}

/** Autoria somente por id: o e-mail não existe na resposta da API. */
export function ehAutor(doc: { autor_id?: string | null }, user: User | null) {
  return !!user && !!doc.autor_id && doc.autor_id === user.id;
}

/** Datas sem fuso vêm do Mongo em UTC; sem o "Z" o navegador leria como hora local. */
export function parsearData(iso: string) {
  const temFuso = /(Z|[+-]\d{2}:?\d{2})$/.test(iso);
  return new Date(temFuso ? iso : `${iso}Z`);
}

export function plural(n: number, singular: string, pluralForm: string) {
  return `${n} ${Math.abs(n) === 1 ? singular : pluralForm}`;
}

export function tempoRelativo(iso: string, agora = Date.now()) {
  const t = parsearData(iso).getTime();
  if (Number.isNaN(t)) return "";
  const seg = Math.max(0, Math.round((agora - t) / 1000));
  if (seg < 60) return "agora";
  const min = Math.round(seg / 60);
  if (min < 60) return `há ${min} min`;
  const h = Math.round(min / 60);
  if (h < 24) return `há ${h} h`;
  const d = Math.round(h / 24);
  if (d < 30) return `há ${plural(d, "dia", "dias")}`;
  const m = Math.round(d / 30);
  if (m < 12) return `há ${plural(m, "mês", "meses")}`;
  return `há ${plural(Math.round(d / 365), "ano", "anos")}`;
}

export function dataCompleta(iso: string) {
  const d = parsearData(iso);
  if (Number.isNaN(d.getTime())) return "";
  return d.toLocaleString("pt-BR", { dateStyle: "long", timeStyle: "short" });
}

/** Letra do avatar: a primeira do nome ou, sem nome, do username ("U" para autor desconhecido). */
export function inicialDe(nome?: string | null, username?: string | null) {
  const base = (nome || username || "").trim();
  return base ? base.charAt(0).toUpperCase() : "U";
}

/** Parágrafos separados por linha em branco; quebras simples ficam dentro do <p>. */
export function paragrafos(texto: string) {
  return texto
    .split(/\n\s*\n/)
    .map((p) => p.trim())
    .filter(Boolean);
}

/**
 * Mesma lógica de toggle do backend, aplicada localmente para a atualização
 * otimista: repetir o voto remove; votar o oposto troca.
 */
export function aplicarVotoLocal(topico: Topico, usuarioId: string, tipo: TipoVoto): Topico {
  const tinhaLike = topico.likes.includes(usuarioId);
  const tinhaDislike = topico.dislikes.includes(usuarioId);
  const likes = topico.likes.filter((id) => id !== usuarioId);
  const dislikes = topico.dislikes.filter((id) => id !== usuarioId);
  if (tipo === "like" && !tinhaLike) likes.push(usuarioId);
  if (tipo === "dislike" && !tinhaDislike) dislikes.push(usuarioId);
  return { ...topico, likes, dislikes };
}

export function mensagemDeErro(err: unknown, padrao: string) {
  const detail = (err as { detail?: unknown })?.detail;
  return typeof detail === "string" && detail ? detail : padrao;
}

/** Status HTTP de um erro lançado por `api` (lib/api.ts), quando houver. */
export function statusDoErro(err: unknown) {
  const status = (err as { status?: unknown })?.status;
  return typeof status === "number" ? status : 0;
}

/** Junta uma página nova às respostas já carregadas sem repetir nenhuma. */
export function juntarRespostas(atuais: Resposta[], novas: Resposta[]) {
  const vistas = new Set(atuais.map((r) => r.id));
  return [...atuais, ...novas.filter((r) => !vistas.has(r.id))];
}
