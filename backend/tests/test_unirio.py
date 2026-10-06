"""Parser, coleta e job dos portais da UNIRIO — sem rede.

As fixtures abaixo reproduzem a estrutura esperada das páginas (tabela de
resultados com link de detalhe, paginação por link e detalhe em pares
rótulo/valor). Quando o HTML real for capturado (`python -m jobs.sync_unirio
--captura`), ele deve substituir estes trechos em `tests/fixtures/`.
"""

from datetime import date

from jobs.sync_unirio import executar_sync
from services.fontes import UNIRIO
from services.sigaa import repositorio
from services.unirio import parser, scraper
from services.unirio.config import UnirioConfig
from services.unirio.scraper import ResultadoColeta, UnirioErro

URL_EXT = UnirioConfig().url_extensao
URL_PESQ = UnirioConfig().url_pesquisa


def listagem_extensao(pagina: int, total_paginas: int = 2) -> str:
    base = (pagina - 1) * 2
    linhas = "".join(
        f"""<tr>
              <td>{2024 + i % 2}</td>
              <td><a href="/extensao/detalhes/index?ID_PROJETO={8600 + base + i}">Projeto Extensão {base + i}</a></td>
              <td>Escola de Medicina e Cirurgia</td>
              <td>Em andamento</td>
            </tr>"""
        for i in range(1, 3)
    )
    proxima = (
        f'<a href="/extensao/busca/projetos?f_status=1&page={pagina + 1}">Próxima</a>'
        if pagina < total_paginas
        else '<span class="disabled">Próxima</span>'
    )
    return f"""<html><head><title>Buscar projetos - Portal da Extensão</title></head><body>
      <form><select name="f_status"><option value="1" selected>Em andamento</option></select></form>
      <table class="table"><thead><tr><th>Ano</th><th>Título</th><th>Unidade</th><th>Status</th></tr></thead>
      <tbody>{linhas}</tbody></table>
      <ul class="pagination"><li><a href="/extensao/busca/projetos?f_status=1&page=1">1</a></li><li>{proxima}</li></ul>
    </body></html>"""


DETALHE_EXTENSAO = """<html><body>
  <h2>Detalhes do Projeto</h2>
  <table>
    <tr><th>Título:</th><td>Clínica de Leitura e Escrita</td></tr>
    <tr><th>Coordenador(a):</th><td>Carla Menezes de Souza</td></tr>
    <tr><th>E-mail:</th><td>Carla.Menezes@unirio.br</td></tr>
    <tr><th>Unidade:</th><td>Escola de Medicina e Cirurgia</td></tr>
    <tr><th>Área temática:</th><td>Saúde</td></tr>
    <tr><th>Período de realização:</th><td>01/03/2026 a 20/12/2026</td></tr>
    <tr><th>Status:</th><td>Em andamento</td></tr>
    <tr><th>Palavras-chave:</th><td>leitura; escrita; saúde</td></tr>
  </table>
  <h4>Resumo</h4>
  <p>Atividades   de leitura com pacientes.</p>
</body></html>"""

LISTAGEM_PESQUISA = """<html><body>
  <table class="items">
    <tr><th>Título</th><th>Coordenador</th><th>Unidade</th></tr>
    <tr><td><a href="/projetos/search/view?id=501">Genômica de bactérias</a></td>
        <td>Ana Paula Souza</td><td>Instituto Biomédico</td></tr>
    <tr><td><a href="/projetos/search/view?id=502">História do Rio</a></td>
        <td>Bruno Lima</td><td>Escola de História</td></tr>
  </table>
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


class TestParser:
    def test_listagem_extensao_le_titulo_id_link_e_ano(self):
        itens = parser.parse_listagem(listagem_extensao(1), "extensao", parser.BASE_EXTENSAO)
        assert [i["unirio_id"] for i in itens] == ["8601", "8602"]
        assert itens[0]["titulo"] == "Projeto Extensão 1"
        assert itens[0]["link_detalhe"] == "https://sistemas2.unirio.br/extensao/detalhes/index?ID_PROJETO=8601"
        assert itens[0]["ano"] == "2025"
        assert "Escola de Medicina e Cirurgia" in itens[0]["colunas"]

    def test_links_de_paginacao_nao_viram_itens(self):
        itens = parser.parse_listagem(listagem_extensao(1), "extensao", parser.BASE_EXTENSAO)
        assert len(itens) == 2

    def test_proxima_pagina_e_ultima(self):
        assert parser.proxima_pagina(listagem_extensao(1), URL_EXT) == (
            "https://sistemas2.unirio.br/extensao/busca/projetos?f_status=1&page=2"
        )
        assert parser.proxima_pagina(listagem_extensao(2), URL_EXT) is None

    def test_listagem_pesquisa(self):
        itens = parser.parse_listagem(LISTAGEM_PESQUISA, "pesquisa", parser.BASE_PESQUISA)
        assert [(i["unirio_id"], i["titulo"]) for i in itens] == [("501", "Genômica de bactérias"),
                                                                   ("502", "História do Rio")]
        assert itens[0]["link_detalhe"] == "https://sistemas.unirio.br/projetos/search/view?id=501"

    def test_detalhe_extensao_mapeia_campos(self):
        d = parser.parse_detalhe(DETALHE_EXTENSAO, hoje=date(2026, 6, 1))
        assert d["coordenador"] == "Carla Menezes de Souza"
        assert d["email"] == "carla.menezes@unirio.br"
        assert d["unidade"] == "Escola de Medicina e Cirurgia"
        assert (d["periodo_inicio"], d["periodo_fim"]) == ("2026-03-01", "2026-12-20")
        assert d["situacao"] == "EM EXECUÇÃO"
        assert d["ano"] == "2026"
        assert d["extras"] == {"area_tematica": "Saúde", "palavras_chave": ["leitura", "escrita", "saúde"]}

    def test_detalhe_pesquisa_com_dl_e_situacao_concluida(self):
        d = parser.parse_detalhe(DETALHE_PESQUISA)
        assert d["coordenador"] == "Ana Paula Souza"
        assert d["situacao"] == "FINALIZADO"
        assert (d["periodo_inicio"], d["periodo_fim"]) == ("2023-02-01", "2025-01-31")
        assert d["email"] is None

    def test_detalhe_inesperado_levanta_value_error(self):
        import pytest

        with pytest.raises(ValueError):
            parser.parse_detalhe("<html><body><p>Página não encontrada</p></body></html>")

    def test_situacao_derivada_do_periodo_quando_portal_nao_informa(self):
        assert parser.situacao_normalizada(None, "2026-01-01", "2026-12-31", hoje=date(2026, 6, 1)) == "EM EXECUÇÃO"
        assert parser.situacao_normalizada(None, "2027-01-01", "2027-12-31", hoje=date(2026, 6, 1)) == "NÃO INICIADO"
        assert parser.situacao_normalizada("Cancelado") == "FINALIZADO"
        assert parser.situacao_normalizada("Aguardando parecer") == "AGUARDANDO PARECER"


class ClienteRoteado:
    """Cliente falso que responde por URL, sem throttle."""

    def __init__(self, cfg, rotas):
        self.cfg = cfg
        self.rotas = rotas
        self.total_requisicoes = 0
        self.urls = []

    def get(self, url, **kwargs):
        self.total_requisicoes += 1
        self.urls.append(url)
        r = self.rotas[url]
        if isinstance(r, Exception):
            raise r
        return r


def _rotas_extensao(falha_em=None):
    rotas = {
        URL_EXT: listagem_extensao(1),
        "https://sistemas2.unirio.br/extensao/busca/projetos?f_status=1&page=2": listagem_extensao(2),
    }
    for id_ in ("8601", "8602", "8603", "8604"):
        rotas[f"https://sistemas2.unirio.br/extensao/detalhes/index?ID_PROJETO={id_}"] = DETALHE_EXTENSAO
    if falha_em:
        rotas[f"https://sistemas2.unirio.br/extensao/detalhes/index?ID_PROJETO={falha_em}"] = UnirioErro("timeout")
    return rotas


class TestColeta:
    def test_segue_paginacao_e_abre_detalhes(self):
        cliente = ClienteRoteado(UnirioConfig(), _rotas_extensao())
        res = scraper.coletar_extensao(cliente)
        assert res.paginas == 2
        assert [i["unirio_id"] for i in res.itens] == ["8601", "8602", "8603", "8604"]
        assert all(i["email"] == "carla.menezes@unirio.br" and i["detalhe_ok"] for i in res.itens)
        assert res.itens[0]["titulo"] == "Clínica de Leitura e Escrita"  # título completo vem do detalhe
        assert res.itens[0]["modulo"] == "extensao"
        assert res.erros == []
        assert cliente.total_requisicoes == 2 + 4

    def test_falha_em_um_detalhe_mantem_item_da_listagem(self):
        res = scraper.coletar_extensao(ClienteRoteado(UnirioConfig(), _rotas_extensao(falha_em="8602")))
        falho = next(i for i in res.itens if i["unirio_id"] == "8602")
        assert falho["detalhe_ok"] is False
        assert falho["titulo"] == "Projeto Extensão 2"
        assert falho["coordenador"] is None and falho["email"] is None
        assert res.erros == [{"modulo": "extensao", "unirio_id": "8602", "titulo": "Projeto Extensão 2",
                              "erro": "timeout"}]

    def test_teto_de_paginas_e_detalhes(self):
        cfg = UnirioConfig(max_paginas=1, max_detalhes=1)
        res = scraper.coletar_extensao(ClienteRoteado(cfg, _rotas_extensao()))
        assert res.paginas == 1
        assert len(res.itens) == 2
        assert [i["detalhe_ok"] for i in res.itens] == [True, False]
        assert res.erros == []  # itens além do teto não contam como erro

    def test_pesquisa_usa_url_e_base_proprias(self):
        rotas = {
            URL_PESQ: LISTAGEM_PESQUISA,
            "https://sistemas.unirio.br/projetos/search/view?id=501": DETALHE_PESQUISA,
            "https://sistemas.unirio.br/projetos/search/view?id=502": DETALHE_PESQUISA,
        }
        res = scraper.coletar_pesquisa(ClienteRoteado(UnirioConfig(), rotas))
        assert len(res.itens) == 2
        assert res.itens[1]["titulo"] == "Genômica de bactérias"  # detalhe (fixture única) sobrescreve
        assert res.itens[1]["situacao"] == "FINALIZADO"


# ─────────────────────────────────────────────
#  Job
# ─────────────────────────────────────────────

class ClienteNulo:
    total_requisicoes = 5


def item(modulo, id_, **extra):
    return {"modulo": modulo, "unirio_id": id_, "titulo": f"Projeto {id_}", "coordenador": "COORD",
            "email": "c@unirio.br", "ano": "2026", "situacao": "EM EXECUÇÃO", "detalhe_ok": True,
            "extras": {"palavras_chave": ["a", "b"]}, **extra}


def coletores(pesquisa=None, extensao=None, erros_ext=None):
    def fazer(modulo, itens, erros=None):
        def coletar(client):
            if isinstance(itens, Exception):
                raise itens
            return ResultadoColeta(modulo, list(itens), list(erros or []), paginas=1)
        return coletar
    return {"pesquisa": fazer("pesquisa", pesquisa or []), "extensao": fazer("extensao", extensao or [], erros_ext)}


CFG = UnirioConfig()


async def test_sucesso_grava_com_origem_unirio_e_desativa_ausentes(db):
    await executar_sync(db, CFG, coletores([item("pesquisa", "1"), item("pesquisa", "2")],
                                           [item("extensao", "9")]), ClienteNulo())
    run = await executar_sync(db, CFG, coletores([item("pesquisa", "1")], [item("extensao", "9")]), ClienteNulo())

    assert run["status"] == "sucesso" and run["fonte"] == "unirio"
    assert run["modulos"]["pesquisa"] == {"coletados": 1, "novos": 0, "atualizados": 1, "desativados": 1,
                                         "erros_detalhe": 0, "paginas": 1, "status": "sucesso"}
    doc = await db.projetos.find_one({"unirio_id": "1"})
    assert doc["origem"] == "unirio" and doc["instituicao"] == "UNIRIO" and doc["modulo"] == "pesquisa"
    assert doc["tipo"] == "Pesquisa" and doc["palavras_chave"] == ["a", "b"]
    assert "tipo_sigaa" not in doc and "chave_sigaa" not in doc
    assert (await db.projetos.find_one({"unirio_id": "2"}))["ativo"] is False
    salvo = await db.sigaa_sync_runs.find_one({"_id": run["_id"]})
    assert salvo["fonte"] == "unirio" and salvo["requisicoes"] == 5


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


async def test_dry_run_nao_grava_nada(db, capsys):
    run = await executar_sync(db, CFG, coletores([item("pesquisa", "1")], [item("extensao", "9")]),
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
