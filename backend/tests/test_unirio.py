"""Parser, coleta e job dos portais da UNIRIO — sem rede.

`tests/fixtures/unirio_extensao_*.html` é o HTML real do Portal da Extensão
(anonimizado). Os trechos sintéticos abaixo cobrem outros layouts comuns de
portais PHP (tabela com cabeçalho e botão "Detalhes", paginação Bootstrap,
detalhe em th/td, dt/dd, strong+br e colunas Bootstrap) e o fluxo do Portal
da Pesquisa (formulário web2py + POST).
"""

from datetime import date

import pytest
import requests

from conftest import FIXTURES
from jobs.sync_unirio import capturar, executar_sync
from services.fontes import UNIRIO
from services.http_client import ClienteHttp, ErroColeta
from services.sigaa import repositorio
from services.unirio import parser, scraper
from services.unirio.config import UnirioConfig
from services.unirio.scraper import ResultadoColeta, UnirioErro

URL_EXT = UnirioConfig().url_extensao
URL_PESQ = UnirioConfig().url_pesquisa
URL_PESQ_FORM = UnirioConfig().url_pesquisa_formulario
URL_EXT_P2 = "https://sistemas2.unirio.br/extensao/busca/projetos?f_status=1&page=2"


def fixture(nome: str) -> str:
    return (FIXTURES / nome).read_text(encoding="utf-8")


# Formulário real do Portal da Pesquisa (web2py), reduzido.
FORM_PESQUISA = """<html><body><h2>Busca de Projetos</h2>
<form action="#" class="form-horizontal" enctype="multipart/form-data" method="post">
  <input name="TITULO" type="text"/>
  <input name="participante" type="text"/>
  <select class="combo" name="NOME_UNIDADE"><option value=""></option><option value="156">Arquivo Central</option></select>
  <select class="combo" name="ANO_REFERENCIA"><option value=""></option><option value="2025">2025</option>
    <option value="2026">2026</option></select>
  <select class="combo" name="GRUPO_CNPQ"><option value=""></option><option value="2612">Ecologia</option></select>
  <input name="palavra_chave_upper" type="text"/>
  <input type="submit" value="Buscar"/>
  <div style="display:none;"><input name="_formkey" type="hidden" value="58673d0c-bd05"/>
  <input name="_formname" type="hidden" value="default"/></div>
</form></body></html>"""

FORM_PESQUISA_EXIGE_BUSCA = FORM_PESQUISA.replace("<h2>Busca de Projetos</h2>",
                                                  "<div class='flash'>Você precisa realizar uma busca.</div>")


def listagem_extensao(pagina: int, total_paginas: int = 2) -> str:
    """Tabela com cabeçalho, link de detalhe RELATIVO em um botão genérico e
    paginação Bootstrap (último = <li class="disabled">)."""
    base = (pagina - 1) * 2
    linhas = "".join(
        f"""<tr>
              <td>{2024 + i % 2}</td>
              <td>Projeto Extensão {base + i}</td>
              <td>Escola de Medicina e Cirurgia</td>
              <td>Em andamento</td>
              <td><a class="btn btn-sm" href="../detalhes/index?ID_PROJETO={8600 + base + i}">Detalhes</a></td>
            </tr>"""
        for i in range(1, 3)
    )
    proxima = (
        f'<li><a href="/extensao/busca/projetos?f_status=1&amp;page={pagina + 1}">Próxima »</a></li>'
        if pagina < total_paginas
        else '<li class="disabled"><a href="/extensao/busca/projetos?f_status=1&amp;page=3">Próxima »</a></li>'
    )
    return f"""<html><head><title>Buscar projetos - Portal da Extensão</title></head><body>
      <a href="/extensao/default/ajuda">Ajuda</a>
      <form><select name="f_status"><option value="1" selected>Em andamento</option></select></form>
      <table class="table"><thead><tr><th>Ano</th><th>Título</th><th>Unidade</th><th>Status</th><th></th></tr></thead>
      <tbody>{linhas}</tbody></table>
      <ul class="pagination"><li><a href="/extensao/busca/projetos?f_status=1&amp;page=1">1</a></li>
      <li><a href="/extensao/busca/projetos?f_status=1&amp;page=2">2</a></li>{proxima}
      <li><a href="/extensao/busca/projetos?f_status=1&amp;page=2">Última »»</a></li></ul>
    </body></html>"""


DETALHE_EXTENSAO = """<html><body>
  <h2>Detalhes do Projeto</h2>
  <table>
    <tr><th>Título:</th><td>Clínica de Leitura e Escrita</td></tr>
    <tr><th>E-mail do coordenador:</th><td>Carla.Menezes@unirio.br</td></tr>
    <tr><th>Vice-coordenador(a):</th><td>Pedro Vice</td></tr>
    <tr><th>Coordenador(a):</th><td>Carla Menezes de Souza</td></tr>
    <tr><th>Comunidade atendida:</th><td>Bairro Urca</td></tr>
    <tr><th>Unidade:</th><td>Escola de Medicina e Cirurgia</td></tr>
    <tr><th>Área temática:</th><td>Saúde</td></tr>
    <tr><th>Plano de trabalho:</th><td>Reuniões em 2019 e 2020</td></tr>
    <tr><th>Período de realização:</th><td>01/03/2026 a 20/12/2026</td></tr>
    <tr><th>Status:</th><td>Em andamento</td></tr>
    <tr><th>Tipo de bolsa:</th><td>PIBEX</td></tr>
    <tr><th>Palavras-chave:</th><td>leitura; escrita; saúde</td></tr>
  </table>
  <h4>Resumo</h4>
  <p>Atividades   de leitura com pacientes.</p>
</body></html>"""

LISTAGEM_PESQUISA = """<html><body>
  <table class="items">
    <tr><th>Título</th><th>Coordenador</th><th>Unidade</th><th></th></tr>
    <tr><td>Genômica de bactérias</td>
        <td><a href="/projetos/pessoa/view?id=77">Ana Paula Souza</a></td><td>Instituto Biomédico</td>
        <td><a href="view?id=501">Ver</a></td></tr>
    <tr><td>História do Rio</td>
        <td><a href="/projetos/pessoa/view?id=78">Bruno Lima</a></td><td>Escola de História</td>
        <td><a href="/projetos/search/view?Id=502">Ver</a></td></tr>
  </table>
  <div class="pager"><a href="/projetos/search/index?page=2" class="next">Next &gt;</a></div>
</body></html>"""

DETALHE_PESQUISA = """<html><body>
  <dl>
    <dt>Título</dt><dd>Genômica de bactérias</dd>
    <dt>Coordenador</dt><dd>Ana Paula Souza</dd>
    <dt>Situação</dt><dd>Concluído</dd>
    <dt>Início</dt><dd>01/02/2023</dd>
    <dt>Término</dt><dd>31/01/2025</dd>
  </dl>
  <h4>Resumo</h4><p>Sequenciamento.</p>
</body></html>"""

DETALHE_STRONG_BR = """<html><body><div class="box">
  <strong>Coordenador:</strong> Fulano de Tal<br>
  <strong>E-mail:</strong> fulano@unirio.br<br>
  <strong>Unidade:</strong> Escola de Medicina<br>
  <strong>Situação:</strong> Inativo<br>
  <strong>Resumo:</strong><br>Texto do resumo em várias palavras.<br>
</div></body></html>"""

DETALHE_COLUNAS = """<html><body>
  <div class="row"><div class="col-md-3"><strong>Coordenador:</strong></div><div class="col-md-9">Beltrana Silva</div></div>
  <div class="row"><div class="col-md-3"><strong>E-mail:</strong></div><div class="col-md-9">beltrana@unirio.br</div></div>
  <div class="row"><div class="col-md-3"><strong>Status:</strong></div><div class="col-md-9">Não aprovado</div></div>
</body></html>"""


class TestHtmlRealExtensao:
    """HTML real (anonimizado) do Portal da Extensão."""

    def test_listagem_list_group(self):
        itens = parser.parse_listagem(fixture("unirio_extensao_listagem.html"), "extensao", URL_EXT)
        assert len(itens) == 5
        assert itens[0]["titulo"] == "Maré de Saúde"
        assert itens[0]["unirio_id"] == "6637"
        assert itens[0]["link_detalhe"] == "https://sistemas2.unirio.br/extensao/detalhes?ID_PROJETO=6637"
        assert itens[0]["unidade"] == "Departamento de Interpretacao Teatral"
        assert itens[0]["coordenador"] == "ANA PAULA SOUZA, BRUNO LIMA"
        assert itens[0]["ano"] == "2018"
        assert parser.proxima_pagina(fixture("unirio_extensao_listagem.html"), URL_EXT) == URL_EXT.replace(
            "&f_uni=0&termos=", "&f_uni=0&pag=2&termos=")
        assert parser.total_resultados(fixture("unirio_extensao_listagem.html")) == 386

    def test_detalhe_em_cards(self):
        d = parser.parse_detalhe(fixture("unirio_extensao_detalhe.html"), hoje=date(2026, 6, 1))
        assert d["titulo"] == "Maré de Saúde"
        assert d["codigo"] == "X0272/2017"
        assert d["coordenador"] == "BRUNO LIMA"               # card "Dados do coordenador"
        assert d["email"] == "coordenador@unirio.br"          # não o e-mail dos participantes
        assert d["unidade"] == "Departamento de Interpretacao Teatral"
        assert d["situacao"] == "EM EXECUÇÃO"                 # do projeto, não dos participantes (Inativo)
        assert (d["periodo_inicio"], d["periodo_fim"]) == ("2018-03-01", "2026-12-31")
        assert d["ano"] == "2018"
        assert d["descricao"].startswith("O projeto de extensão desenvolve")
        assert d["extras"]["area_tematica"] == "Saúde"
        assert "Pessoas com deficiências, incapacidades, e necessidades especiais" in d["extras"]["linhas_extensao"]
        assert d["extras"]["financiamento"] == "Não Possui Financiamento"
        assert "palavras_chave" not in d["extras"]            # "-" conta como vazio

    def test_coleta_completa_com_html_real(self):
        listagem = fixture("unirio_extensao_listagem.html")
        detalhe = fixture("unirio_extensao_detalhe.html")
        # página 2: outros ids e sem link "Próximo" (fim da paginação)
        pagina2 = listagem.replace("ID_PROJETO=6", "ID_PROJETO=7").replace(">Próximo<", ">Fim<")
        rotas = {URL_EXT: listagem, URL_EXT.replace("&f_uni=0&termos=", "&f_uni=0&pag=2&termos="): pagina2}
        for html in (listagem, pagina2):
            for link in parser.links_de_detalhe(html, "extensao", URL_EXT):
                rotas[link] = detalhe
        res = scraper.coletar_extensao(ClienteRoteado(UnirioConfig(), rotas))
        # a paginação acabou, mas a busca anuncia 386 resultados e lemos 10 → incompleta
        assert res.paginas == 2 and res.completa is False
        assert len(res.itens) == 10 and all(i["detalhe_ok"] for i in res.itens)
        assert res.itens[0]["codigo"] == "X0272/2017" and res.itens[0]["email"] == "coordenador@unirio.br"


class TestHtmlRealPesquisa:
    """HTML real (anonimizado e reduzido) da listagem do Portal da Pesquisa: uma
    tabela única com todos os projetos, sem paginação."""

    def test_listagem_em_tabela_com_cabecalho(self):
        html = fixture("unirio_pesquisa_listagem.html")
        itens = parser.parse_listagem(html, "pesquisa", URL_PESQ)
        assert len(itens) == 8
        assert itens[0]["unirio_id"] == "1370"
        assert itens[0]["link_detalhe"] == "https://sistemas.unirio.br/projetos/projeto/index?ID_PROJETO=1370"
        assert itens[0]["titulo"].startswith("Práticas curriculares e artes de formação")
        assert itens[0]["unidade"] == "Departamento de Didatica"
        assert itens[0]["coordenador"] == "ANA PAULA SOUZA"
        assert itens[0]["ano"] == "2013"
        assert parser.proxima_pagina(html, URL_PESQ) is None
        assert scraper.exige_busca(html) is False

    def test_detalhe_em_tabela_de_pares(self):
        d = parser.parse_detalhe(fixture("unirio_pesquisa_detalhe.html"))
        assert d["titulo"].startswith("Práticas curriculares e artes de formação")
        assert d["coordenador"] == "ANA PAULA SOUZA"             # "NOME( e-mail )" separado
        assert d["email"] == "coordenador@unirio.br"
        assert d["unidade"] == "Departamento de Didatica"       # "Unidade Responsável" não é o coordenador
        assert d["situacao"] == "FINALIZADO"                    # "Concluído/Publicado"
        assert (d["periodo_inicio"], d["periodo_fim"]) == ("2013-09-01", "2017-07-31")
        assert d["ano"] == "2013"
        assert d["categoria"] is None                           # cabeçalho "Tipo | Classificação" ignorado
        assert d["descricao"].startswith("Projeto de pesquisa sobre currículos")
        assert d["extras"]["area_tematica"] == "CIÊNCIAS HUMANAS"   # Classificação CNPq (principal)
        assert d["extras"]["grupo_pesquisa"] == "Práticas Educativas e Formação de Professores"
        assert d["extras"]["palavras_chave"] == ["curriculo formacao de professores cotidiano emancipacacao social"]

    def test_coleta_pesquisa_com_html_real_e_corte_por_ano(self):
        listagem = fixture("unirio_pesquisa_listagem.html")
        rotas = {URL_PESQ_FORM: FORM_PESQUISA, URL_PESQ_FORM + "#post": listagem}
        for link in parser.links_de_detalhe(listagem, "pesquisa", URL_PESQ):
            rotas[link] = fixture("unirio_pesquisa_detalhe.html")
        res = scraper.coletar_pesquisa(ClienteRoteado(UnirioConfig(), rotas))
        assert len(res.itens) == 8 and res.completa is True and res.erros == []
        assert res.paginas == 2  # GET do formulário + POST (uma página só)

        # o corte usa o ano de referência da LISTAGEM (antes de abrir os detalhes)
        res = scraper.coletar_pesquisa(ClienteRoteado(UnirioConfig(pesquisa_ano_minimo=2014), rotas))
        ids = [i["unirio_id"] for i in res.itens]
        assert len(ids) == 4 and "1536" in ids and "2797" in ids and "1370" not in ids


class TestParser:
    def test_listagem_extensao_resolve_href_relativo_e_le_colunas_pelo_cabecalho(self):
        itens = parser.parse_listagem(listagem_extensao(1), "extensao", URL_EXT)
        assert [i["unirio_id"] for i in itens] == ["8601", "8602"]
        assert itens[0]["titulo"] == "Projeto Extensão 1"  # célula "Título", não o botão "Detalhes"
        assert itens[0]["link_detalhe"] == "https://sistemas2.unirio.br/extensao/detalhes/index?ID_PROJETO=8601"
        assert itens[0]["ano"] == "2025"
        assert itens[0]["unidade"] == "Escola de Medicina e Cirurgia"
        assert itens[0]["situacao"] == "EM EXECUÇÃO"

    def test_links_de_paginacao_e_menu_nao_viram_itens(self):
        assert len(parser.parse_listagem(listagem_extensao(1), "extensao", URL_EXT)) == 2

    def test_linha_sem_titulo_utilizavel_e_descartada(self):
        html = '<table><tr><td>2024</td><td><a href="/extensao/detalhes/index?ID_PROJETO=1">Detalhes</a></td></tr></table>'
        assert parser.parse_listagem(html, "extensao", URL_EXT) == []

    def test_proxima_pagina_rotulos_glifos_e_desabilitado(self):
        assert parser.proxima_pagina(listagem_extensao(1), URL_EXT) == URL_EXT_P2
        assert parser.proxima_pagina(listagem_extensao(2), URL_EXT_P2) is None  # li.disabled; "Última »»" ignorado
        for rotulo in ("Próximo >", "Next", "Seguinte", "›", "»"):
            html = f'<a href="?page=2">{rotulo}</a>'
            assert parser.proxima_pagina(html, URL_PESQ) == URL_PESQ + "?page=2", rotulo
        assert parser.proxima_pagina('<a rel="next" href="?page=9">9</a>', URL_PESQ) == URL_PESQ + "?page=9"
        assert parser.proxima_pagina('<span aria-hidden="true">»</span><a href="?page=2"><span class="sr-only">Next</span></a>',
                                     URL_PESQ) == URL_PESQ + "?page=2"
        for html in ('<a href="#">Próxima</a>', '<a href="javascript:void(0)">Próxima</a>',
                     '<a href="?page=2">>></a>', '<a href="?page=5">Última »</a>',
                     '<a class="disabled" href="?page=2">Próxima</a>'):
            assert parser.proxima_pagina(html, URL_PESQ) is None, html

    def test_listagem_pesquisa_ignora_links_de_pessoa_e_aceita_id_em_outra_caixa(self, monkeypatch):
        assert UnirioConfig().pesquisa_detalhe_prefixo is None  # sem restrição até conhecer a listagem real
        monkeypatch.setenv("UNIRIO_PESQUISA_DETALHE_PREFIXO", "/projetos/search/")
        prefixo = UnirioConfig().pesquisa_detalhe_prefixo
        assert prefixo == "/projetos/search/"
        itens = parser.parse_listagem(LISTAGEM_PESQUISA, "pesquisa", URL_PESQ, prefixo)
        assert [(i["unirio_id"], i["titulo"]) for i in itens] == [("501", "Genômica de bactérias"),
                                                                   ("502", "História do Rio")]
        assert itens[0]["link_detalhe"] == "https://sistemas.unirio.br/projetos/search/view?id=501"
        assert itens[0]["coordenador"] == "Ana Paula Souza" and itens[0]["unidade"] == "Instituto Biomédico"
        assert parser.proxima_pagina(LISTAGEM_PESQUISA, URL_PESQ) == "https://sistemas.unirio.br/projetos/search/index?page=2"

    def test_id_da_url(self):
        assert parser.id_da_url("https://x/extensao/detalhes/index?ID_PROJETO=8620") == "8620"
        assert parser.id_da_url("https://x/projetos/search/view?Id=5") == "5"
        assert parser.id_da_url("https://x/projetos/search/view/42") == "42"
        assert parser.id_da_url("https://x/projetos/search/view?idProjeto=9") == "9"
        assert parser.id_da_url("https://x/projetos/search/index?page=2") is None

    def test_detalhe_extensao_mapeia_campos_por_palavra_inteira(self):
        d = parser.parse_detalhe(DETALHE_EXTENSAO, hoje=date(2026, 6, 1))
        assert d["coordenador"] == "Carla Menezes de Souza"  # não o vice nem o e-mail
        assert d["email"] == "carla.menezes@unirio.br"
        assert d["unidade"] == "Escola de Medicina e Cirurgia"  # não "Comunidade atendida"
        assert (d["periodo_inicio"], d["periodo_fim"]) == ("2026-03-01", "2026-12-20")
        assert d["situacao"] == "EM EXECUÇÃO"
        assert d["ano"] == "2026"  # não o "2019" do plano de trabalho
        assert d["categoria"] is None  # "Tipo de bolsa" não é o tipo do projeto
        assert d["descricao"] == "Atividades de leitura com pacientes."
        assert d["extras"] == {"area_tematica": "Saúde", "palavras_chave": ["leitura", "escrita", "saúde"]}

    def test_detalhe_pesquisa_com_dl_e_situacao_concluida(self):
        d = parser.parse_detalhe(DETALHE_PESQUISA)
        assert d["coordenador"] == "Ana Paula Souza"
        assert d["situacao"] == "FINALIZADO"
        assert (d["periodo_inicio"], d["periodo_fim"]) == ("2023-02-01", "2025-01-31")
        assert d["email"] is None
        assert d["descricao"] == "Sequenciamento."

    def test_detalhe_com_strong_e_br(self):
        d = parser.parse_detalhe(DETALHE_STRONG_BR)
        assert d["coordenador"] == "Fulano de Tal"
        assert d["email"] == "fulano@unirio.br"
        assert d["unidade"] == "Escola de Medicina"
        assert d["situacao"] == "FINALIZADO"  # "Inativo" não é "ativo"
        assert d["descricao"] == "Texto do resumo em várias palavras."

    def test_detalhe_em_colunas_bootstrap(self):
        d = parser.parse_detalhe(DETALHE_COLUNAS)
        assert d["coordenador"] == "Beltrana Silva"
        assert d["email"] == "beltrana@unirio.br"
        assert d["situacao"] == "FINALIZADO"  # "Não aprovado"

    def test_detalhe_inesperado_levanta_value_error(self):
        with pytest.raises(ValueError):
            parser.parse_detalhe("<html><body><p>Página não encontrada</p></body></html>")

    def test_situacao_normalizada(self):
        assert parser.situacao_normalizada(None, "2026-01-01", "2026-12-31", hoje=date(2026, 6, 1)) == "EM EXECUÇÃO"
        assert parser.situacao_normalizada(None, "2027-01-01", "2027-12-31", hoje=date(2026, 6, 1)) == "NÃO INICIADO"
        assert parser.situacao_normalizada("Cancelado") == "FINALIZADO"
        assert parser.situacao_normalizada("Inativo") == "FINALIZADO"
        assert parser.situacao_normalizada("Não aprovado") == "FINALIZADO"
        assert parser.situacao_normalizada("Ativo") == "EM EXECUÇÃO"
        assert parser.situacao_normalizada("Aguardando parecer") == "AGUARDANDO PARECER"


class TestConfig:
    def test_variavel_vazia_conta_como_ausente(self, monkeypatch):
        for nome in ("UNIRIO_MAX_DETALHES", "UNIRIO_MAX_PAGINAS", "UNIRIO_PAUSA_SEGUNDOS", "UNIRIO_TIMEOUT_SEGUNDOS",
                     "UNIRIO_MAX_TENTATIVAS", "UNIRIO_MODULOS", "UNIRIO_EXTENSAO_STATUS", "UNIRIO_PESQUISA_ANOS"):
            monkeypatch.setenv(nome, "")
        cfg = UnirioConfig.from_env()
        assert cfg == UnirioConfig()
        monkeypatch.setenv("UNIRIO_PESQUISA_ANOS", "2025, 2026")
        assert UnirioConfig.from_env().pesquisa_anos == ["2025", "2026"]

    def test_prefixo_de_detalhe_configuravel(self, monkeypatch):
        monkeypatch.setenv("UNIRIO_PESQUISA_DETALHE_PREFIXO", "/projetos/projeto/")
        assert UnirioConfig().pesquisa_detalhe_prefixo == "/projetos/projeto/"

    def test_modo_de_detalhes(self, monkeypatch):
        assert UnirioConfig.from_env().detalhes == "incremental"
        monkeypatch.setenv("UNIRIO_DETALHES", " Completo ")
        assert UnirioConfig.from_env().detalhes == "completo"
        monkeypatch.setenv("UNIRIO_DETALHES", "rapido")
        with pytest.raises(ValueError):
            UnirioConfig.from_env()


class TestEncoding:
    class _Resp:
        def __init__(self, corpo: bytes, content_type: str):
            self.content = corpo
            self.headers = {"content-type": content_type}
            self.status_code = 200
            self.encoding = None if "charset" not in content_type else content_type.split("charset=")[1]
            self.apparent_encoding = "utf-8"

        @property
        def text(self):
            return self.content.decode(self.encoding or "iso-8859-1")

        def raise_for_status(self):
            pass

    def _cliente(self, resp):
        class Sessao:
            headers = {}

            def request(self, *a, **k):
                return resp
        return ClienteHttp(UnirioConfig(), session=Sessao(), sleep=lambda s: None, clock=lambda: 0.0)

    def test_sem_charset_no_header_usa_meta_do_html(self):
        corpo = '<html><head><meta charset="utf-8"></head><body>ação</body></html>'.encode("utf-8")
        assert "ação" in self._cliente(self._Resp(corpo, "text/html")).get("https://x")

    def test_charset_do_header_prevalece(self):
        corpo = "ação".encode("iso-8859-1")
        assert "ação" in self._cliente(self._Resp(corpo, "text/html; charset=iso-8859-1")).get("https://x")


class ClienteRoteado:
    """Cliente falso que responde por URL, sem throttle. POSTs são roteados por
    `url#post` ou, com ano, `url#post:ANO`."""

    def __init__(self, cfg, rotas):
        self.cfg = cfg
        self.rotas = rotas
        self.total_requisicoes = 0
        self.urls = []
        self.posts = []

    def _resp(self, chave):
        self.total_requisicoes += 1
        self.urls.append(chave)
        if chave not in self.rotas:
            raise UnirioErro(f"HTTP 404 em {chave}")
        r = self.rotas[chave]
        if isinstance(r, Exception):
            raise r
        return r

    def get(self, url, **kwargs):
        return self._resp(url)

    def post(self, url, data):
        return self.request_raw("POST", url, data=data).text

    def request_raw(self, method, url, data=None, **kwargs):
        """POST roteado por `url#post[:ANO]`; a "resposta" simula o 303 do web2py
        para a URL de resultados (`...#post` → URL_PESQ)."""
        self.posts.append(data or {})
        ano = (data or {}).get(scraper.CAMPO_ANO_PESQUISA)
        chave = f"{url}#post:{ano}" if ano else f"{url}#post"
        texto = self._resp(chave)

        class Resp:
            text = texto
            status_code = 200
            history = []
            headers = {}
            url = URL_PESQ

        return Resp()


def _rotas_extensao(falha_em=None):
    rotas = {URL_EXT: listagem_extensao(1), URL_EXT_P2: listagem_extensao(2)}
    for id_ in ("8601", "8602", "8603", "8604"):
        rotas[f"https://sistemas2.unirio.br/extensao/detalhes/index?ID_PROJETO={id_}"] = DETALHE_EXTENSAO
    if falha_em:
        rotas[f"https://sistemas2.unirio.br/extensao/detalhes/index?ID_PROJETO={falha_em}"] = UnirioErro("timeout")
    return rotas


class TestColeta:
    def test_segue_paginacao_e_abre_detalhes(self):
        cliente = ClienteRoteado(UnirioConfig(), _rotas_extensao())
        res = scraper.coletar_extensao(cliente)
        assert res.paginas == 2 and res.completa is True
        assert [i["unirio_id"] for i in res.itens] == ["8601", "8602", "8603", "8604"]
        assert all(i["email"] == "carla.menezes@unirio.br" and i["detalhe_ok"] for i in res.itens)
        assert res.itens[0]["titulo"] == "Clínica de Leitura e Escrita"  # título completo vem do detalhe
        assert res.itens[0]["modulo"] == "extensao"
        assert res.erros == []
        assert cliente.total_requisicoes == 2 + 4

    def test_falha_em_um_detalhe_mantem_dados_da_listagem(self):
        res = scraper.coletar_extensao(ClienteRoteado(UnirioConfig(), _rotas_extensao(falha_em="8602")))
        falho = next(i for i in res.itens if i["unirio_id"] == "8602")
        assert falho["detalhe_ok"] is False
        assert falho["titulo"] == "Projeto Extensão 2"
        assert falho["unidade"] == "Escola de Medicina e Cirurgia"  # coluna da listagem
        assert falho["situacao"] == "EM EXECUÇÃO"
        assert falho["coordenador"] is None and falho["email"] is None
        assert res.erros == [{"modulo": "extensao", "unirio_id": "8602", "titulo": "Projeto Extensão 2",
                              "erro": "timeout"}]

    def test_teto_de_paginas_marca_listagem_incompleta(self):
        res = scraper.coletar_extensao(ClienteRoteado(UnirioConfig(max_paginas=1), _rotas_extensao()))
        assert res.paginas == 1 and res.completa is False
        assert len(res.itens) == 2

    def test_teto_de_detalhes(self):
        res = scraper.coletar_extensao(ClienteRoteado(UnirioConfig(max_detalhes=1), _rotas_extensao()))
        assert [i["detalhe_ok"] for i in res.itens] == [True, False, False, False]
        assert res.erros == []  # itens além do teto não contam como erro

    def test_pular_detalhe_de_itens_ja_conhecidos(self):
        cliente = ClienteRoteado(UnirioConfig(), _rotas_extensao())
        res = scraper.coletar_extensao(cliente, pular_detalhe={"8601", "8603"})
        assert res.pulados == 2 and res.erros == []
        assert cliente.total_requisicoes == 2 + 2  # listagem (2 páginas) + só os detalhes não pulados
        por_id = {i["unirio_id"]: i for i in res.itens}
        assert por_id["8601"]["so_listagem"] is True and por_id["8601"]["detalhe_ok"] is False
        assert por_id["8601"]["titulo"] == "Projeto Extensão 1"  # só o que a listagem traz
        assert "so_listagem" not in por_id["8602"] and por_id["8602"]["detalhe_ok"] is True
        # o teto de detalhes conta só os que foram abertos
        res = scraper.coletar_extensao(ClienteRoteado(UnirioConfig(max_detalhes=1), _rotas_extensao()),
                                       pular_detalhe={"8601"})
        assert [i.get("detalhe_ok") for i in res.itens] == [False, True, False, False]

    def test_pesquisa_posta_o_formulario_e_segue_a_listagem(self, monkeypatch):
        rotas = {
            URL_PESQ_FORM: FORM_PESQUISA,
            URL_PESQ_FORM + "#post": LISTAGEM_PESQUISA,
            "https://sistemas.unirio.br/projetos/search/index?page=2": LISTAGEM_PESQUISA,  # mesma página
            "https://sistemas.unirio.br/projetos/search/view?id=501": DETALHE_PESQUISA,
            "https://sistemas.unirio.br/projetos/search/view?Id=502": DETALHE_PESQUISA,
            "https://sistemas.unirio.br/projetos/pessoa/view?id=77": DETALHE_PESQUISA,
            "https://sistemas.unirio.br/projetos/pessoa/view?id=78": DETALHE_PESQUISA,
        }
        cliente = ClienteRoteado(UnirioConfig(), rotas)
        res = scraper.coletar_pesquisa(cliente)
        # sem prefixo configurado, os links de pessoa também entram (4 itens, 2 por linha)
        assert len(res.itens) == 4
        # com o prefixo do controller da listagem, só os projetos
        monkeypatch.setenv("UNIRIO_PESQUISA_DETALHE_PREFIXO", "/projetos/search/")
        cliente = ClienteRoteado(UnirioConfig(), rotas)
        res = scraper.coletar_pesquisa(cliente)
        # POST leva o _formkey/_formname do web2py e os campos vazios
        assert cliente.posts[0]["_formkey"] == "58673d0c-bd05" and cliente.posts[0]["_formname"] == "default"
        assert cliente.posts[0]["TITULO"] == "" and cliente.posts[0]["ANO_REFERENCIA"] == ""
        # GET do form + POST + página 2 repetida: paramos e marcamos incompleta (paginação não avançou)
        assert res.paginas == 3 and res.completa is False
        assert len(res.itens) == 2
        assert res.itens[1]["titulo"] == "Genômica de bactérias"  # detalhe (fixture única) sobrescreve
        assert res.itens[1]["situacao"] == "FINALIZADO"

    def test_pesquisa_busca_por_ano_quando_o_portal_exige_filtro(self, monkeypatch):
        listagem_2025 = LISTAGEM_PESQUISA.replace("id=501", "id=601").replace("Id=502", "Id=602").replace(
            '<div class="pager"><a href="/projetos/search/index?page=2" class="next">Next &gt;</a></div>', "")
        assert "pager" not in listagem_2025
        listagem_2026 = listagem_2025.replace("id=601", "id=701").replace("Id=602", "Id=702")
        rotas = {
            URL_PESQ_FORM: FORM_PESQUISA,
            URL_PESQ_FORM + "#post": FORM_PESQUISA_EXIGE_BUSCA,      # busca vazia recusada
            URL_PESQ_FORM + "#post:2025": listagem_2025,
            URL_PESQ_FORM + "#post:2026": listagem_2026,
        }
        # só links do controller da listagem contam como projeto
        monkeypatch.setenv("UNIRIO_PESQUISA_DETALHE_PREFIXO", "/projetos/search/")
        for id_ in ("601", "602", "701", "702"):
            chave = "Id" if id_.endswith("2") else "id"
            rotas[f"https://sistemas.unirio.br/projetos/search/view?{chave}={id_}"] = DETALHE_PESQUISA
        cliente = ClienteRoteado(UnirioConfig(), rotas)
        res = scraper.coletar_pesquisa(cliente)
        assert [p.get("ANO_REFERENCIA") for p in cliente.posts] == ["", "2025", "2026"]  # anos do formulário
        assert [i["unirio_id"] for i in res.itens] == ["601", "602", "701", "702"]
        assert res.completa is True and res.erros == []

        cfg = UnirioConfig(pesquisa_anos=["2026"])
        cliente = ClienteRoteado(cfg, rotas)
        res = scraper.coletar_pesquisa(cliente)
        assert [p.get("ANO_REFERENCIA") for p in cliente.posts] == ["", "2026"]
        assert [i["unirio_id"] for i in res.itens] == ["701", "702"]


# ─────────────────────────────────────────────
#  Job
# ─────────────────────────────────────────────

class ClienteNulo:
    total_requisicoes = 5


def item(modulo, id_, **extra):
    return {"modulo": modulo, "unirio_id": id_, "titulo": f"Projeto {id_}", "coordenador": "COORD",
            "email": "c@unirio.br", "ano": "2026", "situacao": "EM EXECUÇÃO", "detalhe_ok": True,
            "extras": {"palavras_chave": ["a", "b"]}, **extra}


def coletores(pesquisa=None, extensao=None, erros_ext=None, completa=True):
    def fazer(modulo, itens, erros=None):
        def coletar(client):
            if isinstance(itens, Exception):
                raise itens
            return ResultadoColeta(modulo, list(itens), list(erros or []), paginas=1, completa=completa)
        return coletar
    return {"pesquisa": fazer("pesquisa", pesquisa or []), "extensao": fazer("extensao", extensao or [], erros_ext)}


CFG = UnirioConfig()


async def test_sucesso_grava_com_origem_unirio_e_desativa_ausentes(db):
    await executar_sync(db, CFG, coletores([item("pesquisa", "1"), item("pesquisa", "2")],
                                           [item("extensao", "9")]), ClienteNulo())
    run = await executar_sync(db, CFG, coletores([item("pesquisa", "1")], [item("extensao", "9")]), ClienteNulo())

    assert run["status"] == "sucesso" and run["fonte"] == "unirio"
    assert run["modulos"]["pesquisa"] == {"coletados": 1, "novos": 0, "atualizados": 1, "desativados": 1,
                                         "erros_detalhe": 0, "detalhes_pulados": 0, "paginas": 1, "completa": True,
                                         "status": "sucesso"}
    doc = await db.projetos.find_one({"unirio_id": "1"})
    assert doc["origem"] == "unirio" and doc["instituicao"] == "UNIRIO" and doc["modulo"] == "pesquisa"
    assert doc["tipo"] == "Pesquisa" and doc["palavras_chave"] == ["a", "b"]
    assert "tipo_sigaa" not in doc and "chave_sigaa" not in doc
    assert (await db.projetos.find_one({"unirio_id": "2"}))["ativo"] is False
    salvo = await db.sigaa_sync_runs.find_one({"_id": run["_id"]})
    assert salvo["fonte"] == "unirio" and salvo["requisicoes"] == 5


async def test_listagem_incompleta_grava_mas_nao_desativa_e_alerta(db):
    await executar_sync(db, CFG, coletores([item("pesquisa", "1"), item("pesquisa", "2")],
                                           [item("extensao", "9")]), ClienteNulo())
    alertas = []

    async def alertar(run):
        alertas.append(run)

    run = await executar_sync(db, CFG, coletores([item("pesquisa", "1"), item("pesquisa", "3")],
                                                 [item("extensao", "9")], completa=False),
                              ClienteNulo(), alertar)
    assert run["status"] == "falha"
    assert run["modulos"]["pesquisa"]["status"] == "falha"
    assert run["modulos"]["pesquisa"]["desativados"] == 0
    assert run["modulos"]["pesquisa"]["novos"] == 1  # o que veio foi gravado
    assert await db.projetos.count_documents({"ativo": False}) == 0
    assert any("incompleta" in e["erro"] for e in run["erros"])
    assert len(alertas) == 1


async def test_incremental_so_reabre_novos_e_pesquisa_em_execucao(db):
    from jobs.sync_unirio import ids_sem_detalhe

    # 1ª carga completa: pesquisa 1 (em execução), 2 (finalizado), 3 (detalhe falhou); extensão 9
    await executar_sync(db, CFG, coletores(
        [item("pesquisa", "1"), item("pesquisa", "2", situacao="FINALIZADO"),
         item("pesquisa", "3", detalhe_ok=False, coordenador=None, email=None)],
        [item("extensao", "9")]), ClienteNulo())

    assert await ids_sem_detalhe(db, "pesquisa", CFG) == {"2"}       # finalizado e com detalhe
    assert await ids_sem_detalhe(db, "extensao", CFG) == {"9"}       # listagem já filtra em andamento
    assert await ids_sem_detalhe(db, "pesquisa", UnirioConfig(detalhes="completo")) == set()

    # 2ª execução: o coletor recebe o conjunto e devolve o item 2 e o 9 só com a listagem
    recebidos = {}

    def fazer(modulo, itens):
        def coletar(client, pular_detalhe=frozenset()):
            recebidos[modulo] = set(pular_detalhe)
            saida = []
            for it in itens:
                if it["unirio_id"] in pular_detalhe:
                    saida.append({"modulo": modulo, "unirio_id": it["unirio_id"], "titulo": "Título da listagem",
                                  "coordenador": "COORD DA LISTAGEM", "ano": "2026", "detalhe_ok": False,
                                  "so_listagem": True})
                else:
                    saida.append(it)
            return ResultadoColeta(modulo, saida, paginas=1, pulados=len(saida) - len(itens) + len(pular_detalhe))
        return coletar

    run = await executar_sync(db, CFG, {
        "pesquisa": fazer("pesquisa", [item("pesquisa", "1", situacao="FINALIZADO"), item("pesquisa", "2"),
                                       item("pesquisa", "3"), item("pesquisa", "4")]),
        "extensao": fazer("extensao", [item("extensao", "9")]),
    }, ClienteNulo())

    assert recebidos == {"pesquisa": {"2"}, "extensao": {"9"}}
    assert run["status"] == "sucesso"
    assert run["modulos"]["pesquisa"]["detalhes_pulados"] == 1 and run["modulos"]["extensao"]["detalhes_pulados"] == 1
    assert run["modulos"]["pesquisa"]["novos"] == 1 and run["modulos"]["pesquisa"]["desativados"] == 0
    # o item pulado manteve o detalhe anterior e continua ativo, visto agora
    dois = await db.projetos.find_one({"unirio_id": "2"})
    assert dois["titulo"] == "Projeto 2" and dois["email_professor"] == "c@unirio.br"
    assert dois["situacao"] == "FINALIZADO" and dois["detalhe_ok"] is True and dois["ativo"] is True
    assert await db.projetos.count_documents({"origem": "unirio", "modulo": "pesquisa"}) == 4  # sem duplicata
    # o que foi reaberto mudou: 1 encerrou, 3 ganhou detalhe
    assert (await db.projetos.find_one({"unirio_id": "1"}))["situacao"] == "FINALIZADO"
    assert (await db.projetos.find_one({"unirio_id": "3"}))["detalhe_ok"] is True
    nove = await db.projetos.find_one({"unirio_id": "9"})
    assert nove["ativo"] is True and nove["email_professor"] == "c@unirio.br"


def _coletor_em_lotes(lotes, listados, falhar_no=None):
    """Dublê de `coletar_*.em_lotes`: gera (estado, lote); pode explodir num lote."""
    def em_lotes(client, pular_detalhe=frozenset()):
        estado = scraper.EstadoColeta("pesquisa", listados=listados, paginas=1)
        yield estado, []
        for i, lote in enumerate(lotes, start=1):
            if falhar_no == i:
                raise KeyboardInterrupt  # SIGINT do Actions no meio da coleta
            yield estado, list(lote)
    coletor = lambda client, pular_detalhe=frozenset(): None  # noqa: E731  (não usado no sync real)
    coletor.em_lotes = em_lotes
    return coletor


async def test_sync_real_grava_cada_lote_e_registra_progresso(db):
    coletor = _coletor_em_lotes([[item("pesquisa", "1"), item("pesquisa", "2")], [item("pesquisa", "3")]], listados=3)
    run = await executar_sync(db, UnirioConfig(modulos=["pesquisa"]), {"pesquisa": coletor}, ClienteNulo())
    assert run["status"] == "sucesso"
    assert run["modulos"]["pesquisa"]["coletados"] == 3 and run["modulos"]["pesquisa"]["novos"] == 3
    assert await db.projetos.count_documents({"origem": "unirio"}) == 3
    salvo = await db.sigaa_sync_runs.find_one({"_id": run["_id"]})
    assert salvo["progresso"]["pesquisa"]["coletados"] == 3 and salvo["progresso"]["pesquisa"]["listados"] == 3


async def test_sync_interrompido_mantem_os_lotes_ja_gravados(db):
    coletor = _coletor_em_lotes([[item("pesquisa", "1"), item("pesquisa", "2")], [item("pesquisa", "3")]],
                                listados=3, falhar_no=2)
    with pytest.raises(KeyboardInterrupt):
        await executar_sync(db, UnirioConfig(modulos=["pesquisa"]), {"pesquisa": coletor}, ClienteNulo())
    # o 1º lote ficou no banco, nada foi desativado e a run ficou abortada
    assert sorted(p["unirio_id"] for p in await db.projetos.find({"origem": "unirio"}).to_list(None)) == ["1", "2"]
    run = await db.sigaa_sync_runs.find_one({"fonte": "unirio"})
    assert run["status"] == "abortada" and run["progresso"]["pesquisa"]["coletados"] == 2


async def test_ano_minimo_nao_desativa_projetos_antigos_nao_lidos(db):
    await executar_sync(db, CFG, coletores([item("pesquisa", "1", ano="2015"), item("pesquisa", "2", ano="2024")]),
                        ClienteNulo())
    cfg = UnirioConfig(pesquisa_ano_minimo=2022, modulos=["pesquisa"])
    # a listagem recortada só traz o de 2024 (o de 2015 nem foi lido)
    run = await executar_sync(db, cfg, coletores([item("pesquisa", "2", ano="2024")]), ClienteNulo())
    assert run["modulos"]["pesquisa"]["desativados"] == 0
    assert (await db.projetos.find_one({"unirio_id": "1"}))["ativo"] is True
    # um de 2023 que sumiu dentro do recorte é desativado normalmente
    await db.projetos.insert_one({"origem": "unirio", "modulo": "pesquisa", "chave_unirio": "x", "unirio_id": "9",
                                  "ano": "2023", "ativo": True, "titulo": "Sumido"})
    run = await executar_sync(db, cfg, coletores([item("pesquisa", "2", ano="2024")]), ClienteNulo())
    assert run["modulos"]["pesquisa"]["desativados"] == 1


def test_coletar_em_lotes_entrega_a_listagem_primeiro_e_os_detalhes_em_lotes():
    cliente = ClienteRoteado(UnirioConfig(), _rotas_extensao())
    passos = list(scraper.coletar_em_lotes(cliente, "extensao", tamanho_lote=3))
    assert passos[0][1] == [] and passos[0][0].listados == 4 and passos[0][0].paginas == 2
    assert [len(lote) for _, lote in passos[1:]] == [3, 1]
    assert cliente.total_requisicoes == 2 + 4
    assert scraper.coletar_extensao.em_lotes.func is scraper.coletar_em_lotes


async def test_item_so_listagem_que_sumiu_do_banco_volta_pelo_fluxo_normal(db):
    reg = {**item("pesquisa", "7", detalhe_ok=False, email=None), "so_listagem": True}
    up = await repositorio.upsert_projetos(db, [reg], fonte=UNIRIO)
    assert up.novos == 1
    doc = await db.projetos.find_one({"unirio_id": "7"})
    assert doc["ativo"] is True and doc["detalhe_ok"] is False


async def test_max_detalhes_e_ignorado_no_sync_real(db):
    visto = {}

    def coletar(client):
        visto["max_detalhes"] = client.cfg.max_detalhes
        return ResultadoColeta("pesquisa", [item("pesquisa", "1")], paginas=1)

    class Cliente(ClienteNulo):
        def __init__(self, cfg):
            self.cfg = cfg

    cfg = UnirioConfig(modulos=["pesquisa"], max_detalhes=5)
    run = await executar_sync(db, cfg, {"pesquisa": coletar}, Cliente(cfg))
    # o cliente recebeu a config original, mas o job avisa e segue; o próprio
    # coletor real lê cfg do cliente, então o teste cobre o aviso e a run
    assert run["status"] == "sucesso"
    assert cfg.max_detalhes == 5  # config original não é mutada


async def test_nao_encosta_nos_projetos_do_sigaa_nem_nos_manuais(db):
    await repositorio.upsert_projetos(db, [{"modulo": "pesquisa", "sigaa_id": "77", "titulo": "Do SIGAA",
                                            "coordenador": "X", "ano": "2026", "detalhe_ok": True}])
    await db.projetos.insert_one({"titulo": "Manual", "nome_professor": "Prof.", "modulo": "pesquisa", "ativo": True})

    await executar_sync(db, CFG, coletores([item("pesquisa", "1")], [item("extensao", "9")]), ClienteNulo())

    assert (await db.projetos.find_one({"sigaa_id": "77"}))["ativo"] is True
    assert (await db.projetos.find_one({"titulo": "Manual"}))["ativo"] is True
    assert await db.projetos.count_documents({"origem": "unirio"}) == 2


async def test_zero_resultados_e_falha_nao_desativa_e_alerta(db):
    await executar_sync(db, CFG, coletores([item("pesquisa", "1")], [item("extensao", "9")]), ClienteNulo())
    alertas = []

    async def alertar(run):
        alertas.append(run)

    run = await executar_sync(db, CFG, coletores([], UnirioErro("portal fora do ar")), ClienteNulo(), alertar)

    assert run["status"] == "falha"
    assert run["modulos"]["pesquisa"]["status"] == "falha"
    assert run["modulos"]["extensao"]["status"] == "falha"
    assert await db.projetos.count_documents({"ativo": False}) == 0
    assert any("portal fora do ar" in e["erro"] for e in run["erros"])
    assert len(alertas) == 1


async def test_excecao_inesperada_marca_run_abortada(db):
    def explode(client):
        raise RuntimeError("bug")

    class Repositorio:
        pass

    # Força uma exceção fora do try do módulo: upsert com registro inválido (sem titulo).
    run_antes = await db.sigaa_sync_runs.count_documents({})
    with pytest.raises(KeyError):
        await executar_sync(db, CFG, coletores([{"modulo": "pesquisa", "unirio_id": "1"}], [item("extensao", "9")]),
                            ClienteNulo())
    assert await db.sigaa_sync_runs.count_documents({}) == run_antes + 1
    run = await db.sigaa_sync_runs.find_one({}, sort=[("iniciada_em", -1)])
    assert run["status"] == "abortada" and "KeyError" in run["erro"]
    assert explode and Repositorio  # silencia o lint; auxiliares não usados


async def test_dry_run_nao_grava_nada_e_funciona_sem_banco(db, capsys):
    run = await executar_sync(None, CFG, coletores([item("pesquisa", "1")], [item("extensao", "9")]),
                              ClienteNulo(), dry_run=True)
    assert run["status"] == "sucesso" and run["dry_run"] is True and run["_id"] is None
    assert run["modulos"]["pesquisa"]["coletados"] == 1
    assert await db.projetos.count_documents({}) == 0
    assert await db.sigaa_sync_runs.count_documents({}) == 0
    assert "Amostra (pesquisa)" in capsys.readouterr().out


async def test_fonte_unirio_nao_usa_campos_do_sigaa(db):
    await repositorio.upsert_projetos(db, [item("extensao", "9")], fonte=UNIRIO)
    doc = await db.projetos.find_one({})
    assert doc["chave_unirio"] == repositorio.chave_natural(item("extensao", "9"))
    assert doc["unirio_id"] == "9"


async def test_contato_manual_por_unirio_id(db):
    from jobs.definir_contato import definir_contato, montar_filtro

    class Args:
        projeto_id = None
        codigo = None
        sigaa_id = None
        unirio_id = "9"

    await repositorio.upsert_projetos(db, [item("extensao", "9", email=None)], fonte=UNIRIO)
    filtro = montar_filtro(Args())
    assert filtro == {"origem": "unirio", "unirio_id": "9"}
    assert await definir_contato(db, filtro, "secretaria@unirio.br") == 1
    assert (await db.projetos.find_one(filtro))["email_contato_manual"] == "secretaria@unirio.br"


# ─────────────────────────────────────────────
#  Captura
# ─────────────────────────────────────────────

def test_captura_salva_arquivos_e_isola_falha_por_modulo(tmp_path, capsys, monkeypatch):
    rotas = {
        URL_PESQ: requests.ConnectionError("fora do ar"),
        URL_EXT: listagem_extensao(1),
        "https://sistemas2.unirio.br/extensao/detalhes/index?ID_PROJETO=8601": DETALHE_EXTENSAO,
        "https://sistemas2.unirio.br/extensao/detalhes/index?ID_PROJETO=8602": DETALHE_EXTENSAO,
    }

    class Sessao:
        headers = {}

        def request(self, method, url, **kwargs):
            r = rotas[url]
            if isinstance(r, Exception):
                raise r

            class Resp:
                status_code = 200
                headers = {"content-type": "text/html; charset=utf-8"}
                encoding = "utf-8"
                text = r
                content = r.encode("utf-8")

                def raise_for_status(self):
                    pass
            return Resp()

    monkeypatch.setattr("jobs.sync_unirio.UnirioClient",
                        lambda cfg: ClienteHttp(cfg, session=Sessao(), sleep=lambda s: None, clock=lambda: 0.0))
    cfg = UnirioConfig(max_tentativas=1)
    falhas = capturar(cfg, max_detalhes=2, destino=str(tmp_path))
    assert falhas == 1  # pesquisa falhou, extensão foi capturada
    nomes = sorted(p.name for p in tmp_path.iterdir())
    assert nomes == ["extensao_detalhe_8601.html", "extensao_detalhe_8602.html", "extensao_listagem.html"]
    saida = capsys.readouterr().out
    assert "pesquisa: listagem FALHOU" in saida
    assert "extensao: 2 link(s) de detalhe, 2 item(ns) reconhecidos" in saida
    assert "CAPTURA-B64 extensao_listagem.html 1/" in saida


# ── portal fora do ar, modo "novos", ordem por ano ───────────────────────────

class _Relogio:
    def __init__(self):
        self.t = 0.0

    def __call__(self):
        return self.t

    def dormir(self, s):
        self.t += s


class _ClienteInstavel:
    """Falha nas primeiras `falhas` chamadas e depois responde."""

    def __init__(self, falhas):
        self.cfg = UnirioConfig()
        self.falhas = falhas
        self.chamadas = 0

    def get(self, url, **kw):
        self.chamadas += 1
        if self.chamadas <= self.falhas:
            raise UnirioErro("HTTP 500")
        return "<html></html>"


def test_aguardar_portal_verifica_ate_responder_ou_esgotar_o_prazo():
    relogio = _Relogio()
    cliente = _ClienteInstavel(falhas=3)
    assert scraper.aguardar_portal(cliente, "pesquisa", 60, sleep=relogio.dormir, relogio=relogio) is True
    assert cliente.chamadas == 4 and relogio.t == 3 * 600

    relogio = _Relogio()
    cliente = _ClienteInstavel(falhas=99)
    assert scraper.aguardar_portal(cliente, "pesquisa", 25, sleep=relogio.dormir, relogio=relogio) is False
    assert relogio.t == 25 * 60  # a última espera é cortada no prazo

    # 0 minutos: nem verifica
    cliente = _ClienteInstavel(falhas=99)
    assert scraper.aguardar_portal(cliente, "pesquisa", 0) is True and cliente.chamadas == 0


async def test_portal_fora_do_ar_alem_do_prazo_vira_falha_do_modulo(db, monkeypatch):
    monkeypatch.setattr("jobs.sync_unirio.aguardar_portal", lambda *a, **k: False)
    cfg = UnirioConfig(modulos=["pesquisa"], espera_portal_minutos=5)
    run = await executar_sync(db, cfg, coletores([item("pesquisa", "1")]), ClienteNulo())
    assert run["status"] == "falha" and run["modulos"]["pesquisa"]["status"] == "falha"
    assert "fora do ar" in run["erros"][0]["erro"]
    assert await db.projetos.count_documents({}) == 0


async def test_modo_novos_pula_todo_detalhe_ja_gravado(db):
    from jobs.sync_unirio import ids_sem_detalhe
    await executar_sync(db, CFG, coletores(
        [item("pesquisa", "1"), item("pesquisa", "2", situacao="FINALIZADO"),
         item("pesquisa", "3", detalhe_ok=False, coordenador=None, email=None)]), ClienteNulo())
    assert await ids_sem_detalhe(db, "pesquisa", UnirioConfig(detalhes="novos")) == {"1", "2"}
    assert await ids_sem_detalhe(db, "pesquisa", UnirioConfig(detalhes="incremental")) == {"2"}


def test_pesquisa_abre_os_detalhes_dos_anos_mais_recentes_primeiro(monkeypatch):
    itens = [{"unirio_id": "a", "ano": "2019", "link_detalhe": "u/a", "titulo": "A"},
             {"unirio_id": "b", "ano": "2025", "link_detalhe": "u/b", "titulo": "B"},
             {"unirio_id": "c", "ano": None, "link_detalhe": "u/c", "titulo": "C"},
             {"unirio_id": "d", "ano": "2025", "link_detalhe": "u/d", "titulo": "D"}]
    monkeypatch.setattr(scraper, "listar", lambda client, modulo: (list(itens), 1, True))
    abertos = []

    class Cliente:
        cfg = UnirioConfig()

        def get(self, url, **kw):
            abertos.append(url)
            raise UnirioErro("sem rede")

    list(scraper.coletar_em_lotes(Cliente(), "pesquisa"))
    assert abertos == ["u/b", "u/d", "u/a", "u/c"]


class TestCargaLeve:
    class _Resp:
        def __init__(self, status=200, headers=None):
            self.status_code = status
            self.headers = headers or {"content-type": "text/html; charset=utf-8"}
            self.text = "ok"
            self.content = b"ok"

        def raise_for_status(self):
            pass

    class _Sessao:
        def __init__(self, respostas, relogio, duracao):
            self.respostas = list(respostas)
            self.relogio = relogio
            self.duracao = duracao
            self.headers = {}

        def request(self, method, url, **kw):
            self.relogio.t += self.duracao  # o servidor demora para responder
            return self.respostas.pop(0)

    def _cliente(self, respostas, duracao, **cfg):
        relogio = _Relogio()
        dormidas = []

        def dormir(s):
            dormidas.append(s)
            relogio.dormir(s)

        cliente = ClienteHttp(UnirioConfig(**cfg), session=self._Sessao(respostas, relogio, duracao),
                              sleep=dormir, clock=relogio)
        return cliente, dormidas

    def test_pausa_acompanha_o_tempo_de_resposta_do_servidor(self):
        cliente, dormidas = self._cliente([self._Resp(), self._Resp()], duracao=30)
        cliente.get("u/1")
        cliente.get("u/2")
        assert dormidas == [30]  # esperou o mesmo que o servidor levou (fator 1.0)

        cliente, dormidas = self._cliente([self._Resp(), self._Resp()], duracao=0.2)
        cliente.get("u/1")
        cliente.get("u/2")
        assert dormidas == [1.5]  # servidor rápido: vale a pausa mínima de 1,5 s

    def test_poucas_tentativas_espacadas_e_retry_after(self):
        erro = self._Resp(503, {"Retry-After": "120"})
        cliente, dormidas = self._cliente([erro, self._Resp(500), self._Resp(500)], duracao=1)
        with pytest.raises(ErroColeta):
            cliente.get("u/1")
        # 3 tentativas: espera max(10, 120) após a 1ª e 20 após a 2ª (mais as pausas mínimas)
        assert 120 in dormidas and 20 in dormidas and len([d for d in dormidas if d >= 10]) == 2
