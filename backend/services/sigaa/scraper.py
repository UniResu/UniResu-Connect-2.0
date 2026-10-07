"""
Coleta de projetos das consultas públicas do SIGAA (UNIR e as demais
instituições de `services.sigaa.instituicoes`; muda só o endereço base).

Fluxo JSF (baseado no script de referência scraper_sigaa_unir.py):
  1. GET na página de consulta → captura o form e o javax.faces.ViewState;
  2. POST com todos os campos + filtros + name=value do botão "Buscar";
  3. parse da tabela de resultados;
  4. para cada item, busca a página de detalhe (coordenador, e-mail, período).

Boas maneiras com o servidor da UNIR: pausa mínima entre QUALQUER
requisição (SIGAA_PAUSA_SEGUNDOS, nunca < 1s), timeout, e retry com backoff
exponencial. Falha no detalhe de um item não aborta a coleta: o item é
mantido com os dados da listagem e o erro é registrado.
"""

import logging
from dataclasses import dataclass, field
from typing import Optional

from bs4 import BeautifulSoup

from services.http_client import ClienteHttp, ErroColeta
from services.sigaa import parser
from services.sigaa.config import SigaaConfig

logger = logging.getLogger(__name__)

CAMINHOS_CONSULTA = {
    "pesquisa": "/sigaa/public/pesquisa/consulta_projetos.jsf?aba=p-pesquisa",
    "extensao": "/sigaa/public/extensao/consulta_extensao.jsf?acao=2&aba=p-extensao",
}


def urls_consulta(base_url: str) -> dict[str, str]:
    """Páginas públicas de consulta de um SIGAA, por módulo."""
    base = base_url.rstrip("/")
    return {modulo: base + caminho for modulo, caminho in CAMINHOS_CONSULTA.items()}


# Endereços da UNIR (padrão histórico; os demais vêm de SigaaClient.urls).
URLS = urls_consulta(parser.BASE_URL)


def _base_url(client) -> str:
    """Endereço base do SIGAA do cliente (clientes de teste podem não ter cfg)."""
    cfg = getattr(client, "cfg", None)
    return (getattr(cfg, "base_url", None) or parser.BASE_URL).rstrip("/")


def _urls(client) -> dict[str, str]:
    return urls_consulta(_base_url(client))


def _nome(client) -> str:
    cfg = getattr(client, "cfg", None)
    return getattr(client, "nome", None) or f"SIGAA/{getattr(cfg, 'instituicao', 'UNIR')}"


def _limitar(client, itens: list[dict]) -> list[dict]:
    """Aplica o teto SIGAA_MAX_ITENS (0 = sem teto), para testes e dry-run."""
    teto = int(getattr(getattr(client, "cfg", None), "max_itens", 0) or 0)
    if teto and len(itens) > teto:
        logger.info("%s: só os %d primeiros de %d itens serão abertos (SIGAA_MAX_ITENS)",
                    _nome(client), teto, len(itens))
        return itens[:teto]
    return itens


class SigaaErro(ErroColeta):
    """Falha de rede/HTTP após esgotar as tentativas, ou página inesperada."""


@dataclass
class ResultadoColeta:
    modulo: str
    itens: list[dict] = field(default_factory=list)
    erros: list[dict] = field(default_factory=list)


class SigaaClient(ClienteHttp):
    """Sessão HTTP com throttle, timeout e retry com backoff (ver services/http_client.py)."""

    erro = SigaaErro
    # O SIGAA responde em ISO-8859-1 (declarado no Content-Type).
    encoding_padrao = "iso-8859-1"
    nome = "SIGAA"

    def __init__(self, cfg: SigaaConfig, **kwargs):
        super().__init__(cfg, **kwargs)
        self.nome = f"SIGAA/{getattr(cfg, 'instituicao', 'UNIR')}"

    @property
    def base_url(self) -> str:
        return _base_url(self)

    @property
    def urls(self) -> dict[str, str]:
        return _urls(self)


# ─────────────────────────────────────────────
#  Busca (listagem)
# ─────────────────────────────────────────────

# Variações de "em execução" nos formulários de pesquisa dos SIGAAs.
SITUACOES_EM_EXECUCAO = ("EM EXECUÇÃO", "EM ANDAMENTO", "EM EXECUCAO")

# Select usado para dividir uma busca que o portal recusa por excesso de
# resultados, por módulo, em ordem de tentativa.
DIVISOES = {"pesquisa": ["centro", "unidade"], "extensao": ["TipoAcao", "unidade"]}


def montar_payload_busca(html_form: str, modulo: str, ano: str, situacao: Optional[str],
                         extra: Optional[tuple[str, str]] = None) -> dict:
    """Monta o POST da busca a partir do HTML da página de consulta.

    `extra` = (trecho do name do select, valor) restringe a busca por mais um
    campo (centro, unidade, tipo de ação), usado quando o portal limita o
    número de resultados. Se a opção de situação pedida não existe no
    formulário (cada SIGAA tem seu vocabulário), a busca segue sem esse
    filtro e o chamador filtra pela situação da listagem.
    """
    form = parser.achar_form(BeautifulSoup(html_form, "html.parser"))
    dados = parser.payload_base(form)
    if modulo == "pesquisa" and situacao:
        opcao = parser.opcao_disponivel(form, [situacao, *SITUACOES_EM_EXECUCAO])
        if opcao:
            parser.aplicar_filtro_select(form, dados, opcao)
        else:
            logger.warning("Situação '%s' não existe no formulário (opções: %s); buscando sem esse filtro.",
                           situacao, ", ".join(parser.opcoes_de_situacao(form)) or "nenhuma")
    if not parser.aplicar_filtro_texto(form, dados, ["ANO"], ano):
        raise SigaaErro("Campo Ano não encontrado no formulário.")
    if extra and not parser.aplicar_select_por_nome(form, dados, extra[0], extra[1]):
        raise SigaaErro(f"Select '{extra[0]}' não encontrado no formulário.")
    parser.aplicar_botao_buscar(form, dados)
    return dados


def situacao_filtrada(html_form: str, situacao: Optional[str]) -> bool:
    """O formulário tem a opção de situação pedida (ou uma equivalente)?"""
    if not situacao:
        return False
    form = parser.achar_form(BeautifulSoup(html_form, "html.parser"))
    return parser.opcao_disponivel(form, [situacao, *SITUACOES_EM_EXECUCAO]) is not None


@dataclass
class PaginaListagem:
    """Uma página de resultados e como ela foi obtida (para refazer o POST)."""
    html: str
    extra: Optional[tuple[str, str]] = None
    situacao_filtrada: bool = True


def _buscar(client: SigaaClient, modulo: str, ano: str, extra: Optional[tuple[str, str]] = None) -> PaginaListagem:
    url = _urls(client)[modulo]
    html_form = client.get(url)
    situacao = client.cfg.pesquisa_situacao if modulo == "pesquisa" else None
    dados = montar_payload_busca(html_form, modulo, ano, situacao, extra)
    return PaginaListagem(client.post(url, dados), extra, situacao_filtrada(html_form, situacao))


def _opcoes_divisao(client: SigaaClient, modulo: str, nome_select: str, apenas: Optional[set[str]] = None) -> list[tuple[str, str]]:
    form = parser.achar_form(BeautifulSoup(client.get(_urls(client)[modulo]), "html.parser"))
    opcoes = parser.opcoes_select(form, nome_select)
    if apenas is not None:
        opcoes = [(v, t) for v, t in opcoes if parser.normalizar(t) in apenas]
    return opcoes


def buscar_paginas(client: SigaaClient, modulo: str, ano: str) -> list[PaginaListagem]:
    """Todas as páginas de resultado de um módulo/ano. Quando o portal recusa a
    busca por excesso de resultados, divide por centro/unidade (pesquisa) ou
    por tipo de ação e depois unidade (extensão) e junta tudo."""
    primeira = _buscar(client, modulo, ano)
    if not parser.resultados_excessivos(primeira.html):
        return [primeira]
    paginas: list[PaginaListagem] = []
    divisoes = DIVISOES[modulo]
    apenas = {parser.normalizar(t) for t in client.cfg.extensao_tipos} if modulo == "extensao" else None
    primeiro_nivel = _opcoes_divisao(client, modulo, divisoes[0], apenas)
    logger.info("%s %s %s: portal limita resultados; dividindo por %s (%d opções)",
                _nome(client), modulo, ano, divisoes[0], len(primeiro_nivel))
    for valor, texto in primeiro_nivel:
        pagina = _buscar(client, modulo, ano, (divisoes[0], valor))
        if not parser.resultados_excessivos(pagina.html):
            paginas.append(pagina)
            continue
        if len(divisoes) < 2:
            logger.warning("%s %s %s: ainda excessivo em %s=%s; sem outro nível de divisão", _nome(client), modulo, ano, divisoes[0], texto)
            continue
        segundo_nivel = _opcoes_divisao(client, modulo, divisoes[1])
        logger.info("%s %s %s: %s=%s ainda excessivo; dividindo por %s (%d opções)",
                    _nome(client), modulo, ano, divisoes[0], texto, divisoes[1], len(segundo_nivel))
        for valor2, texto2 in segundo_nivel:
            # Dois filtros ao mesmo tempo: o do primeiro nível fica no payload
            # base e o do segundo entra como extra.
            url = _urls(client)[modulo]
            html_form = client.get(url)
            situacao = client.cfg.pesquisa_situacao if modulo == "pesquisa" else None
            dados = montar_payload_busca(html_form, modulo, ano, situacao, (divisoes[0], valor))
            form = parser.achar_form(BeautifulSoup(html_form, "html.parser"))
            parser.aplicar_select_por_nome(form, dados, divisoes[1], valor2)
            html = client.post(url, dados)
            if parser.resultados_excessivos(html):
                logger.warning("%s %s %s: ainda excessivo em %s=%s / %s=%s", _nome(client), modulo, ano,
                               divisoes[0], texto, divisoes[1], texto2)
                continue
            paginas.append(PaginaListagem(html, (divisoes[1], valor2), situacao_filtrada(html_form, situacao)))
    return paginas


def _detalhe_por_postback(client: SigaaClient, modulo: str, pagina: PaginaListagem, item: dict, ano: str,
                          parse) -> dict:
    """Detalhe aberto por postback do form da listagem (a página de detalhe
    não tem URL própria). Se o ViewState expirou, refaz a busca e tenta de novo."""
    html = pagina.html
    for tentativa in range(2):
        try:
            if tentativa == 1:
                html = _buscar(client, modulo, ano, pagina.extra).html
            form = parser.achar_form(BeautifulSoup(html, "html.parser"), "formConsulta")
            dados = parser.payload_base(form)
            dados.update(item.get("detalhe_params") or {})
            return parse(client.post(_urls(client)[modulo], dados))
        except (ErroColeta, ValueError):
            if tentativa == 1:
                raise
    raise SigaaErro("detalhe indisponível")


# ─────────────────────────────────────────────
#  Pesquisa
# ─────────────────────────────────────────────

def coletar_pesquisa(client: SigaaClient, ano: str) -> ResultadoColeta:
    res = ResultadoColeta("pesquisa")
    paginas = buscar_paginas(client, "pesquisa", ano)
    itens: list[tuple[dict, PaginaListagem]] = []
    vistos: set = set()
    for pagina in paginas:
        for item in parser.parse_listagem_pesquisa(pagina.html):
            chave = item.get("sigaa_id") or (item.get("codigo"), item.get("titulo"))
            if chave in vistos:
                continue
            vistos.add(chave)
            if not pagina.situacao_filtrada and client.cfg.pesquisa_situacao \
                    and not parser.situacao_vigente(item.get("situacao")):
                continue  # o portal não filtrou por situação: filtramos pela listagem
            itens.append((item, pagina))
    itens = itens[: client.cfg.max_itens] if getattr(client.cfg, "max_itens", 0) else itens
    logger.info("%s pesquisa %s: %d projetos na listagem (%d página(s))", _nome(client), ano, len(itens), len(paginas))
    if not itens and paginas:
        logger.warning("%s pesquisa %s: nenhum item reconhecido.\n%s", _nome(client), ano,
                       parser.diagnostico_pagina(paginas[0].html))

    for item, pagina in itens:
        detalhe = None
        try:
            detalhe = _detalhe_por_postback(client, "pesquisa", pagina, item, ano, parser.parse_detalhe_pesquisa)
        except (ErroColeta, ValueError) as e:
            res.erros.append(_erro("pesquisa", item, e))
        res.itens.append(_registro("pesquisa", item, detalhe))
    return res


# ─────────────────────────────────────────────
#  Extensão
# ─────────────────────────────────────────────

def coletar_extensao(client: SigaaClient, ano: str) -> ResultadoColeta:
    res = ResultadoColeta("extensao")
    paginas = buscar_paginas(client, "extensao", ano)
    tipos = {parser.normalizar(t) for t in client.cfg.extensao_tipos}
    todos = 0
    itens: list[tuple[dict, PaginaListagem]] = []
    vistos: set = set()
    for pagina in paginas:
        for item in parser.parse_listagem_extensao(pagina.html, _base_url(client)):
            todos += 1
            chave = item.get("sigaa_id") or (item.get("ano"), item.get("titulo"))
            if chave in vistos or parser.normalizar(item.get("categoria")) not in tipos:
                continue
            vistos.add(chave)
            itens.append((item, pagina))
    itens = itens[: client.cfg.max_itens] if getattr(client.cfg, "max_itens", 0) else itens
    logger.info("%s extensão %s: %d ações na listagem, %d nos tipos %s (%d página(s))",
                _nome(client), ano, todos, len(itens), sorted(tipos), len(paginas))
    if not todos and paginas:
        logger.warning("%s extensão %s: nenhum item reconhecido.\n%s", _nome(client), ano,
                       parser.diagnostico_pagina(paginas[0].html))

    for item, pagina in itens:
        detalhe = None
        try:
            if not item.get("link_detalhe") and not item.get("detalhe_params"):
                raise SigaaErro("Item sem link de detalhe.")
            erro_link = None
            try:
                # Link público estável (GET): não depende de ViewState.
                detalhe = parser.parse_detalhe_extensao(client.get(item["link_detalhe"])) if item.get("link_detalhe") else None
            except (ErroColeta, ValueError) as e:
                if not item.get("detalhe_params"):
                    raise
                logger.info("%s extensão: link público falhou (%s); tentando o detalhe por postback", _nome(client), e)
                erro_link = e
            if detalhe is None:
                try:
                    detalhe = _detalhe_por_postback(client, "extensao", pagina, item, ano, parser.parse_detalhe_extensao)
                except (ErroColeta, ValueError) as e:
                    # O erro registrado é o do link público, que é o caminho principal.
                    raise erro_link or e
            detalhe["situacao"] = parser.situacao_por_periodo(detalhe["periodo_inicio"], detalhe["periodo_fim"])
        except (ErroColeta, ValueError) as e:
            res.erros.append(_erro("extensao", item, e))
        res.itens.append(_registro("extensao", item, detalhe))
    return res


# ─────────────────────────────────────────────
#  Normalização
# ─────────────────────────────────────────────

def _registro(modulo: str, item: dict, detalhe: Optional[dict]) -> dict:
    """Registro final: dados da listagem, enriquecidos pelo detalhe se houver."""
    d = detalhe or {}
    return {
        "modulo": modulo,
        "sigaa_id": item.get("sigaa_id"),
        "codigo": item.get("codigo"),
        "titulo": item.get("titulo"),
        "coordenador": d.get("coordenador") or item.get("coordenador"),
        "email": d.get("email"),
        "unidade": d.get("unidade") or item.get("unidade"),
        "situacao": d.get("situacao") or item.get("situacao"),
        "ano": item.get("ano"),
        "categoria": item.get("categoria"),
        "link_detalhe": item.get("link_detalhe"),
        "descricao": d.get("descricao"),
        "periodo_inicio": d.get("periodo_inicio"),
        "periodo_fim": d.get("periodo_fim"),
        "detalhe_ok": detalhe is not None,
        # Extensão: quem assina como responsável pela ação (pode ser discente) e a equipe.
        "extras": {k: d[k] for k in ("responsavel_acao", "equipe") if d.get(k)},
    }


def _erro(modulo: str, item: dict, e: Exception) -> dict:
    logger.warning("SIGAA %s: falha no detalhe de '%s' (id=%s): %s",
                   modulo, item.get("titulo"), item.get("sigaa_id"), e)
    erro = {"modulo": modulo, "sigaa_id": item.get("sigaa_id"), "titulo": item.get("titulo"), "erro": str(e)}
    if item.get("onclick") and not item.get("sigaa_id"):
        # Sem id reconhecido: guarda o onclick cru para adaptar o parser.
        erro["onclick"] = item["onclick"]
    return erro


COLETORES = {"pesquisa": coletar_pesquisa, "extensao": coletar_extensao}
