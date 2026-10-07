"""Cliente HTTP do SIGAA (retry/backoff/throttle) e coleta com falha parcial — sem rede."""

import pytest
import requests

from conftest import ler_fixture
from services.sigaa import scraper
from services.sigaa.config import SigaaConfig
from services.sigaa.scraper import SigaaClient, SigaaErro


class Resposta:
    def __init__(self, texto="", status=200):
        self.text = texto
        self.status_code = status
        self.encoding = "ISO-8859-1"

    def raise_for_status(self):
        if self.status_code >= 400:
            raise requests.HTTPError(f"HTTP {self.status_code}")


class SessaoFalsa:
    """Devolve respostas (ou levanta exceções) na ordem configurada."""

    def __init__(self, respostas):
        self.respostas = list(respostas)
        self.headers = {}
        self.chamadas = []

    def request(self, method, url, timeout=None, **kwargs):
        self.chamadas.append((method, url, timeout))
        r = self.respostas.pop(0)
        if isinstance(r, Exception):
            raise r
        return r


class Relogio:
    def __init__(self):
        self.agora = 0.0
        self.pausas = []

    def sleep(self, s):
        self.pausas.append(s)
        self.agora += s

    def clock(self):
        return self.agora


def _cliente(respostas, **cfg):
    relogio = Relogio()
    cfg = SigaaConfig(**{"pausa_segundos": 1.5, "max_tentativas": 3, "backoff_base_segundos": 2.0, **cfg})
    sessao = SessaoFalsa(respostas)
    return SigaaClient(cfg, session=sessao, sleep=relogio.sleep, clock=relogio.clock), sessao, relogio


class TestSigaaClient:
    def test_retry_com_backoff_exponencial_ate_sucesso(self):
        cliente, sessao, relogio = _cliente([
            requests.ConnectionError("caiu"),
            Resposta(status=503),
            Resposta("ok"),
        ])
        assert cliente.get("https://sigaa/x") == "ok"
        assert len(sessao.chamadas) == 3
        # backoff 2s e 4s; o throttle não soma porque o backoff já cobre a pausa
        assert relogio.pausas == [2.0, 4.0]

    def test_esgota_tentativas_e_levanta_sigaa_erro(self):
        cliente, sessao, _ = _cliente([requests.Timeout("t")] * 3)
        with pytest.raises(SigaaErro):
            cliente.get("https://sigaa/x")
        assert len(sessao.chamadas) == 3

    def test_usa_timeout_configurado(self):
        cliente, sessao, _ = _cliente([Resposta("ok")], timeout_segundos=42)
        cliente.get("https://sigaa/x")
        assert sessao.chamadas[0][2] == 42

    def test_pausa_minima_entre_requisicoes(self):
        cliente, _, relogio = _cliente([Resposta("a"), Resposta("b"), Resposta("c")])
        cliente.get("https://sigaa/1")
        relogio.agora += 0.4  # processamento entre chamadas
        cliente.get("https://sigaa/2")
        cliente.get("https://sigaa/3")
        assert relogio.pausas == [pytest.approx(1.1), pytest.approx(1.5)]

    def test_config_nunca_permite_pausa_menor_que_1s(self, monkeypatch):
        monkeypatch.setenv("SIGAA_PAUSA_SEGUNDOS", "0.2")
        assert SigaaConfig.from_env().pausa_segundos == 1.0


class ClienteRoteado:
    """Cliente falso que responde por URL, sem throttle (para testar a coleta)."""

    def __init__(self, cfg, rotas):
        self.cfg = cfg
        self.rotas = rotas
        self.total_requisicoes = 0

    def _resp(self, url):
        self.total_requisicoes += 1
        r = self.rotas[url]
        if isinstance(r, Exception):
            raise r
        return r

    def get(self, url):
        return self._resp(url)

    def post(self, url, data):
        return self._resp(url + "#post")


def _link(id_):
    return f"https://sigaa.unir.br/sigaa/link/public/extensao/visualizacaoAcaoExtensao/{id_}"


class TestColetaExtensao:
    def _rotas(self, falha_em=None):
        listagem = ler_fixture("sigaa_extensao_listagem.html")
        detalhe = ler_fixture("sigaa_extensao_detalhe.html")
        rotas = {
            scraper.URLS["extensao"]: listagem,
            scraper.URLS["extensao"] + "#post": listagem,
        }
        for id_ in ("4527", "4534", "4712", "4019"):  # PROJETO x3 + PROGRAMA
            rotas[_link(id_)] = detalhe
        if falha_em:
            rotas[_link(falha_em)] = SigaaErro("Falha após 3 tentativas: timeout")
        return rotas

    def test_filtra_tipos_configurados(self):
        cfg = SigaaConfig(extensao_tipos=["PROJETO", "PROGRAMA"])
        res = scraper.coletar_extensao(ClienteRoteado(cfg, self._rotas()), "2026")
        assert len(res.itens) == 4
        assert {i["categoria"] for i in res.itens} == {"PROJETO", "PROGRAMA"}
        assert res.erros == []
        assert all(i["email"] == "coordenador@unir.br" and i["detalhe_ok"] for i in res.itens)

    def test_falha_em_um_detalhe_nao_aborta_e_mantem_item_da_listagem(self):
        cfg = SigaaConfig(extensao_tipos=["PROJETO", "PROGRAMA"])
        res = scraper.coletar_extensao(ClienteRoteado(cfg, self._rotas(falha_em="4534")), "2026")

        assert len(res.itens) == 4
        falho = next(i for i in res.itens if i["sigaa_id"] == "4534")
        assert falho["detalhe_ok"] is False
        assert falho["email"] is None and falho["coordenador"] is None
        assert falho["titulo"] == "MEDPOP - Informação instantânea sobre saúde"
        assert falho["unidade"] == "DNS"  # sigla da listagem
        assert res.erros == [{
            "modulo": "extensao", "sigaa_id": "4534",
            "titulo": "MEDPOP - Informação instantânea sobre saúde",
            "erro": "Falha após 3 tentativas: timeout",
        }]


class TestColetaPesquisa:
    def test_coleta_listagem_e_detalhes(self):
        listagem = ler_fixture("sigaa_pesquisa_listagem.html")
        detalhe = ler_fixture("sigaa_pesquisa_detalhe.html")
        respostas = iter([listagem, detalhe, detalhe, detalhe])

        class Cliente(ClienteRoteado):
            def get(self, url):
                return listagem

            def post(self, url, data):
                return next(respostas)

        res = scraper.coletar_pesquisa(Cliente(SigaaConfig(), {}), "2026")
        assert len(res.itens) == 3
        assert all(i["email"] == "coordenador@unir.br" for i in res.itens)
        assert res.itens[0]["codigo"] == "PVC2148-2026"
        assert res.erros == []


# ── Portais que limitam resultados e vocabulários de situação diferentes ───

FORM_PESQUISA_LIMITADO = """
<html><body><form id="formConsulta" action="/sigaa/public/pesquisa/consulta_projetos.jsf">
<input type="hidden" name="javax.faces.ViewState" value="vs1"/>
<table class="formulario">
<tr><td><input type="checkbox" name="formConsulta:chkSituacao"/></td><td>Situação do Projeto:</td>
<td><select name="formConsulta:situacaoProjeto"><option value="0">-- SELECIONE --</option>
<option value="2">Em Andamento</option><option value="5">Finalizado</option></select></td></tr>
<tr><td><input type="checkbox" name="formConsulta:chkAno"/></td><td>Ano:</td>
<td><input type="text" name="formConsulta:ano" value=""/></td></tr>
<tr><td><input type="checkbox" name="formConsulta:chkCentro"/></td><td>Centro:</td>
<td><select name="formConsulta:centro"><option value="0">-- SELECIONE UM CENTRO --</option>
<option value="15">CENTRO DE CIÊNCIAS DA SAÚDE</option><option value="17">CENTRO DE BIOCIÊNCIAS</option></select></td></tr>
</table>
<input type="submit" name="formConsulta:buscar" value="Buscar"/>
</form></body></html>
"""

EXCESSIVO = "<html><body>A consulta retornou 599 resultados. Por favor, restrinja mais a busca.</body></html>"


class ClientePortalLimitado:
    """Recusa a busca geral e só responde quando a busca vem restrita por centro."""

    def __init__(self, listagem_html):
        self.cfg = SigaaConfig(pesquisa_situacao="EM EXECUÇÃO", modulos=["pesquisa"])
        self.listagem_html = listagem_html
        self.posts = []
        self.total_requisicoes = 0

    def get(self, url, **kw):
        self.total_requisicoes += 1
        return FORM_PESQUISA_LIMITADO

    def post(self, url, data):
        self.total_requisicoes += 1
        self.posts.append(dict(data))
        if data.get("formConsulta:centro") in ("15", "17"):
            return self.listagem_html
        return EXCESSIVO


def test_busca_dividida_por_centro_e_situacao_equivalente():
    listagem = ler_fixture("sigaa_pesquisa_listagem.html")
    cliente = ClientePortalLimitado(listagem)
    paginas = scraper.buscar_paginas(cliente, "pesquisa", "2026")
    assert len(paginas) == 2 and [p.extra for p in paginas] == [("centro", "15"), ("centro", "17")]
    # "EM EXECUÇÃO" não existe no form, mas "Em Andamento" sim: o filtro é aplicado
    assert all(p.situacao_filtrada for p in paginas)
    assert cliente.posts[0]["formConsulta:situacaoProjeto"] == "2" and cliente.posts[0]["formConsulta:ano"] == "2026"
    assert cliente.posts[1]["formConsulta:centro"] == "15" and cliente.posts[1]["formConsulta:chkCentro"] == "on"


def test_helpers_de_opcoes_e_situacao():
    from bs4 import BeautifulSoup

    from services.sigaa import parser
    form = parser.achar_form(BeautifulSoup(FORM_PESQUISA_LIMITADO, "html.parser"))
    assert parser.opcoes_select(form, "centro") == [("15", "CENTRO DE CIÊNCIAS DA SAÚDE"), ("17", "CENTRO DE BIOCIÊNCIAS")]
    assert parser.opcoes_select(form, "unidade") == []
    assert parser.opcoes_de_situacao(form) == ["Em Andamento", "Finalizado"]
    assert parser.opcao_disponivel(form, ["EM EXECUÇÃO", "EM ANDAMENTO"]) == "EM ANDAMENTO"
    assert parser.resultados_excessivos(EXCESSIVO) and not parser.resultados_excessivos("<p>ok</p>")
    assert parser.situacao_vigente("EM EXECUÇÃO") and parser.situacao_vigente("Em Andamento")
    assert not parser.situacao_vigente("FINALIZADO") and not parser.situacao_vigente(None)


def test_situacao_equivalente_vira_em_execucao_e_extensao_sem_periodo_conta_como_vigente():
    from datetime import date

    item = {"sigaa_id": "1", "titulo": "P", "situacao": "EM ANDAMENTO", "ano": str(date.today().year)}
    assert scraper._registro("pesquisa", item, None)["situacao"] == "EM EXECUÇÃO"
    assert scraper._registro("pesquisa", {**item, "situacao": "FINALIZADO"}, None)["situacao"] == "FINALIZADO"


def test_erro_4xx_nao_e_repetido():
    from services.http_client import ClienteHttp, ErroDefinitivo

    class Resp:
        status_code = 404
        headers = {}
        content = b""
        text = ""

        def raise_for_status(self):
            raise AssertionError("não deveria chegar aqui")

    class Sessao:
        chamadas = 0
        headers = {}

        def request(self, *a, **kw):
            self.chamadas += 1
            return Resp()

    cfg = SigaaConfig(max_tentativas=3, pausa_segundos=1.0)
    sessao = Sessao()
    cliente = ClienteHttp(cfg, session=sessao, sleep=lambda s: None)
    with pytest.raises(ErroDefinitivo):
        cliente.get("https://x/y")
    assert sessao.chamadas == 1
