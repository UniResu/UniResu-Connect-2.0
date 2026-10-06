"""
Parser das páginas públicas dos portais da UNIRIO (pesquisa e extensão).

Funções puras: recebem HTML (str) e devolvem dicts. Não fazem rede — o fluxo
de requisições fica em `scraper.py`, o que permite testar com HTML salvo.

Os portais são aplicações PHP comuns (sem ViewState): listagem via GET com
paginação por link e detalhe em URL estável, por exemplo
`/extensao/detalhes/index?ID_PROJETO=8620`.

Os rótulos dos campos de detalhe variam entre os dois portais, então o
mapeamento é feito por palavras-chave (ver `_MAPA_DETALHE`).
"""

import re
from datetime import date, datetime
from typing import Optional
from urllib.parse import parse_qs, urljoin, urlparse

from bs4 import BeautifulSoup

from services.sigaa.parser import SITUACAO_EM_EXECUCAO, limpar, normalizar

BASE_PESQUISA = "https://sistemas.unirio.br"
BASE_EXTENSAO = "https://sistemas2.unirio.br"

_RE_EMAIL = re.compile(r"[\w.+-]+@[\w-]+(?:\.[\w-]+)+")
_RE_DATA = re.compile(r"(\d{2}/\d{2}/\d{4})")
_RE_ANO = re.compile(r"\b(20\d{2}|19\d{2})\b")
_RE_ID_URL = re.compile(r"(?:ID_PROJETO|id_projeto|id|ID|codigo)=(\d+)|/(\d+)(?:/|$|\?)")

# Textos de link que indicam "próxima página" nas paginações comuns em PHP.
_PROXIMA = {"PROXIMA", "PROXIMO", ">", ">>", "»", "NEXT", "PROXIMA PAGINA", "SEGUINTE"}


def _soup(html: str) -> BeautifulSoup:
    return BeautifulSoup(html, "html.parser")


# ─────────────────────────────────────────────
#  Utilidades
# ─────────────────────────────────────────────

def id_da_url(url: Optional[str]) -> Optional[str]:
    """Extrai o id numérico do projeto de uma URL de detalhe."""
    if not url:
        return None
    qs = parse_qs(urlparse(url).query)
    for chave in ("ID_PROJETO", "id_projeto", "id", "ID", "codigo"):
        if qs.get(chave):
            return qs[chave][0]
    m = re.search(r"/(\d+)/?$", urlparse(url).path)
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
        if any(p in v for p in ("ANDAMENTO", "EXECUCAO", "ATIVO", "VIGENTE", "APROVADO", "EM CURSO")):
            return SITUACAO_EM_EXECUCAO
        if any(p in v for p in ("CONCLU", "FINALIZ", "ENCERR", "CANCEL", "INATIV", "SUSPENS", "INDEFER")):
            return "FINALIZADO"
        return limpar(valor).upper()
    if inicio and fim:
        hoje = hoje or date.today()
        if hoje < date.fromisoformat(inicio):
            return "NÃO INICIADO"
        if hoje > date.fromisoformat(fim):
            return "FINALIZADO"
        return SITUACAO_EM_EXECUCAO
    return None


# ─────────────────────────────────────────────
#  Listagens
# ─────────────────────────────────────────────

def _eh_link_detalhe(href: str, modulo: str) -> bool:
    h = href.lower()
    if modulo == "extensao":
        return "detalhes" in h and "id_projeto" in h
    # Portal da Pesquisa: /projetos/<controller>/view?id=N ou /projetos/view/N
    return "/projetos/" in h and ("view" in h or "detal" in h or "visualiz" in h) and bool(id_da_url(href))


def links_de_detalhe(html: str, modulo: str, base: str) -> list[str]:
    """Todos os links de detalhe da página, na ordem, sem repetição (usado no modo captura)."""
    vistos: list[str] = []
    for a in _soup(html).find_all("a", href=True):
        url = urljoin(base, a["href"])
        if _eh_link_detalhe(url, modulo) and url not in vistos:
            vistos.append(url)
    return vistos


def _linha_do_link(a):
    """Linha (tr) ou bloco (li/div/article) que contém o link de detalhe."""
    return a.find_parent("tr") or a.find_parent(["li", "article"]) or a.find_parent("div")


def parse_listagem(html: str, modulo: str, base: str) -> list[dict]:
    """Itens da listagem: título + link de detalhe + colunas da linha.

    Cada linha/bloco com um link de detalhe vira um item. As demais células
    da linha vão em `colunas` (texto limpo), e o parser tenta reconhecer
    ano, unidade e coordenador por heurística; o detalhe completa o resto.
    """
    soup = _soup(html)
    itens: list[dict] = []
    vistos: set[str] = set()
    for a in soup.find_all("a", href=True):
        url = urljoin(base, a["href"])
        if not _eh_link_detalhe(url, modulo):
            continue
        id_ = id_da_url(url)
        if not id_ or id_ in vistos:
            continue
        titulo = limpar(a.get_text(" "))
        linha = _linha_do_link(a)
        colunas = []
        if linha is not None:
            celulas = linha.find_all(["td", "th"]) if linha.name == "tr" else linha.find_all(["p", "span", "div"])
            colunas = [limpar(c.get_text(" ")) for c in celulas]
            colunas = [c for c in colunas if c and c != titulo]
        if not titulo and colunas:
            titulo = colunas[0]
        if not titulo:
            continue
        vistos.add(id_)
        itens.append({
            "unirio_id": id_,
            "titulo": titulo,
            "link_detalhe": url,
            "ano": next((ano_de(c) for c in colunas if ano_de(c) and len(c) <= 12), None),
            "colunas": colunas,
        })
    return itens


def proxima_pagina(html: str, url_atual: str) -> Optional[str]:
    """URL da próxima página da listagem, ou None na última."""
    soup = _soup(html)
    a = soup.find("a", rel=lambda r: r and "next" in [x.lower() for x in (r if isinstance(r, list) else [r])])
    if a and a.get("href"):
        return urljoin(url_atual, a["href"])
    for a in soup.find_all("a", href=True):
        texto = normalizar(a.get_text(" "))
        if texto in _PROXIMA or (a.get("aria-label") and normalizar(a["aria-label"]) in _PROXIMA):
            if "javascript" in a["href"].lower() or a["href"] in ("#", ""):
                continue
            classes = " ".join(a.get("class") or []) + " " + " ".join((a.parent.get("class") or []) if a.parent else [])
            if "disabled" in classes.lower():
                return None
            return urljoin(url_atual, a["href"])
    return None


# ─────────────────────────────────────────────
#  Detalhe
# ─────────────────────────────────────────────

# (palavras no rótulo normalizado) -> campo do registro
_MAPA_DETALHE = [
    (("COORDENADOR", "RESPONSAVEL", "PROPONENTE", "DOCENTE RESPONSAVEL"), "coordenador"),
    (("E-MAIL", "EMAIL"), "email_raw"),
    (("UNIDADE", "CENTRO", "DEPARTAMENTO", "ESCOLA", "INSTITUTO", "LOTACAO"), "unidade"),
    (("SITUACAO", "STATUS"), "situacao_raw"),
    (("PERIODO", "VIGENCIA", "DURACAO"), "periodo_raw"),
    (("INICIO",), "inicio_raw"),
    (("TERMINO", "FIM", "CONCLUSAO"), "fim_raw"),
    (("RESUMO", "DESCRICAO", "OBJETIVO", "APRESENTACAO", "JUSTIFICATIVA"), "descricao"),
    (("PALAVRA",), "palavras_chave_raw"),
    (("AREA", "LINHA"), "area_tematica"),
    (("TITULO",), "titulo"),
    (("ANO",), "ano"),
    (("TIPO", "MODALIDADE", "NATUREZA"), "categoria"),
]


def _pares_rotulo_valor(soup: BeautifulSoup) -> dict:
    """Mapa {RÓTULO NORMALIZADO: valor} a partir de th/td, dt/dd, label/+texto e
    blocos "Rótulo: valor"."""
    campos: dict = {}

    def guardar(rotulo, valor):
        r = normalizar(rotulo).rstrip(":").strip()
        v = limpar(valor)
        if r and v and r not in campos:
            campos[r] = v

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
    for tag in soup.find_all(["label", "strong", "b", "h4", "h5", "dt"]):
        rotulo = limpar(tag.get_text(" "))
        if not rotulo or len(rotulo) > 60:
            continue
        # "Rótulo:" seguido do valor no mesmo bloco ou no irmão seguinte
        pai = tag.parent
        if pai is None:
            continue
        texto_pai = limpar(pai.get_text(" "))
        if texto_pai.startswith(rotulo) and len(texto_pai) > len(rotulo) + 1:
            guardar(rotulo, texto_pai[len(rotulo):].lstrip(" :"))
            continue
        irmao = tag.find_next_sibling()
        if irmao is not None and rotulo.endswith(":"):
            guardar(rotulo, irmao.get_text(" "))
    return campos


def _mapear(campos: dict) -> dict:
    saida: dict = {}
    for rotulo, valor in campos.items():
        for palavras, campo in _MAPA_DETALHE:
            if any(p in rotulo for p in palavras) and campo not in saida:
                saida[campo] = valor
                break
    return saida


def parse_detalhe(html: str, hoje: Optional[date] = None) -> dict:
    soup = _soup(html)
    m = _mapear(_pares_rotulo_valor(soup))
    if not m:
        raise ValueError("Página de detalhe da UNIRIO inesperada (nenhum campo reconhecido).")
    inicio, fim = periodo(m.get("periodo_raw"))
    if not inicio:
        inicio, _ = periodo(m.get("inicio_raw"))
    if not fim:
        fim, _ = periodo(m.get("fim_raw"))
    palavras = [limpar(p) for p in re.split(r"[;,|]", m.get("palavras_chave_raw") or "") if limpar(p)]
    return {
        "titulo": m.get("titulo") or None,
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
            "palavras_chave": palavras or None,
        }.items() if v},
    }
