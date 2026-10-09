"use client";

import {
  Suspense,
  useCallback,
  useEffect,
  useId,
  useMemo,
  useRef,
  useState,
} from "react";
import { useSearchParams } from "next/navigation";
import { api } from "@/lib/api";
import { useAuth } from "@/contexts/AuthContext";
import type { Projeto } from "@/types/projeto";
import Modal from "@/components/ui/Modal";
import MultiSelect from "@/components/ui/MultiSelect";
import ProjetoCard from "@/components/projetos/ProjetoCard";
import { IconeInfo, IconeUfo } from "@/components/ui/Icones";
import { DetalheProjeto } from "./_componentes/DetalheProjeto";
import { Icone } from "./_componentes/Icone";
import styles from "./projetos.module.css";

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

const PAGE_SIZE = 20;

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

/* ═══════════════════════════════════════════
   Página
   ═══════════════════════════════════════════ */

/**
 * A busca da página inicial chega como ?q=. useSearchParams exige um Suspense
 * numa página pré-renderizada: o HTML do servidor sai com a página parada
 * (`pronto` falso, sem pedidos à API) e, no navegador, ela é montada de novo
 * já com o termo, antes de a primeira busca sair.
 */
export default function ProjetosPage() {
  return (
    <Suspense fallback={<ProjetosConteudo qInicial="" pronto={false} />}>
      <ProjetosComTermo />
    </Suspense>
  );
}

function ProjetosComTermo() {
  const q = useSearchParams().get("q") ?? "";
  return <ProjetosConteudo qInicial={q} pronto />;
}

/** Mantém ?q= na URL igual à busca aplicada, sem criar entrada no histórico. */
function gravarParamBusca(termo: string) {
  const url = new URL(window.location.href);
  if ((url.searchParams.get("q") ?? "") === termo) return;
  if (termo) url.searchParams.set("q", termo);
  else url.searchParams.delete("q");
  window.history.replaceState(null, "", url.toString());
}

function ProjetosConteudo({ qInicial, pronto }: { qInicial: string; pronto: boolean }) {
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
  const [busca, setBusca] = useState(qInicial);
  const [buscaAplicada, setBuscaAplicada] = useState(qInicial.trim());
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

  // Celular e tablet: a barra de busca fica presa sob o cabeçalho ao rolar a
  // lista. A marca invisível logo acima dela diz quando a barra descolou do
  // lugar; só então ela ganha fundo e sombra (no topo da página, nada muda).
  const marcaBarraRef = useRef<HTMLSpanElement>(null);
  const [barraColada, setBarraColada] = useState(false);
  useEffect(() => {
    const marca = marcaBarraRef.current;
    if (!marca) return;
    const alturaCabecalho =
      parseFloat(getComputedStyle(document.documentElement).getPropertyValue("--navbar-height")) || 0;
    const observador = new IntersectionObserver(
      ([entrada]) => setBarraColada(!entrada.isIntersecting && entrada.boundingClientRect.top < alturaCabecalho + 1),
      { rootMargin: `-${alturaCabecalho}px 0px 0px 0px` }
    );
    observador.observe(marca);
    return () => observador.disconnect();
  }, []);

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

  // Filtros do painel (sem a busca por texto): a contagem vai no botão
  // "Filtros" do celular e decide se o "Limpar filtros" do painel aparece.
  const totalFiltrosAtivos =
    (tipoFiltro ? 1 : 0) +
    (instituicaoFiltro ? 1 : 0) +
    campiFiltro.length +
    unidadesFiltro.length +
    (areaFiltro ? 1 : 0) +
    (remotoFiltro ? 1 : 0);

  const temFiltroAtivo =
    busca.trim() !== "" ||
    tipoFiltro !== "" ||
    instituicaoFiltro !== "" ||
    campiFiltro.length > 0 ||
    unidadesFiltro.length > 0 ||
    areaFiltro !== "" ||
    remotoFiltro;

  // Painel de filtros: coluna fixa no desktop; no celular e no tablet, uma
  // folha que sobe do rodapé, aberta pelo botão "Filtros".
  const [filtrosAbertos, setFiltrosAbertos] = useState(false);
  const botaoFiltrosRef = useRef<HTMLButtonElement>(null);
  const painelRef = useRef<HTMLElement>(null);
  const idModulo = useId();
  const idInstituicao = useId();
  const idArea = useId();

  const fecharFiltros = useCallback(() => {
    setFiltrosAbertos(false);
    botaoFiltrosRef.current?.focus();
  }, []);

  // Folha aberta: foco nela, Esc fecha, Tab circula só dentro dela, a página
  // de trás não rola, e ela fecha sozinha se a tela passar a desktop.
  useEffect(() => {
    if (!filtrosAbertos) return;
    const painel = painelRef.current;
    painel?.focus();
    function aoTeclar(e: KeyboardEvent) {
      if (e.key === "Escape") {
        fecharFiltros();
        return;
      }
      if (e.key !== "Tab" || !painel) return;
      const focaveis = painel.querySelectorAll<HTMLElement>(
        'button:not([disabled]), select:not([disabled]), input:not([disabled]), [tabindex]:not([tabindex="-1"])'
      );
      if (focaveis.length === 0) return;
      const primeiro = focaveis[0];
      const ultimo = focaveis[focaveis.length - 1];
      if (e.shiftKey && (document.activeElement === primeiro || document.activeElement === painel)) {
        e.preventDefault();
        ultimo.focus();
      } else if (!e.shiftKey && document.activeElement === ultimo) {
        e.preventDefault();
        primeiro.focus();
      }
    }
    const desktop = window.matchMedia("(min-width: 1024px)");
    function aoVirarDesktop(e: MediaQueryListEvent) {
      if (e.matches) setFiltrosAbertos(false);
    }
    document.addEventListener("keydown", aoTeclar);
    desktop.addEventListener("change", aoVirarDesktop);
    const overflowAnterior = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    return () => {
      document.removeEventListener("keydown", aoTeclar);
      desktop.removeEventListener("change", aoVirarDesktop);
      document.body.style.overflow = overflowAnterior;
    };
  }, [filtrosAbertos, fecharFiltros]);

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
    if (pronto) carregarProjetos();
  }, [carregarProjetos, pronto]);

  // Recarregar a página ou mandar o link mantém o termo buscado.
  useEffect(() => {
    if (pronto) gravarParamBusca(buscaAplicada);
  }, [buscaAplicada, pronto]);

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
    if (!pronto) return;
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
  }, [montarParamsRecorte, pronto]);

  // Link direto (/projetos?projeto=<id>): busca o projeto pela rota pública
  // e abre o modal. Lido de window.location dentro do efeito, que só roda
  // quando a página já está montada com a URL certa.
  useEffect(() => {
    if (!pronto) return;
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
  }, [pronto]);

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

  /** Só os filtros do painel; a busca por texto continua. */
  function limparFiltrosDoPainel() {
    setTipoFiltro("");
    setInstituicaoFiltro("");
    setUnidadesEscolhidas([]);
    setCampiEscolhidos([]);
    setAreaFiltro("");
    setRemotoFiltro(false);
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

  // Etiquetas dos filtros em uso, cada uma com o x que tira só ela.
  const etiquetas: { chave: string; rotulo: string; limpar: () => void }[] = [];
  if (buscaAplicada) etiquetas.push({ chave: "q", rotulo: `“${buscaAplicada}”`, limpar: limparBusca });
  if (tipoFiltro) {
    etiquetas.push({
      chave: "modulo",
      rotulo: tipoFiltro === "pesquisa" ? "Pesquisa" : "Extensão",
      limpar: () => setTipoFiltro(""),
    });
  }
  if (instituicaoFiltro) {
    etiquetas.push({
      chave: "instituicao",
      rotulo: instituicaoFiltro,
      limpar: () => {
        setInstituicaoFiltro("");
        setUnidadesEscolhidas([]);
        setCampiEscolhidos([]);
      },
    });
  }
  campiFiltro.forEach((c) =>
    etiquetas.push({
      chave: `campus-${c}`,
      rotulo: `Campus ${c}`,
      limpar: () => setCampiEscolhidos((atuais) => atuais.filter((x) => x !== c)),
    })
  );
  unidadesFiltro.forEach((u) =>
    etiquetas.push({
      chave: `unidade-${u}`,
      rotulo: u,
      limpar: () => setUnidadesEscolhidas((atuais) => atuais.filter((x) => x !== u)),
    })
  );
  if (areaFiltro) etiquetas.push({ chave: "area", rotulo: areaFiltro, limpar: () => setAreaFiltro("") });
  if (remotoFiltro) etiquetas.push({ chave: "remoto", rotulo: "Remoto", limpar: () => setRemotoFiltro(false) });

  return (
    <div className={styles.pagina}>
      <div className={styles.container}>
        <header className="ui-page-header">
          <h1 className="ui-page-title">Projetos acadêmicos</h1>
          <p className="ui-page-subtitle">
            Projetos de pesquisa e extensão das universidades, em um só lugar. Encontre o seu e envie uma
            carta de intenção à coordenação.
          </p>
          {/* Linha discreta: no desktop mostra o resumo e abre o texto completo;
              no celular fica só o título, recolhido. */}
          <details className={styles.origem}>
            <summary className={styles.origemResumo}>
              <IconeInfo tamanho={16} />
              <span className={styles.origemTitulo}>De onde vêm estes projetos</span>
              <span className={styles.origemFrase}>
                Só projetos em andamento que as universidades publicam em acesso aberto, atualizados toda semana.
              </span>
              <span className={styles.origemAcao} aria-hidden="true">
                <span className={styles.origemAbrir}>Saiba mais</span>
                <span className={styles.origemFechar}>Fechar</span>
                <Icone nome="seta" tamanho={16} className={styles.origemSeta} />
              </span>
            </summary>
            <p className={styles.origemTexto}>
              Reunimos somente projetos em andamento que as universidades publicam em acesso aberto, nos
              próprios portais. Quando uma instituição não divulga os projetos, ou divulga sem a situação ou o
              contato da coordenação, eles ficam de fora, e por isso uma busca pode voltar vazia mesmo que o
              tema exista por lá. A base é atualizada toda semana; antes de se candidatar, vale confirmar os
              detalhes no portal da instituição.
            </p>
          </details>
        </header>

        {/* ── Busca por texto ── */}
        <span ref={marcaBarraRef} className={styles.marcaBarra} aria-hidden="true" />
        <form
          onSubmit={handleSearch}
          className={`${styles.barraBusca} ${barraColada ? styles.barraColada : ""}`}
          role="search"
          aria-label="Buscar projetos"
        >
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
              enterKeyHint="search"
            />
            {busca && (
              <button type="button" className={styles.limparBusca} onClick={limparBusca} aria-label="Limpar busca">
                <Icone nome="x" tamanho={18} />
              </button>
            )}
          </div>
          {/* No celular o botão sai: a busca já se aplica sozinha ao parar de
              digitar, e a tecla de busca do teclado envia na hora. */}
          <button type="submit" className={`ui-btn ui-btn-primary ${styles.botaoBuscar}`}>
            Buscar
          </button>
          <button
            type="button"
            ref={botaoFiltrosRef}
            className={`ui-btn ui-btn-secondary ${styles.botaoFiltros}`}
            onClick={() => setFiltrosAbertos(true)}
            aria-expanded={filtrosAbertos}
            aria-controls="painel-filtros"
            aria-label={totalFiltrosAtivos > 0 ? `Filtros, ${totalFiltrosAtivos} em uso` : "Filtros"}
          >
            <Icone nome="filtros" tamanho={18} />
            <span className={styles.botaoFiltrosTexto}>Filtros</span>
            {totalFiltrosAtivos > 0 && <span className={styles.contadorFiltros}>{totalFiltrosAtivos}</span>}
          </button>
        </form>

        <div className={styles.layout}>
          {/* ── Painel de filtros (coluna no desktop, folha no celular) ── */}
          <aside
            id="painel-filtros"
            ref={painelRef}
            className={`${styles.painel} ${filtrosAbertos ? styles.painelAberto : ""}`}
            aria-labelledby="titulo-filtros"
            tabIndex={-1}
            {...(filtrosAbertos ? { role: "dialog", "aria-modal": true } : {})}
          >
            <div className={styles.painelTopo}>
              <h2 id="titulo-filtros" className={styles.painelTitulo}>
                Filtros
              </h2>
              <button type="button" className={styles.painelFechar} onClick={fecharFiltros} aria-label="Fechar filtros">
                <Icone nome="x" tamanho={20} />
              </button>
            </div>

            <div className={styles.painelCorpo}>
              <div className={styles.campoFiltro}>
                <label htmlFor={idModulo} className={styles.rotuloFiltro}>
                  Módulo
                </label>
                <select
                  value={tipoFiltro}
                  onChange={(e) => {
                    setTipoFiltro(e.target.value as Modulo);
                    setUnidadesEscolhidas([]);
                    setCampiEscolhidos([]);
                  }}
                  className="ui-field"
                  id={idModulo}
                >
                  <option value="">Pesquisa e extensão</option>
                  <option value="pesquisa">Pesquisa</option>
                  <option value="extensao">Extensão</option>
                </select>
              </div>

              <div className={styles.campoFiltro}>
                <label htmlFor={idInstituicao} className={styles.rotuloFiltro}>
                  Instituição
                </label>
                <select
                  value={instituicaoFiltro}
                  onChange={(e) => {
                    setInstituicaoFiltro(e.target.value);
                    setUnidadesEscolhidas([]);
                    setCampiEscolhidos([]);
                  }}
                  className="ui-field"
                  id={idInstituicao}
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
              </div>

              {/* Campi e unidades da instituição escolhida, com seleção múltipla. */}
              <div className={styles.campoFiltro}>
                <span className={styles.rotuloFiltro} aria-hidden="true">
                  Campus
                </span>
                <MultiSelect
                  rotulo="Campus"
                  rotuloTodos="Todos os campi"
                  placeholder={
                    !instituicaoFiltro
                      ? "Escolha a instituição"
                      : campiOferecidos.length > 0
                        ? `Campi da ${instituicaoFiltro}`
                        : `Sem campi para ${instituicaoFiltro}`
                  }
                  opcoes={opcoesCampi}
                  selecionados={campiFiltro}
                  onChange={setCampiEscolhidos}
                  disabled={campiOferecidos.length === 0}
                />
              </div>

              <div className={styles.campoFiltro}>
                <span className={styles.rotuloFiltro} aria-hidden="true">
                  Unidade ou departamento
                </span>
                <MultiSelect
                  rotulo="Unidades"
                  rotuloTodos="Todas as unidades"
                  placeholder={
                    !instituicaoFiltro
                      ? "Escolha a instituição"
                      : unidadesOferecidas.length > 0
                        ? `Unidades da ${instituicaoFiltro}`
                        : `Sem unidades para ${instituicaoFiltro}`
                  }
                  opcoes={opcoesUnidades}
                  selecionados={unidadesFiltro}
                  onChange={setUnidadesEscolhidas}
                  disabled={unidadesOferecidas.length === 0}
                />
              </div>

              {/* Grandes áreas do CNPq, na ordem fixa da tabela, só as que têm projeto no recorte atual. */}
              <div className={styles.campoFiltro}>
                <label htmlFor={idArea} className={styles.rotuloFiltro}>
                  Área do conhecimento
                </label>
                <select
                  value={areaFiltro}
                  onChange={(e) => setAreaFiltro(e.target.value)}
                  className="ui-field"
                  id={idArea}
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

              <label className={styles.marcar}>
                <input type="checkbox" checked={remotoFiltro} onChange={(e) => setRemotoFiltro(e.target.checked)} />
                Somente remotos
              </label>

              {totalFiltrosAtivos > 0 && (
                <button type="button" className={`ui-btn ui-btn-ghost ${styles.limparPainel}`} onClick={limparFiltrosDoPainel}>
                  <Icone nome="x" tamanho={16} />
                  Limpar filtros
                </button>
              )}
            </div>

            <div className={styles.painelRodape}>
              <button
                type="button"
                className="ui-btn ui-btn-secondary"
                onClick={limparFiltrosDoPainel}
                disabled={totalFiltrosAtivos === 0}
              >
                Limpar
              </button>
              <button type="button" className="ui-btn ui-btn-primary" onClick={fecharFiltros}>
                Ver resultados
              </button>
            </div>
          </aside>
          {filtrosAbertos && <div className={styles.fundoPainel} onClick={fecharFiltros} aria-hidden="true" />}

          {/* ── Resultados ── */}
          <div className={styles.resultados}>
            {avisoLink && (
              <div className={styles.avisoLink} role="status">
                <Icone nome="info" className={styles.avisoIcone} />
                <span className={styles.avisoTexto}>{avisoLink}</span>
                <button type="button" className={styles.avisoFechar} onClick={() => setAvisoLink("")} aria-label="Fechar aviso">
                  <Icone nome="x" tamanho={16} />
                </button>
              </div>
            )}

            {etiquetas.length > 0 && (
              <div className={styles.etiquetas}>
                <span className="sr-only">Filtros em uso:</span>
                {etiquetas.map((e) => (
                  <button
                    key={e.chave}
                    type="button"
                    className={`ui-chip ${styles.etiqueta}`}
                    onClick={e.limpar}
                    aria-label={`Tirar o filtro ${e.rotulo}`}
                    title={e.rotulo}
                  >
                    <span className={styles.etiquetaTexto}>{e.rotulo}</span>
                    <Icone nome="x" tamanho={14} />
                  </button>
                ))}
                {etiquetas.length > 1 && (
                  <button type="button" className={styles.limparTudo} onClick={limparFiltros}>
                    Limpar tudo
                  </button>
                )}
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
              <div className={`${styles.lista} ${styles.listaCarregando}`} aria-busy="true" aria-label="Carregando projetos">
                {/* Enquanto carrega, a nave passa o feixe sobre os cards em branco. */}
                <div className={styles.varredura} aria-hidden="true">
                  <div className={styles.varreduraNave}>
                    <IconeUfo tamanho={30} />
                    <span className={styles.varreduraFeixe} />
                  </div>
                </div>
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
        </div>
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
