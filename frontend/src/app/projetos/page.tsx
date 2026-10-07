"use client";

import { useState, useEffect, useCallback, useRef } from "react";
import { useRouter } from "next/navigation";
import { api } from "@/lib/api";
import { useAuth } from "@/contexts/AuthContext";
import type { User } from "@/types/user";
import styles from "./projetos.module.css";
import modalStyles from "./modal.module.css";

interface Projeto {
  id: string;
  titulo: string;
  descricao?: string;
  instituicao?: string;
  tipo?: string;
  dataPublicacao?: string;
  local?: string;
  area_estudo?: string;
  e_remoto?: boolean;
  modalidade?: string;
  nome_professor?: string;
  tem_contato: boolean;
  // Projetos importados de fontes externas (SIGAA/UNIR, portais da UNIRIO)
  origem?: "sigaa" | "unirio" | string;
  modulo?: "pesquisa" | "extensao";
  tipo_sigaa?: "pesquisa" | "extensao";
  codigo?: string;
  unidade?: string;
  situacao?: string;
  ano?: string;
  categoria?: string;
  link_detalhe?: string;
  periodo_inicio?: string;
  periodo_fim?: string;
  area_tematica?: string;
  palavras_chave?: string[];
  linhas_extensao?: string[];
  grupo_pesquisa?: string;
  financiamento?: string;
}

interface UnidadeFiltro {
  nome: string;
  total: number;
  modulos: Record<string, number>;
}

interface InstituicaoFiltro {
  sigla: string;
  rotulo: string | null;
  externa: boolean;
  total: number;
  modulos: Record<string, number>;
  unidades: UnidadeFiltro[];
}

/** Unidades de uma instituição que têm projetos no módulo escolhido (ou em qualquer um). */
function unidadesVisiveis(inst: InstituicaoFiltro, modulo: string) {
  return inst.unidades.filter((u) => !modulo || (u.modulos[modulo] || 0) > 0);
}

/** Nome da fonte externa, para rótulos como "Ver no SIGAA". */
const FONTE_NOME: Record<string, string> = {
  sigaa: "SIGAA",
  unirio: "Portal da UNIRIO",
  ufv: "sistema de extensão da UFV",
};

const PAGE_SIZE = 20;
const CARTA_MIN = 300;
const CARTA_MAX = 5000;

const CARTA_PLACEHOLDER = `Quem sou: curso, período e o que já estudei ou fiz que tem relação com o projeto.

Por que este projeto: o que me interessa nele e como posso contribuir.

Disponibilidade: quantas horas por semana, em quais turnos e a partir de quando.`;

function formatarData(iso?: string) {
  if (!iso) return "";
  const [ano, mes, dia] = iso.slice(0, 10).split("-");
  return `${dia}/${mes}/${ano}`;
}

/** "EM EXECUÇÃO" → "Em execução" (os portais publicam tudo em caixa alta). */
function formatarSituacao(situacao?: string) {
  if (!situacao) return "";
  const s = situacao.trim();
  if (s !== s.toUpperCase()) return s;
  return s.charAt(0) + s.slice(1).toLowerCase();
}

type SituacaoTom = "ativa" | "encerrada" | "futura" | "neutra";

function tomDaSituacao(situacao?: string): SituacaoTom {
  const s = (situacao || "").toUpperCase();
  if (!s) return "neutra";
  if (s.includes("EXECU") || s.includes("ANDAMENTO")) return "ativa";
  if (s.includes("NÃO INICIADO") || s.includes("NAO INICIADO")) return "futura";
  if (s.includes("FINALIZ") || s.includes("CONCLU") || s.includes("ENCERR")) return "encerrada";
  return "neutra";
}

function moduloDoProjeto(projeto: Projeto) {
  return projeto.modulo || projeto.tipo_sigaa;
}

function cursoPeriodoDoUsuario(user: User | null) {
  if (!user?.curso) return "";
  const semestre = user.dados_aluno?.semestre;
  return semestre ? `${user.curso} — ${semestre}º período` : user.curso;
}

/** Converte o `detail` da API (string ou lista de erros do FastAPI) em texto. */
function mensagemDeErro(detail: unknown, padrao: string) {
  if (typeof detail === "string") return detail;
  if (Array.isArray(detail)) {
    return detail
      .map((d: { msg?: string }) => (d.msg || "").replace(/^Value error, /, ""))
      .filter(Boolean)
      .join(" ") || padrao;
  }
  return padrao;
}

export default function ProjetosPage() {
  const { token, user } = useAuth();
  const router = useRouter();
  const [projetos, setProjetos] = useState<Projeto[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [isLoadingMore, setIsLoadingMore] = useState(false);
  const [hasMore, setHasMore] = useState(false);

  // Filtros
  const [busca, setBusca] = useState("");
  const [buscaAplicada, setBuscaAplicada] = useState("");
  const [tipoFiltro, setTipoFiltro] = useState<"" | "pesquisa" | "extensao">("");
  const [instituicaoFiltro, setInstituicaoFiltro] = useState("");
  const [unidadeEscolhida, setUnidadeFiltro] = useState("");
  const [areaFiltro, setAreaFiltro] = useState("");
  const [remotoFiltro, setRemotoFiltro] = useState(false);
  const [filtros, setFiltros] = useState<InstituicaoFiltro[]>([]);

  // Categorias: instituição > unidade/departamento. As unidades só aparecem
  // depois de escolher a instituição (sem ela o seletor fica vazio e
  // desabilitado, em vez de listar as unidades de todas as universidades);
  // a lista toda vem de uma única chamada a /api/projetos/filtros.
  const gruposDeUnidades = filtros
    .filter((i) => instituicaoFiltro && i.sigla === instituicaoFiltro)
    .map((i) => ({ sigla: i.sigla, unidades: unidadesVisiveis(i, tipoFiltro) }))
    .filter((g) => g.unidades.length > 0);
  const unidadesOferecidas = gruposDeUnidades.flatMap((g) => g.unidades.map((u) => u.nome));
  // Uma unidade escolhida que saiu das opções (mudou a instituição ou o módulo)
  // deixa de valer, sem precisar de efeito.
  const unidadeFiltro =
    unidadeEscolhida && (filtros.length === 0 || unidadesOferecidas.includes(unidadeEscolhida))
      ? unidadeEscolhida
      : "";

  // Ignora respostas de buscas antigas (filtros mudaram no meio do caminho).
  const buscaAtual = useRef(0);

  // Modal State
  const [selectedProjeto, setSelectedProjeto] = useState<Projeto | null>(null);
  const [nome, setNome] = useState("");
  const [cursoPeriodo, setCursoPeriodo] = useState("");
  const [emailCandidato, setEmailCandidato] = useState("");
  const [lattes, setLattes] = useState("");
  const [carta, setCarta] = useState("");
  const [formStatus, setFormStatus] = useState<"idle" | "submitting" | "success" | "error">("idle");
  const [formError, setFormError] = useState("");

  const montarParams = useCallback(() => {
    const params = new URLSearchParams();
    if (buscaAplicada) params.set("q", buscaAplicada);
    if (tipoFiltro) params.set("modulo", tipoFiltro);
    if (instituicaoFiltro) params.set("instituicao", instituicaoFiltro);
    if (unidadeFiltro) params.set("unidade", unidadeFiltro);
    if (areaFiltro) params.set("area", areaFiltro);
    if (remotoFiltro) params.set("remoto", "true");
    params.set("page_size", String(PAGE_SIZE));
    return params;
  }, [buscaAplicada, tipoFiltro, instituicaoFiltro, unidadeFiltro, areaFiltro, remotoFiltro]);

  const carregarProjetos = useCallback(async () => {
    const id = ++buscaAtual.current;
    setIsLoading(true);
    try {
      const data = await api.get<Projeto[]>(
        `/api/projetos/buscar?${montarParams().toString()}`,
        { token: token || undefined }
      );
      if (id !== buscaAtual.current) return;
      setProjetos(data);
      setHasMore(data.length === PAGE_SIZE);
    } catch {
      if (id !== buscaAtual.current) return;
      setProjetos([]);
      setHasMore(false);
    } finally {
      if (id === buscaAtual.current) setIsLoading(false);
    }
  }, [montarParams, token]);

  useEffect(() => {
    carregarProjetos();
  }, [carregarProjetos]);

  // Busca por texto com debounce (o botão "Buscar" aplica na hora).
  useEffect(() => {
    const t = setTimeout(() => setBuscaAplicada(busca.trim()), 400);
    return () => clearTimeout(t);
  }, [busca]);

  useEffect(() => {
    api
      .get<{ instituicoes: InstituicaoFiltro[] }>("/api/projetos/filtros")
      .then((f) => setFiltros(f.instituicoes || []))
      .catch(() => setFiltros([]));
  }, []);

  async function carregarMais() {
    const ultimo = projetos[projetos.length - 1];
    if (!ultimo) return;
    const id = buscaAtual.current;
    setIsLoadingMore(true);
    try {
      const params = montarParams();
      params.set("last_id", ultimo.id);
      const data = await api.get<Projeto[]>(`/api/projetos/buscar?${params.toString()}`, {
        token: token || undefined,
      });
      if (id !== buscaAtual.current) return;
      setProjetos((atuais) => [...atuais, ...data]);
      setHasMore(data.length === PAGE_SIZE);
    } catch {
      setHasMore(false);
    } finally {
      setIsLoadingMore(false);
    }
  }

  function handleSearch(e: React.FormEvent) {
    e.preventDefault();
    setBuscaAplicada(busca.trim());
  }

  function abrirProjeto(projeto: Projeto) {
    setSelectedProjeto(projeto);
    // Pré-preenche com o que já sabemos do aluno logado.
    setNome(user?.nome_social || user?.nome || "");
    setCursoPeriodo(cursoPeriodoDoUsuario(user));
    setEmailCandidato(user?.email || "");
  }

  function fecharModal() {
    setSelectedProjeto(null);
    setFormStatus("idle");
    setFormError("");
    setNome("");
    setCursoPeriodo("");
    setEmailCandidato("");
    setLattes("");
    setCarta("");
  }

  async function handleCandidatar(e: React.FormEvent) {
    e.preventDefault();
    if (!token) {
      router.push("/login");
      return;
    }
    if (user?.perfil_completo === false) {
      // Conta do ORCID que ainda não escolheu o vínculo nem aceitou as regras:
      // a API recusa a candidatura (403) até concluir o perfil.
      router.push("/perfil/completar");
      return;
    }
    if (!selectedProjeto) return;
    if (carta.trim().length < CARTA_MIN) {
      setFormStatus("error");
      setFormError(`A carta de intenção precisa ter pelo menos ${CARTA_MIN} caracteres.`);
      return;
    }

    setFormStatus("submitting");
    setFormError("");

    try {
      await api.post(
        `/api/projetos/${selectedProjeto.id}/candidatar`,
        {
          nome,
          curso_periodo: cursoPeriodo,
          email: emailCandidato,
          lattes_url: lattes.trim() || null,
          carta,
        },
        { token }
      );
      setFormStatus("success");
      setTimeout(() => {
        fecharModal();
      }, 3000);
    } catch (err: unknown) {
      setFormStatus("error");
      const apiErr = err as { detail?: unknown };
      setFormError(mensagemDeErro(apiErr.detail, "Falha ao enviar candidatura ao servidor."));
    }
  }

  const tamanhoCarta = carta.trim().length;

  return (
    <div className={styles.page}>
      <div className={styles.header}>
        <h1 className={styles.title}>Projetos Acadêmicos</h1>
        <p className={styles.subtitle}>
          Descubra oportunidades de pesquisa e extensão
        </p>
        {/* A data da última coleta não é exibida: o momento em que a base foi
            atualizada é informação interna da equipe. */}
      </div>

      {/* ── Filtros ── */}
      <form onSubmit={handleSearch} className={styles.filters}>
        <div className={styles.searchGroup}>
          <input
            type="text"
            value={busca}
            onChange={(e) => setBusca(e.target.value)}
            placeholder="Buscar por título ou coordenador(a)..."
            className={styles.searchInput}
            maxLength={200}
          />
          <button type="submit" className={styles.searchButton}>
            Buscar
          </button>
        </div>
        <div className={styles.filterRow}>
          <select
            value={tipoFiltro}
            onChange={(e) => {
              setTipoFiltro(e.target.value as "" | "pesquisa" | "extensao");
              setUnidadeFiltro("");
            }}
            className={styles.filterInput}
            aria-label="Tipo de projeto"
          >
            <option value="">Pesquisa e Extensão</option>
            <option value="pesquisa">Pesquisa</option>
            <option value="extensao">Extensão</option>
          </select>
          {filtros.length > 0 && (
            <select
              value={instituicaoFiltro}
              onChange={(e) => {
                setInstituicaoFiltro(e.target.value);
                setUnidadeFiltro("");
              }}
              className={styles.filterInput}
              aria-label="Instituição ou universidade"
            >
              <option value="">Todas as instituições</option>
              {filtros.some((i) => i.externa) && (
                <optgroup label="Universidades (coleta automática)">
                  {filtros.filter((i) => i.externa).map((i) => (
                    <option key={i.sigla} value={i.sigla}>
                      {i.sigla} ({i.total})
                    </option>
                  ))}
                </optgroup>
              )}
              {filtros.some((i) => !i.externa) && (
                <optgroup label="Cadastrados na plataforma">
                  {filtros.filter((i) => !i.externa).map((i) => (
                    <option key={i.sigla} value={i.sigla}>
                      {i.sigla} ({i.total})
                    </option>
                  ))}
                </optgroup>
              )}
            </select>
          )}
          <select
            value={unidadeFiltro}
            onChange={(e) => setUnidadeFiltro(e.target.value)}
            className={styles.filterInput}
            aria-label="Unidade, departamento ou curso"
            disabled={unidadesOferecidas.length === 0}
          >
            <option value="">
              {!instituicaoFiltro
                ? "Unidades / Departamentos (escolha a instituição)"
                : unidadesOferecidas.length > 0
                  ? `Unidades da ${instituicaoFiltro}`
                  : `Sem unidades cadastradas para ${instituicaoFiltro}`}
            </option>
            {gruposDeUnidades.map((g) => (
              <optgroup key={g.sigla} label={g.sigla}>
                {g.unidades.map((u) => (
                  <option key={`${g.sigla}|${u.nome}`} value={u.nome}>
                    {u.nome} ({u.total})
                  </option>
                ))}
              </optgroup>
            ))}
          </select>
          <select
            value={areaFiltro}
            onChange={(e) => setAreaFiltro(e.target.value)}
            className={styles.filterInput}
          >
            <option value="">Áreas de Estudo</option>
            <option value="Ciências Biológicas e da Saúde">Ciências Biológicas e da Saúde</option>
            <option value="Ciências Exatas e da Terra">Ciências Exatas e da Terra</option>
            <option value="Ciências Humanas">Ciências Humanas</option>
            <option value="Ciências Sociais Aplicadas">Ciências Sociais Aplicadas</option>
            <option value="Área de Tecnologias">Área de Tecnologias</option>
            <option value="Engenharias">Engenharias</option>
            <option value="Ciências Agrárias">Ciências Agrárias</option>
            <option value="Artes e Design">Artes e Design</option>
            <option value="Linguística e Letras">Linguística e Letras</option>
          </select>
          <label className={styles.checkboxLabel}>
            <input
              type="checkbox"
              checked={remotoFiltro}
              onChange={(e) => setRemotoFiltro(e.target.checked)}
              className={styles.checkbox}
            />
            Remoto
          </label>
        </div>
      </form>

      {/* ── Lista de Projetos ── */}
      {isLoading ? (
        <div className={styles.loadingGrid}>
          {[1, 2, 3].map((i) => (
            <div key={i} className={styles.skeletonCard} />
          ))}
        </div>
      ) : projetos.length === 0 ? (
        <div className={styles.emptyState}>
          <span className={styles.emptyIcon}>📭</span>
          <h3>Nenhum projeto encontrado com esses filtros</h3>
          <p>Tente outra busca ou limpe os filtros de tipo e unidade.</p>
        </div>
      ) : (
        <>
          <div className={styles.projetosList}>
            {projetos.map((projeto, i) => (
              <article
                key={projeto.id}
                className={styles.projetoCard}
                style={{ animationDelay: `${(i % PAGE_SIZE) * 0.06}s`, cursor: "pointer" }}
                onClick={() => abrirProjeto(projeto)}
              >
                <div className={styles.projetoContent}>
                  <h3 className={styles.projetoTitulo}>{projeto.titulo}</h3>
                  {projeto.nome_professor && (
                    <p className={styles.projetoCoordenador}>
                      Coordenação: {projeto.nome_professor}
                    </p>
                  )}
                  {projeto.descricao && (
                    <p className={styles.projetoDesc}>{projeto.descricao}</p>
                  )}
                </div>
                {/*
                  Tags em ordem fixa, do mais geral ao mais específico:
                  tipo (Pesquisa/Extensão) → instituição → unidade → ano → remoto.
                  A situação fica fora do grupo, à direita, como indicador de estado,
                  para não virar um item solto quando as tags quebram de linha.
                */}
                <div className={styles.projetoMeta}>
                  <div className={styles.metaTags}>
                    {projeto.tipo && (
                      <span
                        className={`${styles.metaTag} ${
                          moduloDoProjeto(projeto) === "pesquisa"
                            ? styles.metaPesquisa
                            : moduloDoProjeto(projeto) === "extensao"
                              ? styles.metaExtensao
                              : ""
                        }`}
                      >
                        {projeto.tipo}
                      </span>
                    )}
                    {projeto.instituicao && (
                      // Sigla (UNIR, UNIRIO) para fontes externas; nome livre dos projetos
                      // manuais recebe o mesmo tratamento longo da unidade.
                      <span
                        className={`${styles.metaTag} ${projeto.origem ? styles.metaInstituicao : styles.metaUnidade}`}
                        title={projeto.instituicao}
                      >
                        {!projeto.origem && <span aria-hidden="true">🏛️</span>} {projeto.instituicao}
                      </span>
                    )}
                    {projeto.unidade && (
                      <span className={`${styles.metaTag} ${styles.metaUnidade}`} title={projeto.unidade}>
                        <span aria-hidden="true">🏛️</span> {projeto.unidade}
                      </span>
                    )}
                    {projeto.ano && (
                      <span className={styles.metaTag}>
                        <span aria-hidden="true">📅</span> {projeto.ano}
                      </span>
                    )}
                    {projeto.e_remoto && (
                      <span className={`${styles.metaTag} ${styles.metaRemoto}`}>
                        <span aria-hidden="true">🌐</span> Remoto
                      </span>
                    )}
                  </div>
                  {projeto.situacao ? (
                    <span className={`${styles.metaStatus} ${styles[`status_${tomDaSituacao(projeto.situacao)}`]}`}>
                      <span className={styles.statusDot} aria-hidden="true" />
                      {formatarSituacao(projeto.situacao)}
                    </span>
                  ) : projeto.dataPublicacao ? (
                    <span className={styles.metaDate}>{projeto.dataPublicacao}</span>
                  ) : null}
                </div>
              </article>
            ))}
          </div>
          {hasMore && (
            <div className={styles.loadMoreWrapper}>
              <button
                type="button"
                className={styles.loadMoreButton}
                onClick={carregarMais}
                disabled={isLoadingMore}
              >
                {isLoadingMore ? "Carregando..." : "Carregar mais projetos"}
              </button>
            </div>
          )}
        </>
      )}

      {/* ── Modal de Detalhes e Candidatura ── */}
      {selectedProjeto && (
        <div className={modalStyles.overlay} onClick={(e) => {
          if (e.target === e.currentTarget) fecharModal();
        }}>
          <div className={modalStyles.modal} role="dialog" aria-modal="true" aria-labelledby="projeto-titulo">
            <button className={modalStyles.closeButton} onClick={fecharModal} aria-label="Fechar">
              &times;
            </button>
            <h2 id="projeto-titulo" className={modalStyles.title}>{selectedProjeto.titulo}</h2>

            <div className={modalStyles.infoGrid}>
              {selectedProjeto.tipo && (
                <div className={modalStyles.infoLine}><strong>Tipo:</strong> {selectedProjeto.tipo}
                  {selectedProjeto.categoria && selectedProjeto.origem ? ` (${selectedProjeto.categoria})` : ""}
                </div>
              )}
              {selectedProjeto.nome_professor && (
                <div className={modalStyles.infoLine}>
                  <strong>{selectedProjeto.origem ? "Coordenador(a):" : "Professor/Pesquisador:"}</strong>{" "}
                  {selectedProjeto.nome_professor}
                </div>
              )}
              {selectedProjeto.instituicao && (
                <div className={modalStyles.infoLine}><strong>Instituição:</strong> {selectedProjeto.instituicao}</div>
              )}
              {selectedProjeto.unidade && (
                <div className={modalStyles.infoLine}><strong>Unidade/Departamento:</strong> {selectedProjeto.unidade}</div>
              )}
              {selectedProjeto.area_tematica && (
                <div className={modalStyles.infoLine}><strong>Área:</strong> {selectedProjeto.area_tematica}</div>
              )}
              {selectedProjeto.grupo_pesquisa && (
                <div className={modalStyles.infoLine}><strong>Grupo de pesquisa:</strong> {selectedProjeto.grupo_pesquisa}</div>
              )}
              {selectedProjeto.linhas_extensao && selectedProjeto.linhas_extensao.length > 0 && (
                <div className={modalStyles.infoLine}>
                  <strong>Linhas de extensão:</strong> {selectedProjeto.linhas_extensao.join(", ")}
                </div>
              )}
              {selectedProjeto.financiamento && (
                <div className={modalStyles.infoLine}><strong>Financiamento:</strong> {selectedProjeto.financiamento}</div>
              )}
              {selectedProjeto.ano && (
                <div className={modalStyles.infoLine}><strong>Ano:</strong> {selectedProjeto.ano}</div>
              )}
              {selectedProjeto.situacao && (
                <div className={modalStyles.infoLine}><strong>Situação:</strong> {formatarSituacao(selectedProjeto.situacao)}</div>
              )}
              {selectedProjeto.periodo_inicio && selectedProjeto.periodo_fim && (
                <div className={modalStyles.infoLine}>
                  <strong>Período:</strong> {formatarData(selectedProjeto.periodo_inicio)} a {formatarData(selectedProjeto.periodo_fim)}
                </div>
              )}
              {selectedProjeto.codigo && selectedProjeto.origem === "sigaa" && (
                <div className={modalStyles.infoLine}><strong>Código SIGAA:</strong> {selectedProjeto.codigo}</div>
              )}
              {selectedProjeto.palavras_chave && selectedProjeto.palavras_chave.length > 0 && (
                <div className={modalStyles.infoLine}>
                  <strong>Palavras-chave:</strong> {selectedProjeto.palavras_chave.join(", ")}
                </div>
              )}
              {selectedProjeto.local && (
                <div className={modalStyles.infoLine}><strong>Localização:</strong> {selectedProjeto.local}</div>
              )}
              {selectedProjeto.modalidade && (
                <div className={modalStyles.infoLine}><strong>Modalidade:</strong> {selectedProjeto.modalidade}</div>
              )}
              {selectedProjeto.link_detalhe && (
                <div className={modalStyles.infoLine}>
                  <a href={selectedProjeto.link_detalhe} target="_blank" rel="noopener noreferrer" className={modalStyles.externalLink}>
                    Ver no {FONTE_NOME[selectedProjeto.origem || ""] || "site de origem"} ↗
                  </a>
                </div>
              )}
            </div>

            {selectedProjeto.descricao && (
              <div className={modalStyles.descriptionSection}>
                <h4>Descrição:</h4>
                <p className={modalStyles.descriptionP}>{selectedProjeto.descricao}</p>
              </div>
            )}

            <div className={modalStyles.divider} />

            <div className={modalStyles.candidaturaSection}>
              <h4>Candidatar-se</h4>

              {!selectedProjeto.tem_contato ? (
                <>
                  <div className={modalStyles.noticeMessage}>
                    Projeto ainda sem contato cadastrado. Assim que o e-mail da coordenação
                    for cadastrado, você poderá enviar sua carta de intenção por aqui.
                  </div>
                  <button type="button" className={modalStyles.submitBtn} disabled>
                    Candidatar-se
                  </button>
                </>
              ) : !token ? (
                <button
                  type="button"
                  className={modalStyles.submitBtn}
                  onClick={() => router.push("/login")}
                >
                  Faça login para se candidatar
                </button>
              ) : formStatus === "success" ? (
                <div className={modalStyles.successMessage}>
                  Sua carta de intenção foi enviada à coordenação do projeto! ✅
                  <br />
                  Enviamos uma cópia para o e-mail da sua conta.
                </div>
              ) : (
                <form onSubmit={handleCandidatar}>
                  <div className={modalStyles.formGroup}>
                    <label className={modalStyles.label} htmlFor="cand-nome">Nome completo</label>
                    <input
                      id="cand-nome"
                      type="text"
                      required
                      minLength={3}
                      maxLength={120}
                      className={modalStyles.input}
                      value={nome}
                      onChange={(e) => setNome(e.target.value)}
                    />
                  </div>

                  <div className={modalStyles.formGroup}>
                    <label className={modalStyles.label} htmlFor="cand-curso">Curso e período</label>
                    <input
                      id="cand-curso"
                      type="text"
                      required
                      minLength={2}
                      maxLength={120}
                      placeholder="Ex.: Ciência da Computação — 5º período"
                      className={modalStyles.input}
                      value={cursoPeriodo}
                      onChange={(e) => setCursoPeriodo(e.target.value)}
                    />
                  </div>

                  <div className={modalStyles.formGroup}>
                    <label className={modalStyles.label} htmlFor="cand-email">Seu e-mail</label>
                    <input
                      id="cand-email"
                      type="email"
                      required
                      className={modalStyles.input}
                      value={emailCandidato}
                      onChange={(e) => setEmailCandidato(e.target.value)}
                    />
                    <span className={modalStyles.hint}>A resposta da coordenação chegará neste e-mail.</span>
                  </div>

                  <div className={modalStyles.formGroup}>
                    <label className={modalStyles.label} htmlFor="cand-lattes">
                      Link do Currículo Lattes <span className={modalStyles.optional}>(opcional)</span>
                    </label>
                    <input
                      id="cand-lattes"
                      type="url"
                      maxLength={300}
                      placeholder="http://lattes.cnpq.br/0000000000000000"
                      className={modalStyles.input}
                      value={lattes}
                      onChange={(e) => setLattes(e.target.value)}
                    />
                  </div>

                  <div className={modalStyles.formGroup}>
                    <label className={modalStyles.label} htmlFor="cand-carta">Carta de intenção</label>
                    <textarea
                      id="cand-carta"
                      required
                      rows={9}
                      maxLength={CARTA_MAX}
                      placeholder={CARTA_PLACEHOLDER}
                      className={modalStyles.textarea}
                      value={carta}
                      onChange={(e) => setCarta(e.target.value)}
                    />
                    <span
                      className={`${modalStyles.hint} ${tamanhoCarta >= CARTA_MIN ? modalStyles.hintOk : ""}`}
                      aria-live="polite"
                    >
                      {tamanhoCarta < CARTA_MIN
                        ? `${tamanhoCarta}/${CARTA_MIN} caracteres — faltam ${CARTA_MIN - tamanhoCarta}`
                        : `${tamanhoCarta} caracteres ✓`}
                    </span>
                  </div>

                  {formStatus === "error" && (
                    <div className={modalStyles.errorMessage}>{formError}</div>
                  )}

                  <button
                    type="submit"
                    className={modalStyles.submitBtn}
                    disabled={formStatus === "submitting"}
                  >
                    {formStatus === "submitting" ? "Enviando..." : "Enviar carta de intenção"}
                  </button>
                </form>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
