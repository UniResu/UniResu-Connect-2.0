"""Campus deduzido da unidade e filtros por campus e por várias unidades."""

from services.campi import extrair_campus, garantir_campus
from services.fontes import SIGAA, fonte_sigaa
from services.sigaa.repositorio import upsert_projetos


def test_campus_da_unir_pela_sigla_ou_cidade():
    assert extrair_campus({"instituicao": "UNIR", "unidade": "COORDENADORIA DO CURSO DE DIREITO - CAC"}) == "Cacoal"
    assert extrair_campus({"instituicao": "UNIR", "unidade": "COORDENADORIA DE APOIO ACADÊMICO - ARI - ARIQUEMES - 11.35.01.14"}) == "Ariquemes"
    assert extrair_campus({"instituicao": "UNIR", "unidade": "CAMPUS ARIQUEMES - ARIQUEMES - 11.35"}) == "Ariquemes"
    assert extrair_campus({"instituicao": "UNIR", "unidade": "COORDENAÇÃO DE APOIO ACADÊMICO - RM"}) == "Rolim de Moura"
    assert extrair_campus({"instituicao": "UNIR", "unidade": "DEPARTAMENTO ACADÊMICO DE MEDICINA - NUSAU"}) == "Porto Velho"
    assert extrair_campus({"instituicao": "UNIR", "unidade": None}) is None


def test_campus_de_outros_sigaas_e_institutos():
    assert extrair_campus({"instituicao": "UFRN", "unidade": "CENTRO DE CIÊNCIAS DA SAÚDE - NATAL - 15.00"}) == "Natal"
    assert extrair_campus({"instituicao": "UFRN", "unidade": "CENTRO DE ENSINO SUPERIOR DO SERIDÓ - CAICÓ - 18.00"}) == "Caicó"
    assert extrair_campus({"instituicao": "IFAL", "unidade": "C-MARAGOGI"}) == "Maragogi"
    assert extrair_campus({"instituicao": "UFPB", "unidade": "DEPARTAMENTO DE FÍSICA"}) is None


def test_campus_das_sedes():
    assert extrair_campus({"instituicao": "UNIRIO", "unidade": "Escola de Medicina e Cirurgia"}) == "Rio de Janeiro"
    assert extrair_campus({"instituicao": "UFV", "unidade": "DPS"}) == "Viçosa"
    assert extrair_campus({"instituicao": "UFV", "unidade": "CAF", "departamento_sigla": "CAF"}) == "Florestal"
    assert extrair_campus({"instituicao": "UFV", "departamento_sigla": "CRP-DEP"}) == "Rio Paranaíba"


async def test_upsert_grava_campus_e_migracao_preenche_antigos(db):
    reg = {"modulo": "pesquisa", "sigaa_id": "9", "titulo": "Água", "coordenador": "ANA", "ano": "2026",
           "unidade": "CENTRO DE TECNOLOGIA - NATAL - 14.00", "situacao": "EM EXECUÇÃO"}
    await upsert_projetos(db, [reg], fonte=fonte_sigaa("UFRN"))
    assert (await db.projetos.find_one({"instituicao": "UFRN"}))["campus"] == "Natal"

    await db.projetos.insert_many([
        {"origem": "unirio", "instituicao": "UNIRIO", "modulo": "extensao", "titulo": "X", "unidade": "CCBS"},
        {"origem": "sigaa", "instituicao": "UNIR", "modulo": "extensao", "titulo": "Y", "unidade": "CURSO DE LETRAS - VHA"},
        {"origem": "sigaa", "instituicao": "UFPB", "modulo": "extensao", "titulo": "Z", "unidade": "DEPTO"},
        {"titulo": "manual sem origem"},
    ])
    assert await garantir_campus(db) == 3
    assert (await db.projetos.find_one({"titulo": "X"}))["campus"] == "Rio de Janeiro"
    assert (await db.projetos.find_one({"titulo": "Y"}))["campus"] == "Vilhena"
    assert (await db.projetos.find_one({"titulo": "Z"}))["campus"] is None
    assert "campus" not in (await db.projetos.find_one({"titulo": "manual sem origem"}))
    assert await garantir_campus(db) == 0


async def test_filtro_por_varias_unidades_e_por_campus(db, api):
    regs = [
        {"modulo": "extensao", "sigaa_id": "1", "titulo": "A", "coordenador": "C", "ano": "2026",
         "unidade": "CURSO DE DIREITO - CAC", "situacao": "EM EXECUÇÃO", "periodo_inicio": "2026-01-01", "periodo_fim": "2027-01-01"},
        {"modulo": "extensao", "sigaa_id": "2", "titulo": "B", "coordenador": "C", "ano": "2026",
         "unidade": "CURSO DE LETRAS - VHA", "situacao": "EM EXECUÇÃO", "periodo_inicio": "2026-01-01", "periodo_fim": "2027-01-01"},
        {"modulo": "extensao", "sigaa_id": "3", "titulo": "D", "coordenador": "C", "ano": "2026",
         "unidade": "NUSAU", "situacao": "EM EXECUÇÃO", "periodo_inicio": "2026-01-01", "periodo_fim": "2027-01-01"},
    ]
    await upsert_projetos(db, regs, fonte=SIGAA)
    r = await api.get("/api/projetos/buscar", params=[("unidade", "CURSO DE DIREITO - CAC"), ("unidade", "CURSO DE LETRAS - VHA")])
    assert r.status_code == 200 and sorted(p["titulo"] for p in r.json()) == ["A", "B"]
    r = await api.get("/api/projetos/buscar", params={"campus": "Porto Velho"})
    assert [p["titulo"] for p in r.json()] == ["D"]
    r = await api.get("/api/projetos/buscar", params=[("campus", "Cacoal"), ("campus", "Vilhena")])
    assert sorted(p["titulo"] for p in r.json()) == ["A", "B"]

    r = await api.get("/api/projetos/filtros")
    unir = next(i for i in r.json()["instituicoes"] if i["sigla"] == "UNIR")
    assert [(c["nome"], c["total"]) for c in unir["campi"]] == [("Cacoal", 1), ("Porto Velho", 1), ("Vilhena", 1)]
    assert unir["campi"][0]["modulos"] == {"extensao": 1}
