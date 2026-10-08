"use client";

import { memo, useCallback, useEffect, useId, useMemo, useRef, useState, type ReactNode } from "react";
import { useRouter } from "next/navigation";
import { api } from "@/lib/api";
import { useAuth } from "@/contexts/AuthContext";
import type { User } from "@/types/user";
import {
  formatarData,
  formatarSituacao,
  moduloDoProjeto,
  tomDaSituacao,
  type Projeto,
} from "@/types/projeto";
import Modal from "@/components/ui/Modal";
import MultiSelect from "@/components/ui/MultiSelect";
import ProjetoCard from "@/components/projetos/ProjetoCard";
import { IconeUfo } from "@/components/ui/Icones";
import styles from "./projetos.module.css";
import m from "./modal.module.css";

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
  campi: UnidadeFiltro[];
}

/** Grande área do CNPq com projetos no recorte atual (já vem na ordem fixa da tabela). */
interface AreaFiltro {
  nome: string;
  total: number;
}

interface FiltrosResponse {
  instituicoes: InstituicaoFiltro[];
  areas: AreaFiltro[];
}

type Modulo = "" | "pesquisa" | "extensao";

/** Unidades de uma instituição que têm projetos no módulo escolhido (ou em qualquer um). */
function unidadesVisiveis(inst: InstituicaoFiltro, modulo: string) {
  return inst.unidades.filter((u) => !modulo || (u.modulos[modulo] || 0) > 0);
}

/** Fontes que não publicam o e-mail de cada coordenação, mas têm um contato geral. */
const CONTATO_GERAL: Record<string, { rotulo: string; email: string }> = {
  "ufv:extensao": { rotulo: "Registro de Atividades de Extensão da UFV (RAEX)", email: "raex@ufv.br" },
};

/** Aviso mostrado no lugar do formulário quando o projeto não tem e-mail de contato. */
function avisoSemContato(p: Projeto) {
  const geral = CONTATO_GERAL[`${p.origem}:${p.modulo}`];
  if (geral) {
    return (
      <>
        A UFV não divulga o e-mail de cada coordenação nos dados abertos, então a candidatura por aqui
        fica indisponível. O contato geral é o {geral.rotulo}:{" "}
        <a href={`mailto:${geral.email}`}>{geral.email}</a>. Cite o título do projeto na mensagem.
      </>
    );
  }
  if (p.origem === "ufv") {
    return (
      <>
        A UFV não divulga o e-mail de cada coordenação nos dados abertos. Use a página do projeto no
        sistema de pesquisa da UFV (link acima) ou procure o departamento indicado.
      </>
    );
  }
  return (
    <>
      Projeto ainda sem contato cadastrado. Assim que o e-mail da coordenação for cadastrado, você
      poderá enviar sua carta de intenção por aqui.
    </>
  );
}

/** Nome da fonte externa, para o botão "Ver no SIGAA". */
const FONTE_NOME: Record<string, string> = {
  sigaa: "SIGAA",
  unirio: "Portal da UNIRIO",
  ufv: "Portal da UFV",
};

const PAGE_SIZE = 20;
const CARTA_MIN = 300;
const CARTA_MAX = 5000;

const CARTA_PLACEHOLDER = `Quem sou: curso, período e o que já estudei ou fiz que tem relação com o projeto.

Por que este projeto: o que me interessa nele e como posso contribuir.

Disponibilidade: quantas horas por semana, em quais turnos e a partir de quando.`;

function cursoPeriodoDoUsuario(user: User | null) {
  if (!user?.curso) return "";
  const semestre = user.dados_aluno?.semestre;
  return semestre ? `${user.curso}, ${semestre}º período` : user.curso;
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

/** Tira `?projeto=` da URL sem recarregar nem criar entrada no histórico. */
function removerParamProjeto() {
  const url = new URL(window.location.href);
  if (!url.searchParams.has("projeto")) return;
  url.searchParams.delete("projeto");
  window.history.replaceState(null, "", url.toString());
}

function gravarParamProjeto(id: string) {
  const url = new URL(window.location.href);
  if (url.searchParams.get("projeto") === id) return;
  url.searchParams.set("projeto", id);
  window.history.replaceState(null, "", url.toString());
}

/* ── Ícones (traço 2, estilo Lucide) ── */

const ICONE = {
  lupa: "M19 11a8 8 0 1 1-16 0 8 8 0 0 1 16 0M21 21l-4.3-4.3",
  x: "M18 6 6 18M6 6l12 12",
  linkExterno: "M15 3h6v6M10 14 21 3M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6",
  check: "M20 6 9 17l-5-5",
  buscaVazia: "M13.5 8.5l-5 5M8.5 8.5l5 5M19 11a8 8 0 1 1-16 0 8 8 0 0 1 16 0M21 21l-4.3-4.3",
  alerta: "m21.73 18-8-14a2 2 0 0 0-3.48 0l-8 14A2 2 0 0 0 4 21h16a2 2 0 0 0 1.73-3M12 9v4M12 17h.01",
  info: "M22 12a10 10 0 1 1-20 0 10 10 0 0 1 20 0M12 16v-4M12 8h.01",
  carregando: "M21 12a9 9 0 1 1-6.22-8.56",
  repetir: "M21 12a9 9 0 1 1-9-9c2.52 0 4.93 1 6.74 2.74L21 8M21 3v5h-5",
};

function Icone({
  nome,
  tamanho = 20,
  className = "",
}: {
  nome: keyof typeof ICONE;
  tamanho?: number;
  className?: string;
}) {
  return (
    <svg
      width={tamanho}
      height={tamanho}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
      className={className}
    >
      <path d={ICONE[nome]} />
    </svg>
  );
}

/* ═══════════════════════════════════════════
   Página
   ═══════════════════════════════════════════ */

export default function ProjetosPage() {
  const { token } = useAuth();
  const [projetos, setProjetos] = useState<Projeto[]>([]);
  // A lista nunca é zerada enquanto uma busca nova está no ar: `atualizando`
  // só esmaece o que já está na tela. O esqueleto aparece apenas quando
  // ainda não há nada para mostrar.
  const [atualizando, setAtualizando] = useState(true);
  const [carregouUmaVez, setCarregouUmaVez] = useState(false);
  const [erroBusca, setErroBusca] = useState(false);
  const [isLoadingMore, setIsLoadingMore] = useState(false);
  const [hasMore, setHasMore] = useState(false);

  // Filtros
  const [busca, setBusca] = useState("");
  const [buscaAplicada, setBuscaAplicada] = useState("");
  const [tipoFiltro, setTipoFiltro] = useState<Modulo>("");
  const [instituicaoFiltro, setInstituicaoFiltro] = useState("");
  const [unidadesEscolhidas, setUnidadesEscolhidas] = useState<string[]>([]);
  const [campiEscolhidos, setCampiEscolhidos] = useState<string[]>([]);
  const [areaEscolhida, setAreaFiltro] = useState("");
  const [remotoFiltro, setRemotoFiltro] = useState(false);
  const [filtros, setFiltros] = useState<InstituicaoFiltro[]>([]);
  const [areas, setAreas] = useState<AreaFiltro[]>([]);

  const inputBuscaRef = useRef<HTMLInputElement>(null);
  const idBusca = useId();

  // Categorias: instituição > campus / unidade. Campi e unidades só aparecem
  // depois de escolher a instituição; a lista toda vem de uma única chamada
  // a /api/projetos/filtros.
  const instituicao = useMemo(
    () => (instituicaoFiltro ? filtros.find((i) => i.sigla === instituicaoFiltro) ?? null : null),
    [filtros, instituicaoFiltro]
  );
  const unidadesOferecidas = useMemo(
    () => (instituicao ? unidadesVisiveis(instituicao, tipoFiltro) : []),
    [instituicao, tipoFiltro]
  );
  const campiOferecidos = useMemo(
    () =>
      instituicao
        ? (instituicao.campi || []).filter((c) => !tipoFiltro || (c.modulos[tipoFiltro] || 0) > 0)
        : [],
    [instituicao, tipoFiltro]
  );
  // Escolhas que saíram das opções (mudou a instituição ou o módulo) deixam
  // de valer, sem precisar de efeito.
  const unidadesFiltro = useMemo(
    () =>
      filtros.length === 0
        ? unidadesEscolhidas
        : unidadesEscolhidas.filter((u) => unidadesOferecidas.some((o) => o.nome === u)),
    [filtros.length, unidadesEscolhidas, unidadesOferecidas]
  );
  const campiFiltro = useMemo(
    () =>
      filtros.length === 0
        ? campiEscolhidos
        : campiEscolhidos.filter((c) => campiOferecidos.some((o) => o.nome === c)),
    [filtros.length, campiEscolhidos, campiOferecidos]
  );
  // Áreas do conhecimento com projetos no recorte atual. Uma área escolhida
  // que saiu das opções deixa de valer, pela mesma regra da unidade.
  const areaFiltro =
    areaEscolhida && (areas.length === 0 || areas.some((a) => a.nome === areaEscolhida)) ? areaEscolhida : "";

  const opcoesCampi = useMemo(
    () => campiOferecidos.map((c) => ({ valor: c.nome, rotulo: c.nome, total: c.total })),
    [campiOferecidos]
  );
  const opcoesUnidades = useMemo(
    () => unidadesOferecidas.map((u) => ({ valor: u.nome, rotulo: u.nome, total: u.total })),
    [unidadesOferecidas]
  );

  const instituicoesExternas = useMemo(() => filtros.filter((i) => i.externa), [filtros]);
  const instituicoesInternas = useMemo(() => filtros.filter((i) => !i.externa), [filtros]);

  const temFiltroAtivo =
    busca.trim() !== "" ||
    tipoFiltro !== "" ||
    instituicaoFiltro !== "" ||
    campiFiltro.length > 0 ||
    unidadesFiltro.length > 0 ||
    areaFiltro !== "" ||
    remotoFiltro;

  // Ignora respostas de buscas antigas (filtros mudaram no meio do caminho).
  const buscaAtual = useRef(0);
  const filtrosAtuais = useRef(0);

  // Modal
  const [selectedProjeto, setSelectedProjeto] = useState<Projeto | null>(null);
  const [avisoLink, setAvisoLink] = useState("");

  // Recorte comum à busca e às opções de filtro: tudo menos a área e a
  // paginação. As listas entram como texto para o callback só mudar quando
  // o conteúdo muda (a resposta de /filtros recria os arrays a cada vez).
  const chaveUnidades = JSON.stringify(unidadesFiltro);
  const chaveCampi = JSON.stringify(campiFiltro);
  const montarParamsRecorte = useCallback(() => {
    const params = new URLSearchParams();
    if (buscaAplicada) params.set("q", buscaAplicada);
    if (tipoFiltro) params.set("modulo", tipoFiltro);
    if (instituicaoFiltro) params.set("instituicao", instituicaoFiltro);
    (JSON.parse(chaveUnidades) as string[]).forEach((u) => params.append("unidade", u));
    (JSON.parse(chaveCampi) as string[]).forEach((c) => params.append("campus", c));
    if (remotoFiltro) params.set("remoto", "true");
    return params;
  }, [buscaAplicada, tipoFiltro, instituicaoFiltro, chaveUnidades, chaveCampi, remotoFiltro]);

  const montarParams = useCallback(() => {
    const params = montarParamsRecorte();
    if (areaFiltro) params.set("area", areaFiltro);
    params.set("page_size", String(PAGE_SIZE));
    return params;
  }, [montarParamsRecorte, areaFiltro]);

  const carregarProjetos = useCallback(async () => {
    const id = ++buscaAtual.current;
    setAtualizando(true);
    try {
      const data = await api.get<Projeto[]>(`/api/projetos/buscar?${montarParams().toString()}`, {
        token: token || undefined,
      });
      if (id !== buscaAtual.current) return;
      setProjetos(data);
      setHasMore(data.length === PAGE_SIZE);
      setErroBusca(false);
    } catch {
      if (id !== buscaAtual.current) return;
      setProjetos([]);
      setHasMore(false);
      setErroBusca(true);
    } finally {
      if (id === buscaAtual.current) {
        setAtualizando(false);
        setCarregouUmaVez(true);
      }
    }
  }, [montarParams, token]);

  useEffect(() => {
    carregarProjetos();
  }, [carregarProjetos]);

  // Busca por texto com debounce (o botão "Buscar" aplica na hora). As
  // opções de filtro seguem o mesmo debounce, porque dependem de `buscaAplicada`.
  useEffect(() => {
    const t = setTimeout(() => setBuscaAplicada(busca.trim()), 400);
    return () => clearTimeout(t);
  }, [busca]);

  // Opções de filtro. As instituições (e suas unidades) não dependem do
  // recorte; as áreas do conhecimento sim, então a lista é refeita a cada
  // mudança nos outros filtros, e respostas de recortes antigos são ignoradas.
  useEffect(() => {
    const id = ++filtrosAtuais.current;
    const query = montarParamsRecorte().toString();
    api
      .get<FiltrosResponse>(`/api/projetos/filtros${query ? `?${query}` : ""}`)
      .then((f) => {
        if (id !== filtrosAtuais.current) return;
        setFiltros(f.instituicoes || []);
        setAreas(f.areas || []);
      })
      .catch(() => {
        if (id !== filtrosAtuais.current) return;
        setAreas([]);
      });
  }, [montarParamsRecorte]);

  // Link direto (/projetos?projeto=<id>): busca o projeto pela rota pública
  // e abre o modal. Lido de window.location dentro do efeito para não
  // precisar do Suspense que useSearchParams exige.
  useEffect(() => {
    const id = new URLSearchParams(window.location.search).get("projeto");
    if (!id) return;
    let cancelado = false;
    api
      .get<Projeto>(`/api/projetos/${encodeURIComponent(id)}`)
      .then((p) => {
        if (!cancelado) setSelectedProjeto(p);
      })
      .catch(() => {
        if (cancelado) return;
        setAvisoLink("O projeto do link não foi encontrado ou não está mais disponível.");
        removerParamProjeto();
      });
    return () => {
      cancelado = true;
    };
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

  function limparBusca() {
    setBusca("");
    setBuscaAplicada("");
    inputBuscaRef.current?.focus();
  }

  function limparFiltros() {
    setBusca("");
    setBuscaAplicada("");
    setTipoFiltro("");
    setInstituicaoFiltro("");
    setUnidadesEscolhidas([]);
    setCampiEscolhidos([]);
    setAreaFiltro("");
    setRemotoFiltro(false);
  }

  // Estáveis, para o card (memo) e o modal não serem refeitos a cada render.
  const abrirProjeto = useCallback((projeto: Projeto) => {
    setSelectedProjeto(projeto);
    gravarParamProjeto(projeto.id);
  }, []);

  const fecharModal = useCallback(() => {
    setSelectedProjeto(null);
    removerParamProjeto();
  }, []);

  const total = projetos.length;
  const mostrarEsqueleto = total === 0 && (atualizando || !carregouUmaVez);
  const contagem = total === 1 ? "1 projeto carregado" : `${total} projetos carregados`;

  return (
    <div className={styles.pagina}>
      <div className={styles.container}>
        <header className="ui-page-header">
          <h1 className="ui-page-title">Projetos acadêmicos</h1>
          <p className="ui-page-subtitle">
            Projetos de pesquisa e extensão das universidades, em um só lugar. Encontre o seu e envie uma
            carta de intenção à coordenação.
          </p>
        </header>

        {/* ── Filtros ── */}
        <form onSubmit={handleSearch} className={`ui-card ${styles.filtros}`} role="search" aria-label="Filtrar projetos">
          <div className={styles.linhaBusca}>
            <div className={styles.campoBusca}>
              <Icone nome="lupa" className={styles.iconeBusca} />
              <label htmlFor={idBusca} className="sr-only">
                Buscar por título ou coordenação
              </label>
              <input
                id={idBusca}
                ref={inputBuscaRef}
                type="text"
                value={busca}
                onChange={(e) => setBusca(e.target.value)}
                placeholder="Título ou coordenação"
                className={`ui-field ${styles.inputBusca}`}
                maxLength={200}
                autoComplete="off"
              />
              {busca && (
                <button type="button" className={styles.limparBusca} onClick={limparBusca} aria-label="Limpar busca">
                  <Icone nome="x" tamanho={18} />
                </button>
              )}
            </div>
            <button type="submit" className="ui-btn ui-btn-primary">
              Buscar
            </button>
          </div>

          <div className={styles.grade}>
            <select
              value={tipoFiltro}
              onChange={(e) => {
                setTipoFiltro(e.target.value as Modulo);
                setUnidadesEscolhidas([]);
                setCampiEscolhidos([]);
              }}
              className="ui-field"
              aria-label="Módulo"
            >
              <option value="">Pesquisa e extensão</option>
              <option value="pesquisa">Pesquisa</option>
              <option value="extensao">Extensão</option>
            </select>

            <select
              value={instituicaoFiltro}
              onChange={(e) => {
                setInstituicaoFiltro(e.target.value);
                setUnidadesEscolhidas([]);
                setCampiEscolhidos([]);
              }}
              className="ui-field"
              aria-label="Instituição"
              disabled={filtros.length === 0}
            >
              <option value="">Todas as instituições</option>
              {instituicoesExternas.length > 0 && (
                <optgroup label="Universidades (coleta automática)">
                  {instituicoesExternas.map((i) => (
                    <option key={i.sigla} value={i.sigla}>
                      {i.sigla} ({i.total})
                    </option>
                  ))}
                </optgroup>
              )}
              {instituicoesInternas.length > 0 && (
                <optgroup label="Cadastrados na plataforma">
                  {instituicoesInternas.map((i) => (
                    <option key={i.sigla} value={i.sigla}>
                      {i.sigla} ({i.total})
                    </option>
                  ))}
                </optgroup>
              )}
            </select>

            {/* Campi e unidades da instituição escolhida, com seleção múltipla. */}
            <MultiSelect
              rotulo="Campus"
              rotuloTodos="Todos os campi"
              placeholder={
                !instituicaoFiltro
                  ? "Campus"
                  : campiOferecidos.length > 0
                    ? `Campi da ${instituicaoFiltro}`
                    : `Sem campi para ${instituicaoFiltro}`
              }
              opcoes={opcoesCampi}
              selecionados={campiFiltro}
              onChange={setCampiEscolhidos}
              disabled={campiOferecidos.length === 0}
            />
            <MultiSelect
              rotulo="Unidades"
              rotuloTodos="Todas as unidades"
              placeholder={
                !instituicaoFiltro
                  ? "Unidades"
                  : unidadesOferecidas.length > 0
                    ? `Unidades da ${instituicaoFiltro}`
                    : `Sem unidades para ${instituicaoFiltro}`
              }
              opcoes={opcoesUnidades}
              selecionados={unidadesFiltro}
              onChange={setUnidadesEscolhidas}
              disabled={unidadesOferecidas.length === 0}
            />

            {/* Grandes áreas do CNPq, na ordem fixa da tabela, só as que têm projeto no recorte atual. */}
            <select
              value={areaFiltro}
              onChange={(e) => setAreaFiltro(e.target.value)}
              className="ui-field"
              aria-label="Área do conhecimento"
              disabled={areas.length === 0}
            >
              <option value="">{areas.length > 0 ? "Todas as áreas" : "Área do conhecimento"}</option>
              {areas.map((a) => (
                <option key={a.nome} value={a.nome}>
                  {a.nome} ({a.total})
                </option>
              ))}
            </select>
          </div>

          <div className={styles.linhaExtras}>
            <label className={styles.marcar}>
              <input type="checkbox" checked={remotoFiltro} onChange={(e) => setRemotoFiltro(e.target.checked)} />
              Somente remotos
            </label>
            {temFiltroAtivo && (
              <button type="button" className="ui-btn ui-btn-ghost" onClick={limparFiltros}>
                <Icone nome="x" tamanho={16} />
                Limpar filtros
              </button>
            )}
          </div>
        </form>

        {avisoLink && (
          <div className={styles.avisoLink} role="status">
            <Icone nome="info" className={styles.avisoIcone} />
            <span className={styles.avisoTexto}>{avisoLink}</span>
            <button type="button" className={styles.avisoFechar} onClick={() => setAvisoLink("")} aria-label="Fechar aviso">
              <Icone nome="x" tamanho={16} />
            </button>
          </div>
        )}

        {/* ── Lista ── */}
        {carregouUmaVez && !mostrarEsqueleto && total > 0 && (
          <div className={styles.resultadosTopo}>
            <p className={styles.contagem} aria-live="polite">
              {contagem}
            </p>
            {atualizando && (
              <span className={styles.atualizando}>
                <Icone nome="carregando" tamanho={16} className={styles.girando} />
                Atualizando
              </span>
            )}
          </div>
        )}

        {mostrarEsqueleto ? (
          <div className={styles.lista} aria-busy="true" aria-label="Carregando projetos">
            {[1, 2, 3].map((i) => (
              <div key={i} className={`skeleton ${styles.esqueleto}`} />
            ))}
          </div>
        ) : erroBusca && total === 0 ? (
          <div className={`ui-card ${styles.vazio}`} role="alert">
            <span className={styles.vazioIcone}>
              <Icone nome="alerta" tamanho={24} />
            </span>
            <h2 className={styles.vazioTitulo}>Não foi possível carregar os projetos</h2>
            <p className={styles.vazioTexto}>Confira sua conexão e tente de novo.</p>
            <button type="button" className="ui-btn ui-btn-secondary" onClick={carregarProjetos}>
              <Icone nome="repetir" tamanho={16} />
              Tentar de novo
            </button>
          </div>
        ) : total === 0 ? (
          <div className={`ui-card ${styles.vazio}`}>
            <span className={`${styles.vazioIcone} ${styles.vazioMarca}`}>
              <IconeUfo tamanho={30} />
            </span>
            <h2 className={styles.vazioTitulo}>Nenhum projeto com esses filtros</h2>
            <p className={styles.vazioTexto}>
              Nossa nave varreu a base e não achou nada por aqui. Tente outra palavra ou amplie o recorte de
              instituição, unidade e área.
            </p>
            {temFiltroAtivo && (
              <button type="button" className="ui-btn ui-btn-secondary" onClick={limparFiltros}>
                Limpar filtros
              </button>
            )}
          </div>
        ) : (
          <>
            <div className={`${styles.lista} ${atualizando ? styles.listaAtualizando : ""}`} aria-busy={atualizando}>
              {projetos.map((projeto) => (
                <ProjetoCard key={projeto.id} projeto={projeto} onClick={abrirProjeto} />
              ))}
            </div>
            {hasMore && (
              <div className={styles.maisWrapper}>
                <button
                  type="button"
                  className="ui-btn ui-btn-secondary ui-btn-lg"
                  onClick={carregarMais}
                  disabled={isLoadingMore || atualizando}
                >
                  {isLoadingMore ? "Carregando" : "Carregar mais"}
                </button>
              </div>
            )}
          </>
        )}
      </div>

      {/* ── Modal de detalhes e candidatura ── */}
      <Modal
        aberto={selectedProjeto !== null}
        titulo={selectedProjeto?.titulo ?? ""}
        onFechar={fecharModal}
        tamanho="largo"
        botaoRodape={false}
      >
        {selectedProjeto && <DetalheProjeto projeto={selectedProjeto} onFechar={fecharModal} />}
      </Modal>
    </div>
  );
}

/* ═══════════════════════════════════════════
   Detalhe do projeto (corpo do modal)
   ═══════════════════════════════════════════ */

function Secao({ titulo, children }: { titulo: string; children: ReactNode }) {
  return (
    <section className={m.secao}>
      <h3 className={m.secaoTitulo}>{titulo}</h3>
      {children}
    </section>
  );
}

const DetalheProjeto = memo(function DetalheProjeto({
  projeto: p,
  onFechar,
}: {
  projeto: Projeto;
  onFechar: () => void;
}) {
  const { token, user } = useAuth();
  const router = useRouter();
  const modulo = moduloDoProjeto(p);
  const situacao = formatarSituacao(p.situacao);
  const tom = tomDaSituacao(p.situacao);

  const metadados: { rotulo: string; valor: ReactNode }[] = [];
  if (p.nome_professor) {
    metadados.push({ rotulo: p.origem ? "Coordenação" : "Docente ou pesquisador(a)", valor: p.nome_professor });
  }
  if (p.responsavel_acao && p.responsavel_acao !== p.nome_professor) {
    metadados.push({ rotulo: "Responsável pela ação", valor: p.responsavel_acao });
  }
  if (p.categoria && p.origem) metadados.push({ rotulo: "Categoria", valor: p.categoria });
  if (p.instituicao) metadados.push({ rotulo: "Instituição", valor: p.instituicao });
  if (p.campus) metadados.push({ rotulo: "Campus", valor: p.campus });
  if (p.unidade) metadados.push({ rotulo: "Unidade ou departamento", valor: p.unidade });
  if (p.area_conhecimento) metadados.push({ rotulo: "Área do conhecimento", valor: p.area_conhecimento });
  if (p.area_tematica) metadados.push({ rotulo: "Área temática", valor: p.area_tematica });
  if (situacao) {
    metadados.push({
      rotulo: "Situação",
      valor: (
        <span className={`${m.situacao} ${m[`tom_${tom}`]}`}>
          <span className={m.ponto} aria-hidden="true" />
          {situacao}
        </span>
      ),
    });
  }
  if (p.periodo_inicio && p.periodo_fim) {
    metadados.push({ rotulo: "Período", valor: `${formatarData(p.periodo_inicio)} a ${formatarData(p.periodo_fim)}` });
  }
  if (p.ano) metadados.push({ rotulo: "Ano", valor: p.ano });
  if (p.codigo && p.origem === "sigaa") metadados.push({ rotulo: "Código no SIGAA", valor: p.codigo });
  if (p.modalidade) metadados.push({ rotulo: "Modalidade", valor: p.modalidade });
  if (p.local) metadados.push({ rotulo: "Localização", valor: p.local });

  const temConteudoPrincipal = Boolean(
    p.descricao ||
      (p.palavras_chave && p.palavras_chave.length > 0) ||
      (p.linhas_extensao && p.linhas_extensao.length > 0) ||
      p.grupo_pesquisa ||
      p.financiamento
  );

  return (
    <>
      <div className={m.corpo}>
        <div className={m.principal}>
          <div className={m.chips}>
            {p.tipo && (
              <span
                className={`ui-chip ${
                  modulo === "pesquisa" ? "ui-chip-primary" : modulo === "extensao" ? "ui-chip-info" : ""
                }`}
              >
                {p.tipo}
              </span>
            )}
            {p.e_remoto && <span className="ui-chip ui-chip-success">Remoto</span>}
          </div>

          {p.descricao && (
            <Secao titulo="Descrição">
              <p className={m.texto}>{p.descricao}</p>
            </Secao>
          )}
          {p.palavras_chave && p.palavras_chave.length > 0 && (
            <Secao titulo="Palavras-chave">
              <ul className={m.listaChips}>
                {p.palavras_chave.map((palavra) => (
                  <li key={palavra} className="ui-chip">
                    {palavra}
                  </li>
                ))}
              </ul>
            </Secao>
          )}
          {p.linhas_extensao && p.linhas_extensao.length > 0 && (
            <Secao titulo="Linhas de extensão">
              <ul className={m.listaTexto}>
                {p.linhas_extensao.map((linha) => (
                  <li key={linha}>{linha}</li>
                ))}
              </ul>
            </Secao>
          )}
          {p.grupo_pesquisa && (
            <Secao titulo="Grupo de pesquisa">
              <p className={m.texto}>{p.grupo_pesquisa}</p>
            </Secao>
          )}
          {p.financiamento && (
            <Secao titulo="Financiamento">
              <p className={m.texto}>{p.financiamento}</p>
            </Secao>
          )}
          {!temConteudoPrincipal && (
            <p className={m.semDescricao}>A fonte não publicou descrição para este projeto.</p>
          )}
        </div>

        <aside className={m.lateral} aria-label="Dados do projeto">
          {metadados.length > 0 && (
            <dl className={m.meta}>
              {metadados.map((item) => (
                <div key={item.rotulo} className={m.metaItem}>
                  <dt>{item.rotulo}</dt>
                  <dd>{item.valor}</dd>
                </div>
              ))}
            </dl>
          )}
          {p.link_detalhe ? (
            <a
              href={p.link_detalhe}
              target="_blank"
              rel="noopener noreferrer"
              className={`ui-btn ui-btn-secondary ${m.linkFonte}`}
            >
              Ver no {FONTE_NOME[p.origem || ""] || "site de origem"}
              <Icone nome="linkExterno" tamanho={16} />
            </a>
          ) : p.link_consulta ? (
            // Pesquisa no SIGAA não tem página pública por projeto: o botão abre a
            // consulta da instituição e a dica diz o que digitar lá.
            <div className={m.linkConsulta}>
              <a
                href={p.link_consulta}
                target="_blank"
                rel="noopener noreferrer"
                className={`ui-btn ui-btn-secondary ${m.linkFonte}`}
              >
                Buscar no SIGAA
                <Icone nome="linkExterno" tamanho={16} />
              </a>
              <p className={m.linkConsultaDica}>
                {p.codigo ? (
                  <>
                    Na consulta pública, procure pelo código <strong>{p.codigo}</strong> ou pelo título.
                  </>
                ) : (
                  <>Na consulta pública, procure pelo título do projeto.</>
                )}
              </p>
            </div>
          ) : null}
        </aside>
      </div>

      <section className={`ui-card ${m.candidatura}`} aria-labelledby="candidatura-titulo">
        <h3 id="candidatura-titulo" className={m.candidaturaTitulo}>
          Candidatar-se
        </h3>

        {!p.tem_contato ? (
          <>
            <div className={m.aviso}>
              <Icone nome="info" className={m.avisoIcone} />
              <p>{avisoSemContato(p)}</p>
            </div>
            <button type="button" className="ui-btn ui-btn-primary" disabled>
              Candidatar-se
            </button>
          </>
        ) : !token ? (
          <>
            <p className={m.candidaturaTexto}>
              Entre na sua conta para enviar uma carta de intenção à coordenação deste projeto.
            </p>
            <button type="button" className="ui-btn ui-btn-primary" onClick={() => router.push("/login")}>
              Faça login para se candidatar
            </button>
          </>
        ) : (
          <FormularioCandidatura key={user?.id ?? "anonimo"} projeto={p} onEnviado={onFechar} />
        )}
      </section>
    </>
  );
});

/* ═══════════════════════════════════════════
   Formulário de candidatura (estado local: digitar na carta não refaz o modal)
   ═══════════════════════════════════════════ */

function FormularioCandidatura({ projeto, onEnviado }: { projeto: Projeto; onEnviado: () => void }) {
  const { token, user } = useAuth();
  const router = useRouter();
  const idBase = useId();

  // Pré-preenche com o que já sabemos do aluno logado.
  const [nome, setNome] = useState(user?.nome_social || user?.nome || "");
  const [cursoPeriodo, setCursoPeriodo] = useState(cursoPeriodoDoUsuario(user));
  const [emailCandidato, setEmailCandidato] = useState(user?.email || "");
  const [lattes, setLattes] = useState("");
  const [carta, setCarta] = useState("");
  const [formStatus, setFormStatus] = useState<"idle" | "submitting" | "success" | "error">("idle");
  const [formError, setFormError] = useState("");

  // Depois do envio, o modal fecha sozinho em alguns segundos.
  useEffect(() => {
    if (formStatus !== "success") return;
    const t = setTimeout(onEnviado, 3000);
    return () => clearTimeout(t);
  }, [formStatus, onEnviado]);

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
    if (carta.trim().length < CARTA_MIN) {
      setFormStatus("error");
      setFormError(`A carta de intenção precisa ter pelo menos ${CARTA_MIN} caracteres.`);
      return;
    }

    setFormStatus("submitting");
    setFormError("");

    try {
      await api.post(
        `/api/projetos/${projeto.id}/candidatar`,
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
    } catch (err: unknown) {
      setFormStatus("error");
      const apiErr = err as { detail?: unknown };
      setFormError(mensagemDeErro(apiErr.detail, "Falha ao enviar candidatura ao servidor."));
    }
  }

  if (formStatus === "success") {
    return (
      <div className={m.sucesso} role="status">
        <Icone nome="check" className={m.sucessoIcone} />
        <p>
          Sua carta de intenção foi enviada à coordenação do projeto!
          <br />
          Enviamos uma cópia para o e-mail da sua conta.
        </p>
      </div>
    );
  }

  const tamanhoCarta = carta.trim().length;
  const cartaOk = tamanhoCarta >= CARTA_MIN;

  return (
    <form onSubmit={handleCandidatar} className={m.form}>
      <div className={m.linhaCampos}>
        <div className={m.campo}>
          <label className="ui-label" htmlFor={`${idBase}-nome`}>
            Nome completo
          </label>
          <input
            id={`${idBase}-nome`}
            type="text"
            required
            minLength={3}
            maxLength={120}
            className="ui-field"
            value={nome}
            onChange={(e) => setNome(e.target.value)}
            autoComplete="name"
          />
        </div>

        <div className={m.campo}>
          <label className="ui-label" htmlFor={`${idBase}-curso`}>
            Curso e período
          </label>
          <input
            id={`${idBase}-curso`}
            type="text"
            required
            minLength={2}
            maxLength={120}
            placeholder="Ex.: Ciência da Computação, 5º período"
            className="ui-field"
            value={cursoPeriodo}
            onChange={(e) => setCursoPeriodo(e.target.value)}
          />
        </div>
      </div>

      <div className={m.linhaCampos}>
        <div className={m.campo}>
          <label className="ui-label" htmlFor={`${idBase}-email`}>
            Seu e-mail
          </label>
          <input
            id={`${idBase}-email`}
            type="email"
            required
            className="ui-field"
            value={emailCandidato}
            onChange={(e) => setEmailCandidato(e.target.value)}
            autoComplete="email"
          />
          <p className="ui-hint">A resposta da coordenação chegará neste e-mail.</p>
        </div>

        <div className={m.campo}>
          <label className="ui-label" htmlFor={`${idBase}-lattes`}>
            Link do Currículo Lattes <span className={m.opcional}>(opcional)</span>
          </label>
          <input
            id={`${idBase}-lattes`}
            type="url"
            maxLength={300}
            placeholder="http://lattes.cnpq.br/0000000000000000"
            className="ui-field"
            value={lattes}
            onChange={(e) => setLattes(e.target.value)}
          />
        </div>
      </div>

      <div className={m.campo}>
        <label className="ui-label" htmlFor={`${idBase}-carta`}>
          Carta de intenção
        </label>
        <textarea
          id={`${idBase}-carta`}
          required
          rows={9}
          maxLength={CARTA_MAX}
          placeholder={CARTA_PLACEHOLDER}
          className={`ui-field ${m.carta}`}
          value={carta}
          onChange={(e) => setCarta(e.target.value)}
        />
        <p className={`ui-hint ${m.contador} ${cartaOk ? m.contadorOk : ""}`} aria-live="polite">
          {cartaOk ? (
            <>
              <Icone nome="check" tamanho={14} />
              {tamanhoCarta} caracteres
            </>
          ) : (
            `${tamanhoCarta} de ${CARTA_MIN} caracteres (faltam ${CARTA_MIN - tamanhoCarta})`
          )}
        </p>
      </div>

      {formStatus === "error" && (
        <div className={m.erro} role="alert">
          {formError}
        </div>
      )}

      <div className={m.acoes}>
        <button type="submit" className="ui-btn ui-btn-primary" disabled={formStatus === "submitting"}>
          {formStatus === "submitting" ? "Enviando" : "Enviar carta de intenção"}
        </button>
      </div>
    </form>
  );
}
