"""
Parser das páginas públicas dos portais da UNIRIO (pesquisa e extensão).

Funções puras: recebem HTML (str) e devolvem dicts. Não fazem rede — o fluxo
de requisições fica em `scraper.py`, o que permite testar com HTML salvo.

Os portais são aplicações PHP comuns (sem ViewState): listagem via GET com
paginação por link e detalhe em URL estável, por exemplo
`/extensao/detalhes/index?ID_PROJETO=8620`.

Os rótulos dos campos de detalhe variam entre os dois portais, então o
mapeamento é feito por palavras-chave casadas por palavra inteira
(ver `_MAPA_DETALHE`). Enquanto o HTML real não for capturado
(`python -m jobs.sync_unirio --captura`), tudo aqui é heurística defensiva:
na dúvida o parser prefere devolver menos (o job marca falha e alerta) a
inventar projetos.
"""

import re
from datetime import date, datetime
from typing import Optional
from urllib.parse import parse_qs, urljoin, urlparse

from bs4 import BeautifulSoup, NavigableString, Tag

from services.sigaa.parser import SITUACAO_EM_EXECUCAO, limpar, normalizar

_RE_EMAIL = re.compile(r"[\w.+-]+@[\w-]+(?:\.[\w-]+)+")
_RE_DATA = re.compile(r"(\d{2}/\d{2}/\d{4})")
_RE_ANO = re.compile(r"\b(20\d{2}|19\d{2})\b")

# Nomes de parâmetro de id aceitos nas URLs de detalhe (comparados em minúsculas).
_CHAVES_ID = ("id_projeto", "idprojeto", "projeto_id", "id", "codigo", "cod")
# Última parte do caminho que identifica uma ação de detalhe (Yii/CakePHP/Laravel).
_ACOES_DETALHE = {"view", "detalhe", "detalhes", "visualizar", "show", "detail", "exibir"}

# Textos de link que NÃO são título (botões "ver detalhes" etc.).
_TITULO_GENERICO = {
    "", "+", ">", "»", "›", "DETALHES", "DETALHE", "VER", "VER MAIS", "VER DETALHES", "VISUALIZAR",
    "ABRIR", "ACESSAR", "ACESSE", "SAIBA MAIS", "MAIS", "VIEW", "EXIBIR", "CONSULTAR", "VER PROJETO",
}

# Paginação: palavras (só letras, prefixo) e glifos de "próxima página".
_PROXIMA_PALAVRAS = ("PROXIM", "NEXT", "SEGUINTE", "AVANCAR")
_PROXIMA_GLIFOS = {">", "›", "»"}

# Situação: os negativos são testados ANTES dos positivos ("INATIVO" contém "ATIVO").
_SITUACOES_NEGATIVAS = ("CONCLU", "FINALIZ", "ENCERR", "CANCEL", "INATIV", "DESATIV", "SUSPENS",
                        "INDEFER", "REPROV", "NAO APROV", "ARQUIV", "EXPIR")
_SITUACOES_POSITIVAS = ("ANDAMENTO", "EXECUCAO", "ATIVO", "ATIVA", "VIGENTE", "APROVADO", "EM CURSO")


def _soup(html: str) -> BeautifulSoup:
    return BeautifulSoup(html, "html.parser")


# ─────────────────────────────────────────────
#  Utilidades
# ─────────────────────────────────────────────

def id_da_url(url: Optional[str]) -> Optional[str]:
    """Extrai o id numérico do projeto de uma URL de detalhe (query ou caminho)."""
    if not url:
        return None
    partes = urlparse(url)
    qs = {k.lower(): v for k, v in parse_qs(partes.query).items()}
    for chave in _CHAVES_ID:
        valores = qs.get(chave)
        if valores and valores[0].strip().isdigit():
            return valores[0].strip()
    m = re.search(r"/(\d+)/?$", partes.path)
    return m.group(1) if m else None


def email(valor: Optional[str]) -> Optional[str]:
    m = _RE_EMAIL.search(valor or "")
    return m.group(0).lower() if m else None


def periodo(valor: Optional[str]) -> tuple[Optional[str], Optional[str]]:
    datas = _RE_DATA.findall(valor or "")
    iso = []
    for d in datas[:2]:
        try:
            iso.append(datetime.strptime(d, "%d/%m/%Y").date().isoformat())
        except ValueError:
            continue
    return (iso[0] if iso else None, iso[1] if len(iso) > 1 else None)


def ano_de(texto: Optional[str]) -> Optional[str]:
    m = _RE_ANO.search(texto or "")
    return m.group(1) if m else None


def situacao_normalizada(valor: Optional[str], inicio: Optional[str] = None, fim: Optional[str] = None,
                         hoje: Optional[date] = None) -> Optional[str]:
    """Traduz o status do portal para o vocabulário usado na listagem
    ("EM EXECUÇÃO" habilita o projeto na busca padrão)."""
    v = normalizar(valor)
    if v:
        if any(p in v for p in _SITUACOES_NEGATIVAS):
            return "FINALIZADO"
        if any(p in v for p in _SITUACOES_POSITIVAS):
            return SITUACAO_EM_EXECUCAO
        return limpar(valor).upper()
    if inicio and fim:
        hoje = hoje or date.today()
        if hoje < date.fromisoformat(inicio):
            return "NÃO INICIADO"
        if hoje > date.fromisoformat(fim):
            return "FINALIZADO"
        return SITUACAO_EM_EXECUCAO
    return None


def prefixo_do_controller(url_listagem: str) -> str:
    """Diretório do controller da listagem: ".../projetos/search/index" → "/projetos/search/"."""
    caminho = urlparse(url_listagem).path or "/"
    return caminho.rsplit("/", 1)[0] + "/"


# ─────────────────────────────────────────────
#  Links de detalhe
# ─────────────────────────────────────────────

def _eh_link_detalhe(url: str, modulo: str, prefixo: Optional[str] = None) -> bool:
    partes = urlparse(url)
    caminho = partes.path.lower()
    if modulo == "extensao":
        # /extensao/detalhes/index?ID_PROJETO=8620
        return "detalhes" in caminho and id_da_url(url) is not None
    # Portal da Pesquisa (Yii): só links do mesmo controller da listagem
    # (ex.: /projetos/search/view?id=5), para não confundir perfis de pessoas
    # ou unidades (/projetos/pessoa/view?id=7) com projetos.
    if prefixo and not caminho.startswith(prefixo.lower()):
        return False
    segmentos = [s for s in caminho.split("/") if s]
    if not segmentos:
        return False
    acao = segmentos[-2] if segmentos[-1].isdigit() and len(segmentos) >= 2 else segmentos[-1]
    return acao in _ACOES_DETALHE and id_da_url(url) is not None


def _chave_link(url: str) -> str:
    return urlparse(url).path.lower() + "|" + (id_da_url(url) or "")


def links_de_detalhe(html: str, modulo: str, url_pagina: str, prefixo: Optional[str] = None) -> list[str]:
    """Todos os links de detalhe da página, na ordem, sem repetição (usado no modo captura)."""
    vistos: list[str] = []
    for a in _soup(html).find_all("a", href=True):
        url = urljoin(url_pagina, a["href"])
        if _eh_link_detalhe(url, modulo, prefixo) and url not in vistos:
            vistos.append(url)
    return vistos


# ─────────────────────────────────────────────
#  Listagem
# ─────────────────────────────────────────────

# Cabeçalho da tabela → campo do item (casamento por palavra inteira).
_MAPA_COLUNAS = [
    (("TITULO", "PROJETO", "NOME"), "titulo"),
    (("COORDENADOR", "RESPONSAVEL", "PROPONENTE", "DOCENTE"), "coordenador"),
    (("UNIDADE", "CENTRO", "ESCOLA", "INSTITUTO", "DEPARTAMENTO", "LOTACAO"), "unidade"),
    (("SITUACAO", "STATUS"), "situacao"),
    (("ANO",), "ano"),
]


def _casa_palavra(palavra: str, texto: str) -> bool:
    """`palavra` aparece em `texto` como palavra inteira, aceitando sufixos
    simples (COORDENADORA, OBJETIVOS, PALAVRAS-CHAVE)."""
    return re.search(rf"(?<![A-Z]){re.escape(palavra)}(?:A|AS|O|OS|S|ES)?(?![A-Z])", texto) is not None


def _titulo_generico(texto: str) -> bool:
    n = normalizar(texto)
    return n in _TITULO_GENERICO or len(n) < 4 or n.isdigit()


def _parece_status_ou_data(texto: str) -> bool:
    n = normalizar(texto)
    return bool(_RE_DATA.search(n)) or any(p in n for p in _SITUACOES_NEGATIVAS + _SITUACOES_POSITIVAS)


def _cabecalhos(tabela: Tag) -> list[str]:
    """Textos normalizados dos <th> da primeira linha de cabeçalho da tabela."""
    for tr in tabela.find_all("tr"):
        ths = tr.find_all("th", recursive=False)
        if ths:
            return [normalizar(th.get_text(" ")) for th in ths]
    return []


def _campos_por_cabecalho(cabecalhos: list[str], celulas: list[str]) -> dict:
    campos: dict = {}
    for i, cab in enumerate(cabecalhos):
        if i >= len(celulas) or not celulas[i]:
            continue
        for palavras, campo in _MAPA_COLUNAS:
            if campo not in campos and any(_casa_palavra(p, cab) for p in palavras):
                campos[campo] = celulas[i]
                break
    return campos


def _linha_do_link(a: Tag):
    """Linha (tr) ou bloco (li/article/div) que contém o link de detalhe."""
    return a.find_parent("tr") or a.find_parent(["li", "article"]) or a.find_parent("div")


_RE_UNIDADE = re.compile(r"^(DEPARTAMENTO|CENTRO|ESCOLA|INSTITUTO|COORDENADORIA|FACULDADE|NUCLEO|PRO-REITORIA|"
                         r"PROGRAMA|LABORATORIO|BIBLIOTECA|ARQUIVO|AUDITORIA|HOSPITAL|REITORIA|DECANIA)\b")


def _campos_por_heuristica(colunas: list[str]) -> dict:
    """Blocos sem cabeçalho (ex.: `<li class="list-group-item">` do Portal da
    Extensão, com <small>unidade</small>, <small>COORDENADORES</small>,
    <small>ano</small>): reconhece ano (4 dígitos), coordenador (texto todo em
    caixa alta, como os portais exibem nomes), unidade (começa com
    Departamento/Centro/Escola...) e situação (vocabulário de status)."""
    campos: dict = {}
    for c in colunas:
        n = normalizar(c)
        if re.fullmatch(r"\d{4}", c):
            campos.setdefault("ano", c)
        elif _RE_UNIDADE.match(n):
            campos.setdefault("unidade", c)
        elif len(c) < 40 and any(p in n for p in _SITUACOES_NEGATIVAS + _SITUACOES_POSITIVAS):
            campos.setdefault("situacao", c)
        elif c.upper() == c and re.search(r"[A-Z]{3,}", n) and len(c) > 5 and not _RE_DATA.search(c):
            campos.setdefault("coordenador", c)
    return campos


def _escolher_titulo(texto_link: str, colunas: list[str], por_cabecalho: dict) -> Optional[str]:
    if por_cabecalho.get("titulo") and not _titulo_generico(por_cabecalho["titulo"]):
        return por_cabecalho["titulo"]
    if not _titulo_generico(texto_link):
        return texto_link
    candidatos = [c for c in colunas if not _titulo_generico(c) and not _parece_status_ou_data(c)
                  and not ano_de(c) == c]
    return max(candidatos, key=len) if candidatos else None


def parse_listagem(html: str, modulo: str, url_pagina: str, prefixo_detalhe: Optional[str] = None) -> list[dict]:
    """Itens da listagem: título + link de detalhe + colunas reconhecidas.

    Cada linha/bloco com um link de detalhe vira um item. Quando a tabela tem
    cabeçalho, as células são mapeadas por ele (título, coordenador, unidade,
    situação, ano); sem cabeçalho, o título é o texto do link (se não for um
    botão genérico) ou a maior célula de texto da linha. Linhas sem título
    utilizável são descartadas: melhor faltar do que gravar "Detalhes" como
    projeto. Os hrefs são resolvidos contra a URL da própria página.
    """
    soup = _soup(html)
    itens: list[dict] = []
    vistos: set[str] = set()
    cabecalhos_por_tabela: dict[int, list[str]] = {}

    for a in soup.find_all("a", href=True):
        url = urljoin(url_pagina, a["href"])
        if not _eh_link_detalhe(url, modulo, prefixo_detalhe):
            continue
        id_ = id_da_url(url)
        chave = _chave_link(url)
        if not id_ or chave in vistos:
            continue

        texto_link = limpar(a.get_text(" "))
        linha = _linha_do_link(a)
        colunas: list[str] = []
        por_cabecalho: dict = {}
        if linha is not None:
            if linha.name == "tr":
                celulas = [limpar(td.get_text(" ")) for td in linha.find_all(["td", "th"], recursive=False)]
                tabela = linha.find_parent("table")
                if tabela is not None:
                    cabecalhos = cabecalhos_por_tabela.setdefault(id(tabela), _cabecalhos(tabela))
                    por_cabecalho = _campos_por_cabecalho(cabecalhos, celulas)
            else:
                celulas = [limpar(c.get_text(" ")) for c in linha.find_all(["p", "span", "div", "small", "h3", "h4", "h5"])]
            colunas = [c for c in celulas if c and c != texto_link]
            if not por_cabecalho:
                por_cabecalho = _campos_por_heuristica(colunas)

        titulo = _escolher_titulo(texto_link, colunas, por_cabecalho)
        if not titulo:
            continue
        vistos.add(chave)
        ano = ano_de(por_cabecalho.get("ano")) or next(
            (ano_de(c) for c in colunas if ano_de(c) and len(c) <= 12), None)
        itens.append({
            "unirio_id": id_,
            "titulo": titulo,
            "link_detalhe": url,
            "coordenador": por_cabecalho.get("coordenador"),
            "unidade": por_cabecalho.get("unidade"),
            "situacao": situacao_normalizada(por_cabecalho.get("situacao")) if por_cabecalho.get("situacao") else None,
            "ano": ano,
            "colunas": colunas,
        })
    return itens


def total_resultados(html: str) -> Optional[int]:
    """Total anunciado pela busca ("(386 resultados)"), se houver — serve de
    conferência da paginação."""
    m = re.search(r"\(?\s*(\d[\d.]*)\s+resultados?\s*\)?", _soup(html).get_text(" "), re.I)
    return int(m.group(1).replace(".", "")) if m else None


def _desabilitado(a: Tag) -> bool:
    classes = " ".join(a.get("class") or [])
    if isinstance(a.parent, Tag):
        classes += " " + " ".join(a.parent.get("class") or [])
    return "disabled" in classes.lower() or (a.get("aria-disabled") or "").lower() == "true"


def _eh_proxima(a: Tag) -> bool:
    href = (a.get("href") or "").strip()
    if not href or href.startswith("#") or href.lower().startswith("javascript"):
        return False
    if _desabilitado(a):
        return False
    rels = a.get("rel") or []
    if any(r.lower() == "next" for r in (rels if isinstance(rels, list) else [rels])):
        return True
    for texto in (a.get_text(" "), a.get("aria-label") or "", a.get("title") or ""):
        n = normalizar(texto)
        letras = re.sub(r"[^A-Z]", "", n)
        if letras:
            if any(letras.startswith(p) for p in _PROXIMA_PALAVRAS):
                return True
        elif n.strip() in _PROXIMA_GLIFOS:
            return True
    classes = (" ".join(a.get("class") or []) + " "
               + (" ".join(a.parent.get("class") or []) if isinstance(a.parent, Tag) else "")).lower()
    return re.search(r"(^|[\s_-])next([\s_-]|$)", classes) is not None


def proxima_pagina(html: str, url_atual: str) -> Optional[str]:
    """URL da próxima página da listagem, ou None na última.

    Reconhece rel="next", rótulos "Próxima", "Próximo »", "Next >", "Seguinte",
    glifos isolados (›, », >) e classes `next` (Bootstrap/Yii), ignorando links
    desabilitados, `#` e `javascript:`. ">>"/"»»" costumam ser "última" e não contam.
    """
    for a in _soup(html).find_all("a", href=True):
        if _eh_proxima(a):
            destino = urljoin(url_atual, a["href"])
            return destino if destino != url_atual else None
    return None


# ─────────────────────────────────────────────
#  Detalhe
# ─────────────────────────────────────────────

# (palavras do rótulo, campo, palavras que excluem o rótulo) — ordem importa:
# E-MAIL antes de COORDENADOR ("E-mail do coordenador"), ANO antes de INÍCIO/TÉRMINO,
# LINHA antes de ÁREA ("Linhas de extensão" não é a área temática).
_MAPA_DETALHE = [
    (("E-MAIL", "EMAIL", "E MAIL"), "email_raw", ()),
    (("TITULO",), "titulo", ()),
    (("PROCESSO", "CODIGO"), "codigo", ()),
    (("COORDENADOR", "RESPONSAVEL", "PROPONENTE", "DOCENTE"), "coordenador",
     ("VICE", "ADJUNTO", "TELEFONE", "LATTES", "SUBSTITUTO")),
    (("UNIDADE", "CENTRO", "DEPARTAMENTO", "ESCOLA", "INSTITUTO", "LOTACAO", "FACULDADE"), "unidade",
     ("CUSTO", "COMUNIDADE", "ESCOLARIDADE", "ATENDIDA")),
    (("SITUACAO", "STATUS"), "situacao_raw", ()),
    (("ANO",), "ano", ()),
    (("PERIODO", "VIGENCIA", "DURACAO"), "periodo_raw", ()),
    (("INICIO",), "inicio_raw", ()),
    (("TERMINO", "FIM", "CONCLUSAO", "ENCERRAMENTO"), "fim_raw", ()),
    (("RESUMO", "DESCRICAO", "OBJETIVO", "APRESENTACAO", "JUSTIFICATIVA"), "descricao", ()),
    (("PALAVRA",), "palavras_chave_raw", ()),
    (("LINHA",), "linhas_raw", ()),
    (("AREA", "TEMATICA"), "area_tematica", ()),
    (("FINANCIAMENTO",), "financiamento", ()),
    (("TIPO", "MODALIDADE", "NATUREZA"), "categoria", ("BOLSA",)),
]

# Cards (seções) da ficha cujos rótulos não são do projeto, e sim de outras
# pessoas/anexos — "Situação" e "E-mail" ali são dos participantes.
_CARDS_IGNORADOS = ("PARTICIPANTE", "ARQUIVO", "EQUIPE", "MEMBRO", "BOLSISTA", "ANEXO")

_ROTULOS = ("label", "strong", "b", "h4", "h5")
_BLOCOS = {"p", "div", "li", "tr", "td", "table", "ul", "ol", "dl", "dt", "dd", "section", "article",
           "h1", "h2", "h3", "h4", "h5", "h6", "hr", "form", "fieldset"}


def _valor_apos(tag: Tag) -> str:
    """Texto que segue o rótulo dentro do mesmo pai, até um <br>, um bloco ou
    outro rótulo. Para `<strong>Coordenador:</strong> Fulano<br><strong>E-mail:</strong>…`
    devolve só "Fulano"."""
    partes: list[str] = []
    for no in tag.next_siblings:
        if isinstance(no, NavigableString):
            partes.append(str(no))
        elif isinstance(no, Tag):
            if no.name == "br":
                if limpar(" ".join(partes)):
                    break
                continue
            if no.name in _ROTULOS or no.name in _BLOCOS:
                break
            partes.append(no.get_text(" "))
    return limpar(" ".join(partes))


def _guardar_em(campos: dict, rotulo, valor) -> None:
    r = normalizar(rotulo).rstrip(":").strip()
    v = limpar(valor)
    if re.fullmatch(r"[-–—.*/]+", v):  # "-" = campo vazio nos portais
        v = ""
    if r and v and r not in campos:
        campos[r] = v


def _valor_de_bloco(tag: Tag) -> str:
    """Valor de um bloco da ficha: texto do <p>, ou itens de uma <ul> separados por ';'."""
    if tag.name in ("ul", "ol"):
        return "; ".join(limpar(li.get_text(" ")) for li in tag.find_all("li") if limpar(li.get_text(" ")))
    return limpar(tag.get_text(" "))


def _pares_ficha(soup: BeautifulSoup) -> dict:
    """Layout dos portais da UNIRIO (Bootstrap): cards com <h4> no card-header
    e, no card-body, pares `<p class="card-subtitle titulo_ficha">Rótulo:</p>`
    seguidos do valor em `<p class="card-text">` ou `<ul>`. Cards de
    participantes/arquivos são ignorados (seus rótulos repetem os do projeto)."""
    campos: dict = {}
    for card in soup.select("div.card"):
        cabecalho = card.find(class_="card-header")
        titulo_card = normalizar(cabecalho.get_text(" ")) if cabecalho else ""
        if any(p in titulo_card for p in _CARDS_IGNORADOS):
            continue
        corpo = card.find(class_="card-body") or card
        for rotulo in corpo.select("p.titulo_ficha, p.card-subtitle"):
            valor = rotulo.find_next_sibling()
            if valor is not None and not (valor.get("class") and "titulo_ficha" in valor.get("class")):
                _guardar_em(campos, rotulo.get_text(" "), _valor_de_bloco(valor))
    return campos


def _pares_rotulo_valor(soup: BeautifulSoup) -> dict:
    """Mapa {RÓTULO NORMALIZADO: valor} a partir de th/td, dt/dd, linhas de
    duas células e rótulos em label/strong/b/h4/h5 (valor no texto seguinte,
    no bloco irmão ou na seção seguinte). Fallback genérico para layouts que
    não sejam a ficha em cards (`_pares_ficha`)."""
    campos: dict = {}

    def guardar(rotulo, valor):
        _guardar_em(campos, rotulo, valor)

    for th in soup.find_all("th"):
        td = th.find_next_sibling("td")
        if td is not None:
            guardar(th.get_text(" "), td.get_text(" "))
    for dt in soup.find_all("dt"):
        dd = dt.find_next_sibling("dd")
        if dd is not None:
            guardar(dt.get_text(" "), dd.get_text(" "))
    for tr in soup.find_all("tr"):
        tds = tr.find_all("td", recursive=False)
        if len(tds) == 2:
            guardar(tds[0].get_text(" "), tds[1].get_text(" "))
    for tag in soup.find_all(list(_ROTULOS)):
        rotulo = limpar(tag.get_text(" "))
        if not rotulo or len(rotulo) > 60:
            continue
        if tag.name in ("h4", "h5"):
            # Títulos de seção ("Resumo", "Objetivos") não levam ":" — o valor é
            # o bloco seguinte, como em services.sigaa.parser._secao_h4.
            irmao = tag.find_next_sibling()
            if irmao is not None and irmao.name not in ("h1", "h2", "h3", "h4", "h5", "h6"):
                guardar(rotulo, irmao.get_text(" "))
            continue
        valor = _valor_apos(tag)
        pai = tag.parent
        if not valor and isinstance(pai, Tag) and limpar(pai.get_text(" ")) == rotulo:
            # Rótulo sozinho no seu bloco (ex.: <div class="col-md-3"><strong>Coordenador:</strong></div>
            # <div class="col-md-9">valor</div>): o valor está no bloco irmão.
            irmao = pai.find_next_sibling()
            if irmao is not None:
                valor = limpar(irmao.get_text(" "))
        if valor:
            guardar(rotulo, valor)
    return campos


def _mapear(campos: dict) -> dict:
    """Rótulos → campos do registro. Duas passadas: rótulo igual à palavra, depois
    palavra inteira dentro do rótulo; o primeiro rótulo que casa vence."""
    saida: dict = {}

    def tentar(exato: bool):
        for rotulo, valor in campos.items():
            for palavras, campo, negativas in _MAPA_DETALHE:
                if campo in saida or any(_casa_palavra(n, rotulo) for n in negativas):
                    continue
                casou = (rotulo in palavras) if exato else any(_casa_palavra(p, rotulo) for p in palavras)
                if casou:
                    saida[campo] = valor
                    break

    tentar(exato=True)
    tentar(exato=False)
    return saida


def _lista(valor: Optional[str], separadores: str = r"[;,|]") -> list[str]:
    return [limpar(p) for p in re.split(separadores, valor or "") if limpar(p)]


def parse_detalhe(html: str, hoje: Optional[date] = None) -> dict:
    soup = _soup(html)
    campos = _pares_ficha(soup) or _pares_rotulo_valor(soup)
    m = _mapear(campos)
    if not m:
        raise ValueError("Página de detalhe da UNIRIO inesperada (nenhum campo reconhecido).")
    inicio, fim = periodo(m.get("periodo_raw"))
    if not inicio:
        inicio, _ = periodo(m.get("inicio_raw"))
    if not fim:
        fim, _ = periodo(m.get("fim_raw"))
    return {
        "titulo": m.get("titulo") or None,
        "codigo": m.get("codigo") or None,
        "coordenador": m.get("coordenador") or None,
        "email": email(m.get("email_raw")),
        "unidade": m.get("unidade") or None,
        "situacao": situacao_normalizada(m.get("situacao_raw"), inicio, fim, hoje),
        "periodo_inicio": inicio,
        "periodo_fim": fim,
        "descricao": m.get("descricao") or None,
        "categoria": m.get("categoria") or None,
        "ano": ano_de(m.get("ano")) or ano_de(inicio),
        "extras": {k: v for k, v in {
            "area_tematica": m.get("area_tematica") or None,
            # itens de <ul> chegam separados por ";" e podem conter vírgulas
            "linhas_extensao": _lista(m.get("linhas_raw"), r"[;|]") or None,
            "palavras_chave": _lista(m.get("palavras_chave_raw")) or None,
            "financiamento": m.get("financiamento") or None,
        }.items() if v},
    }
