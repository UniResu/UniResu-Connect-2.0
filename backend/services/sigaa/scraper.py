"""
Coleta de projetos das consultas públicas do SIGAA/UNIR.

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

URLS = {
    "pesquisa": parser.BASE_URL + "/sigaa/public/pesquisa/consulta_projetos.jsf?aba=p-pesquisa",
    "extensao": parser.BASE_URL + "/sigaa/public/extensao/consulta_extensao.jsf?acao=2&aba=p-extensao",
}


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


# ─────────────────────────────────────────────
#  Busca (listagem)
# ─────────────────────────────────────────────

def montar_payload_busca(html_form: str, modulo: str, ano: str, situacao: Optional[str]) -> dict:
    """Monta o POST da busca a partir do HTML da página de consulta."""
    form = parser.achar_form(BeautifulSoup(html_form, "html.parser"))
    dados = parser.payload_base(form)
    if modulo == "pesquisa" and situacao:
        if not parser.aplicar_filtro_select(form, dados, situacao):
            raise SigaaErro(f"Opção de situação '{situacao}' não encontrada no formulário.")
    if not parser.aplicar_filtro_texto(form, dados, ["ANO"], ano):
        raise SigaaErro("Campo Ano não encontrado no formulário.")
    parser.aplicar_botao_buscar(form, dados)
    return dados


def _buscar(client: SigaaClient, modulo: str, ano: str) -> str:
    url = URLS[modulo]
    html_form = client.get(url)
    dados = montar_payload_busca(html_form, modulo, ano, client.cfg.pesquisa_situacao)
    return client.post(url, dados)


# ─────────────────────────────────────────────
#  Pesquisa
# ─────────────────────────────────────────────

def coletar_pesquisa(client: SigaaClient, ano: str) -> ResultadoColeta:
    res = ResultadoColeta("pesquisa")
    html = _buscar(client, "pesquisa", ano)
    itens = parser.parse_listagem_pesquisa(html)
    logger.info("SIGAA pesquisa %s: %d projetos na listagem", ano, len(itens))

    for item in itens:
        detalhe = None
        for tentativa in range(2):
            try:
                if tentativa == 1:
                    # O detalhe é um postback do form da listagem; se o
                    # ViewState expirou, refazemos a busca e tentamos de novo.
                    html = _buscar(client, "pesquisa", ano)
                form = parser.achar_form(BeautifulSoup(html, "html.parser"), "formConsulta")
                dados = parser.payload_base(form)
                dados.update(item.get("detalhe_params") or {})
                detalhe = parser.parse_detalhe_pesquisa(client.post(URLS["pesquisa"], dados))
                break
            except (ErroColeta, ValueError) as e:
                if tentativa == 1:
                    res.erros.append(_erro("pesquisa", item, e))
        res.itens.append(_registro("pesquisa", item, detalhe))
    return res


# ─────────────────────────────────────────────
#  Extensão
# ─────────────────────────────────────────────

def coletar_extensao(client: SigaaClient, ano: str) -> ResultadoColeta:
    res = ResultadoColeta("extensao")
    html = _buscar(client, "extensao", ano)
    todos = parser.parse_listagem_extensao(html)
    tipos = {parser.normalizar(t) for t in client.cfg.extensao_tipos}
    itens = [i for i in todos if parser.normalizar(i.get("categoria")) in tipos]
    logger.info("SIGAA extensão %s: %d ações na listagem, %d nos tipos %s",
                ano, len(todos), len(itens), sorted(tipos))

    for item in itens:
        detalhe = None
        try:
            if not item.get("link_detalhe"):
                raise SigaaErro("Item sem link de detalhe.")
            # Link público estável (GET) — não depende de ViewState.
            detalhe = parser.parse_detalhe_extensao(client.get(item["link_detalhe"]))
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
    }


def _erro(modulo: str, item: dict, e: Exception) -> dict:
    logger.warning("SIGAA %s: falha no detalhe de '%s' (id=%s): %s",
                   modulo, item.get("titulo"), item.get("sigaa_id"), e)
    return {"modulo": modulo, "sigaa_id": item.get("sigaa_id"), "titulo": item.get("titulo"), "erro": str(e)}


COLETORES = {"pesquisa": coletar_pesquisa, "extensao": coletar_extensao}
