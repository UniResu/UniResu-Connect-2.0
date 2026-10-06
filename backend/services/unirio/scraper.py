"""
Coleta de projetos dos portais públicos da UNIRIO.

Fluxo (aplicações PHP, sem ViewState):
  1. GET na página de busca (com os filtros fixos da URL de referência);
  2. segue a paginação até a última página (ou o teto configurado);
  3. para cada item, GET na página de detalhe (coordenador, e-mail, período...).

Mesmas boas maneiras do SIGAA: pausa mínima entre requisições, timeout e
retry com backoff (services/http_client.py). Falha no detalhe de um item não
aborta a coleta: o item fica com os dados da listagem e o erro é registrado.
"""

import logging
from dataclasses import dataclass, field
from typing import Optional

from services.http_client import ClienteHttp, ErroColeta
from services.unirio import parser
from services.unirio.config import UnirioConfig

logger = logging.getLogger(__name__)


class UnirioErro(ErroColeta):
    """Falha de rede/HTTP após esgotar as tentativas, ou página inesperada."""


class UnirioClient(ClienteHttp):
    erro = UnirioErro
    nome = "UNIRIO"

    def __init__(self, cfg: UnirioConfig, **kwargs):
        super().__init__(cfg, **kwargs)


@dataclass
class ResultadoColeta:
    modulo: str
    itens: list[dict] = field(default_factory=list)
    erros: list[dict] = field(default_factory=list)
    paginas: int = 0


BASES = {"pesquisa": parser.BASE_PESQUISA, "extensao": parser.BASE_EXTENSAO}


def url_inicial(cfg: UnirioConfig, modulo: str) -> str:
    return cfg.url_pesquisa if modulo == "pesquisa" else cfg.url_extensao


def listar(client: UnirioClient, modulo: str) -> tuple[list[dict], int]:
    """Percorre todas as páginas da listagem. Devolve (itens, páginas lidas)."""
    cfg: UnirioConfig = client.cfg
    url = url_inicial(cfg, modulo)
    base = BASES[modulo]
    itens: list[dict] = []
    vistos: set[str] = set()
    visitadas: set[str] = set()
    paginas = 0
    while url and url not in visitadas and paginas < cfg.max_paginas:
        visitadas.add(url)
        html = client.get(url)
        paginas += 1
        novos = 0
        for item in parser.parse_listagem(html, modulo, base):
            if item["unirio_id"] not in vistos:
                vistos.add(item["unirio_id"])
                itens.append(item)
                novos += 1
        proxima = parser.proxima_pagina(html, url)
        if novos == 0 and paginas > 1:
            # Página repetida (paginação que não avança): paramos aqui.
            break
        url = proxima
    logger.info("UNIRIO %s: %d itens em %d página(s)", modulo, len(itens), paginas)
    return itens, paginas


def coletar(client: UnirioClient, modulo: str) -> ResultadoColeta:
    res = ResultadoColeta(modulo)
    itens, res.paginas = listar(client, modulo)
    limite = client.cfg.max_detalhes or len(itens)
    for i, item in enumerate(itens):
        detalhe = None
        if i < limite:
            try:
                detalhe = parser.parse_detalhe(client.get(item["link_detalhe"]))
            except (ErroColeta, ValueError) as e:
                res.erros.append(_erro(modulo, item, e))
        res.itens.append(_registro(modulo, item, detalhe))
    return res


def coletar_pesquisa(client: UnirioClient) -> ResultadoColeta:
    return coletar(client, "pesquisa")


def coletar_extensao(client: UnirioClient) -> ResultadoColeta:
    return coletar(client, "extensao")


def _registro(modulo: str, item: dict, detalhe: Optional[dict]) -> dict:
    """Registro final: dados da listagem, enriquecidos pelo detalhe se houver."""
    d = detalhe or {}
    return {
        "modulo": modulo,
        "unirio_id": item.get("unirio_id"),
        "codigo": None,
        "titulo": d.get("titulo") or item.get("titulo"),
        "coordenador": d.get("coordenador") or item.get("coordenador"),
        "email": d.get("email"),
        "unidade": d.get("unidade") or item.get("unidade"),
        "situacao": d.get("situacao") or item.get("situacao"),
        "ano": d.get("ano") or item.get("ano"),
        "categoria": d.get("categoria") or item.get("categoria"),
        "link_detalhe": item.get("link_detalhe"),
        "descricao": d.get("descricao"),
        "periodo_inicio": d.get("periodo_inicio"),
        "periodo_fim": d.get("periodo_fim"),
        "extras": d.get("extras") or {},
        "detalhe_ok": detalhe is not None,
    }


def _erro(modulo: str, item: dict, e: Exception) -> dict:
    logger.warning("UNIRIO %s: falha no detalhe de '%s' (id=%s): %s",
                   modulo, item.get("titulo"), item.get("unirio_id"), e)
    return {"modulo": modulo, "unirio_id": item.get("unirio_id"), "titulo": item.get("titulo"), "erro": str(e)}


COLETORES = {"pesquisa": coletar_pesquisa, "extensao": coletar_extensao}
