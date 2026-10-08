"""Coleta da extensão da PUC-Campinas (página pública de projetos)."""

from datetime import date

from jobs import sync_puccamp
from services.fontes import PUCCAMP
from services.puccamp.coleta import PucCampConfig, parse_extensao, registro_extensao

# Recorte fiel à estrutura da página: tabela título/docente no topo, ciclo
# vigente com blocos rotulados por PIE e, no fim, um ciclo antigo.
HTML = """
<html><head><script>var x = "DOCENTE: falso";</script></head><body>
<table>
<tr><td>Título</td><td>Docente</td></tr>
<tr><td>Cartas do Vida Nova: filmes-cartas e produção partilhada do conhecimento</td>
    <td>Caio de Salvi Lazaneo</td></tr>
<tr><td>Cidadania sem fronteiras: letramento jurídico e acolhimento de migrantes e refugiados</td>
    <td>Carolina Piccolotto Galib</td></tr>
</table>
<h2>Projetos de Atividades de Extensão Institucional</h2>
<p>Vigência de 01/08/2026 a 31/01/2029</p>
<h3>PIE 1 – Educação, Comunicação e Cultura</h3>
<p>DOCENTE: CAIO DE SALVI LAZANEO<br>ESCOLA: ELC<br>FACULDADE: Cinema e Audiovisual<br>
TÍTULO: Cartas do Vida Nova: filmes-cartas e produção partilhada do conhecimento<br>
PÚBLICO: Escola E. Profa. Maria Helena, Campinas<br>
RESUMO: estimular práticas de criação audiovisual com estudantes da educação básica.</p>
<h3>PIE 2 – Direitos humanos e Justiça</h3>
<p>DOCENTE: CAROLINA PICCOLOTTO GALIB<br>ESCOLA: HJS<br>FACULDADE: Direito<br>
TÍTULO: Cidadania sem fronteiras: letramento jurídico e
acolhimento de migrantes e refugiados<br>
PÚBLICO: migrantes e refugiados em Campinas (RMC)<br>
RESUMO: prestar assistência jurídica a migrantes.</p>
<p>DOCENTE: PEDRO DE MIRANDA COSTA<br>ESCOLA: ECON<br>FACULDADE: Ciências Econômicas<br>
TÍTULO: Coleta e divulgação dos preços da cesta básica<br>RESUMO: acompanhar preços.</p>
<h3>Ano de 2023</h3>
<p>DOCENTE: FULANO ANTIGO<br>TÍTULO: Projeto do ciclo passado<br>RESUMO: antigo.</p>
</body></html>
"""


def test_parse_le_so_o_ciclo_vigente_com_programa_e_grafia_dos_nomes():
    projetos = parse_extensao(HTML)
    assert [p["titulo"] for p in projetos] == [
        "Cartas do Vida Nova: filmes-cartas e produção partilhada do conhecimento",
        "Cidadania sem fronteiras: letramento jurídico e acolhimento de migrantes e refugiados",
        "Coleta e divulgação dos preços da cesta básica",
    ]
    primeiro, segundo, terceiro = projetos
    # Grafia da tabela do topo; sem ela, nome próprio com conectivos minúsculos.
    assert primeiro["docente"] == "Caio de Salvi Lazaneo"
    assert segundo["docente"] == "Carolina Piccolotto Galib"
    assert terceiro["docente"] == "Pedro de Miranda Costa"
    assert primeiro["programa"] == "Educação, Comunicação e Cultura"
    assert segundo["programa"] == terceiro["programa"] == "Direitos humanos e Justiça"
    assert segundo["publico"] == "migrantes e refugiados em Campinas (RMC)"
    assert terceiro["publico"] is None
    assert primeiro["inicio"] == "2026-08-01" and primeiro["fim"] == "2029-01-31"


def test_registro_situacao_pela_vigencia_e_campos():
    proj = parse_extensao(HTML)[0]
    reg = registro_extensao(proj, hoje=date(2026, 10, 8))
    assert reg["situacao"] == "EM EXECUÇÃO"
    assert reg["unidade"] == "Faculdade de Cinema e Audiovisual"
    assert reg["descricao"].startswith("Estimular práticas")
    assert reg["descricao"].endswith("Público: Escola E. Profa. Maria Helena, Campinas")
    assert reg["extras"] == {"area_tematica": "Educação, Comunicação e Cultura", "escola": "ELC"}
    assert reg["puccamp_id"] == "cartas-do-vida-nova-filmes-cartas-e-producao-partilhada-do-conhecimento"
    assert reg["email"] is None and reg["ano"] == "2026"
    assert registro_extensao(proj, hoje=date(2026, 7, 1))["situacao"] == "NÃO INICIADO"
    assert registro_extensao(proj, hoje=date(2029, 2, 1))["situacao"] == "FINALIZADO"


class _Cliente:
    total_requisicoes = 0

    def __init__(self, html):
        self.html = html
        self.cfg = PucCampConfig()

    def get(self, url, **_):
        self.total_requisicoes += 1
        return self.html


async def test_sync_grava_com_origem_propria_e_desativa_ausentes(db):
    run = await sync_puccamp.executar_sync(db, PucCampConfig(), client=_Cliente(HTML))
    assert run["status"] == "sucesso" and run["modulos"]["extensao"]["novos"] == 3
    docs = await db.projetos.find({"origem": "puccamp"}).to_list(10)
    assert {d["instituicao"] for d in docs} == {PUCCAMP.instituicao}
    assert all(d["campus"] == "Campinas" and d["chave_puccamp"] for d in docs)

    # Um projeto some da página: é desativado; os demais seguem ativos.
    menor = HTML.replace("<p>DOCENTE: PEDRO DE MIRANDA COSTA", "<p>REMOVIDO: PEDRO DE MIRANDA COSTA")
    run = await sync_puccamp.executar_sync(db, PucCampConfig(), client=_Cliente(menor))
    assert run["modulos"]["extensao"]["desativados"] == 1
    assert await db.projetos.count_documents({"origem": "puccamp", "ativo": True}) == 2

    # Página sem o ciclo: falha e nada é desativado.
    run = await sync_puccamp.executar_sync(db, PucCampConfig(), client=_Cliente("<html></html>"))
    assert run["status"] == "falha"
    assert await db.projetos.count_documents({"origem": "puccamp", "ativo": True}) == 2


async def test_busca_publica_mostra_puc_campinas_no_filtro(api, db):
    await sync_puccamp.executar_sync(db, PucCampConfig(), client=_Cliente(HTML))
    r = await api.get("/api/projetos/buscar", params={"instituicao": "PUC-Campinas"})
    assert r.status_code == 200 and len(r.json()) == 3
    assert all(p["link_detalhe"] for p in r.json())
    filtros = (await api.get("/api/projetos/filtros")).json()
    assert "PUC-Campinas" in {i["sigla"] for i in filtros["instituicoes"]}
