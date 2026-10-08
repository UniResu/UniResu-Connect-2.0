"""Links para o SIGAA de origem: página do projeto ou consulta pública."""

from services.sigaa.links import link_consulta
from tests.test_projetos_api import sigaa


def test_link_consulta_por_instituicao_e_modulo():
    assert link_consulta({"origem": "sigaa", "instituicao": "UNIR", "modulo": "pesquisa"}) == (
        "https://sigaa.unir.br/sigaa/public/pesquisa/consulta_projetos.jsf")
    assert link_consulta({"origem": "sigaa", "instituicao": "UFRN", "modulo": "extensao"}) == (
        "https://sigaa.ufrn.br/sigaa/public/extensao/consulta_extensao.jsf")
    # Documentos antigos só com tipo_sigaa, e da UNIR sem o campo instituicao.
    assert link_consulta({"origem": "sigaa", "tipo_sigaa": "pesquisa"}).startswith("https://sigaa.unir.br/")
    assert link_consulta({"origem": "unirio", "instituicao": "UNIRIO", "modulo": "pesquisa"}) is None
    assert link_consulta({"origem": "sigaa", "instituicao": "XYZ", "modulo": "pesquisa"}) is None


async def test_busca_publica_entrega_consulta_so_sem_link_proprio(api, db):
    pesquisa = sigaa("Robótica educacional")
    extensao = {**sigaa("Horta comunitária", tipo="extensao"),
                "link_detalhe": "https://sigaa.unir.br/sigaa/link/public/extensao/visualizacaoAcaoExtensao/1"}
    await db.projetos.insert_many([pesquisa, extensao])
    por_titulo = {p["titulo"]: p for p in (await api.get("/api/projetos/buscar")).json()}

    assert por_titulo["Robótica educacional"]["link_consulta"].endswith("/sigaa/public/pesquisa/consulta_projetos.jsf")
    assert por_titulo["Robótica educacional"]["link_detalhe"] is None
    assert por_titulo["Horta comunitária"]["link_detalhe"].endswith("/visualizacaoAcaoExtensao/1")
    assert por_titulo["Horta comunitária"]["link_consulta"] is None
