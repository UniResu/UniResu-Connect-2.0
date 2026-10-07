"""Listagem/filtros da aba Projetos Acadêmicos (GET /api/projetos/*)."""

from datetime import datetime, timezone

import pytest
from bson import ObjectId


EXATAS = "Ciências Exatas e da Terra"
ENGENHARIAS = "Engenharias"
SAUDE = "Ciências da Saúde"
AGRARIAS = "Ciências Agrárias"
HUMANAS = "Ciências Humanas"


def sigaa(titulo, tipo="pesquisa", unidade="CAMPUS PORTO VELHO", situacao="EM EXECUÇÃO", ativo=True,
          coordenador="ANA PAULA SOUZA", email="ana@unir.br", area=EXATAS):
    return {"origem": "sigaa", "chave_sigaa": f"{tipo}|{titulo}", "modulo": tipo, "tipo_sigaa": tipo,
            "tipo": "Pesquisa" if tipo == "pesquisa" else "Extensão", "titulo": titulo, "instituicao": "UNIR",
            "nome_professor": coordenador, "email_professor": email, "unidade": unidade,
            "situacao": situacao, "ano": "2026", "ativo": ativo, "area_conhecimento": area}


def unirio(titulo, modulo="extensao", unidade="ESCOLA DE MEDICINA E CIRURGIA", situacao="EM EXECUÇÃO", area=SAUDE):
    return {"origem": "unirio", "chave_unirio": f"{modulo}|{titulo}", "modulo": modulo, "unirio_id": titulo,
            "tipo": "Pesquisa" if modulo == "pesquisa" else "Extensão", "titulo": titulo, "instituicao": "UNIRIO",
            "nome_professor": "CARLA MENEZES", "email_professor": "carla@unirio.br", "unidade": unidade,
            "situacao": situacao, "ano": "2026", "ativo": True, "palavras_chave": ["saúde", "extensão"],
            "area_conhecimento": area}


@pytest.fixture
async def base(db):
    await db.projetos.insert_many([
        sigaa("Robótica educacional", area=ENGENHARIAS),
        sigaa("Horta comunitária", tipo="extensao", unidade="DEPARTAMENTO DE AGRONOMIA", coordenador="BRUNO LIMA",
              area=AGRARIAS),
        sigaa("Projeto finalizado", situacao="FINALIZADO"),
        sigaa("Sumiu do SIGAA", ativo=False),
        sigaa("Sem contato", email=None),
        unirio("Clínica de leitura"),
        {"titulo": "Projeto manual do professor", "descricao": "Cadastrado na plataforma",
         "nome_professor": "Prof. Manual", "email_professor": "manual@unir.br", "tipo_projeto": "voluntario_aberto",
         "area_conhecimento": HUMANAS},
    ])
    return db


def titulos(resp):
    assert resp.status_code == 200, resp.text
    return sorted(p["titulo"] for p in resp.json())


async def test_padrao_mostra_so_ativos_em_execucao_e_manuais(api, base):
    r = await api.get("/api/projetos/buscar")
    assert titulos(r) == ["Clínica de leitura", "Horta comunitária", "Projeto manual do professor",
                          "Robótica educacional", "Sem contato"]


async def test_incluir_inativos(api, base):
    r = await api.get("/api/projetos/buscar", params={"incluir_inativos": "true"})
    assert len(r.json()) == 7


async def test_filtro_por_modulo(api, base):
    r = await api.get("/api/projetos/buscar", params={"modulo": "extensao"})
    assert titulos(r) == ["Clínica de leitura", "Horta comunitária"]
    r = await api.get("/api/projetos/buscar", params={"modulo": "invalido"})
    assert r.status_code == 422
    # nome antigo do parâmetro continua aceito
    r = await api.get("/api/projetos/buscar", params={"tipo_sigaa": "extensao"})
    assert titulos(r) == ["Clínica de leitura", "Horta comunitária"]


async def test_filtro_por_instituicao(api, base):
    r = await api.get("/api/projetos/buscar", params={"instituicao": "UNIRIO"})
    assert titulos(r) == ["Clínica de leitura"]
    assert r.json()[0]["palavras_chave"] == ["saúde", "extensão"]
    r = await api.get("/api/projetos/buscar", params={"instituicao": "UNIR", "modulo": "extensao"})
    assert titulos(r) == ["Horta comunitária"]
    assert (await api.get("/api/projetos/instituicoes")).json() == ["UNIR", "UNIRIO"]


async def test_filtro_por_unidade(api, base):
    r = await api.get("/api/projetos/buscar", params={"unidade": "DEPARTAMENTO DE AGRONOMIA"})
    assert titulos(r) == ["Horta comunitária"]


async def test_filtro_por_area_do_conhecimento(api, base):
    r = await api.get("/api/projetos/buscar", params={"area": ENGENHARIAS})
    assert titulos(r) == ["Robótica educacional"]
    assert r.json()[0]["area_conhecimento"] == ENGENHARIAS
    r = await api.get("/api/projetos/buscar", params={"area": AGRARIAS, "modulo": "extensao"})
    assert titulos(r) == ["Horta comunitária"]
    # projetos fora da busca padrão (finalizado, inativo) continuam de fora
    assert titulos(await api.get("/api/projetos/buscar", params={"area": EXATAS})) == ["Sem contato"]
    # só o valor exato da tabela do CNPq
    r = await api.get("/api/projetos/buscar", params={"area": "Agrárias"})
    assert r.status_code == 422


async def test_filtros_trazem_areas_com_contagem_na_ordem_fixa(api, base):
    r = await api.get("/api/projetos/filtros")
    assert r.status_code == 200, r.text
    # só projetos visíveis ("Projeto finalizado" e "Sumiu do SIGAA" não contam), na ordem da tabela do CNPq
    assert r.json()["areas"] == [
        {"nome": EXATAS, "total": 1},
        {"nome": ENGENHARIAS, "total": 1},
        {"nome": SAUDE, "total": 1},
        {"nome": AGRARIAS, "total": 1},
        {"nome": HUMANAS, "total": 1},
    ]


async def test_areas_respeitam_o_recorte_dos_outros_filtros(api, base):
    async def areas(**params):
        r = await api.get("/api/projetos/filtros", params=params)
        assert r.status_code == 200, r.text
        return [(a["nome"], a["total"]) for a in r.json()["areas"]]

    assert await areas(instituicao="UNIR") == [(EXATAS, 1), (ENGENHARIAS, 1), (AGRARIAS, 1)]
    assert await areas(modulo="extensao") == [(SAUDE, 1), (AGRARIAS, 1)]
    assert await areas(q="robótica") == [(ENGENHARIAS, 1)]
    assert await areas(unidade="DEPARTAMENTO DE AGRONOMIA") == [(AGRARIAS, 1)]
    assert await areas(q="nada disso") == []
    # as instituições não dependem do recorte (o front estreita pela quebra por módulo)
    r = (await api.get("/api/projetos/filtros", params={"q": "nada disso"})).json()
    assert [i["sigla"] for i in r["instituicoes"]] == ["UNIR", "UNIRIO"]


async def test_busca_por_titulo_e_por_coordenador(api, base):
    assert titulos(await api.get("/api/projetos/buscar", params={"q": "robótica"})) == ["Robótica educacional"]
    assert titulos(await api.get("/api/projetos/buscar", params={"q": "bruno"})) == ["Horta comunitária"]


async def test_busca_escapa_regex(api, base):
    r = await api.get("/api/projetos/buscar", params={"q": ".*("})
    assert titulos(r) == []


async def test_filtros_combinados_sem_resultado(api, base):
    r = await api.get("/api/projetos/buscar", params={"modulo": "extensao", "q": "robótica"})
    assert r.json() == []


async def test_resposta_publica_nao_expoe_email(api, base):
    projetos = (await api.get("/api/projetos/buscar")).json()
    for p in projetos:
        assert "email_professor" not in p
        assert "email_contato_manual" not in p
    contato = {p["titulo"]: p["tem_contato"] for p in projetos}
    assert contato["Robótica educacional"] is True
    assert contato["Sem contato"] is False
    assert contato["Projeto manual do professor"] is True


async def test_paginacao_por_cursor(api, base):
    p1 = (await api.get("/api/projetos/buscar", params={"page_size": 2})).json()
    p2 = (await api.get("/api/projetos/buscar", params={"page_size": 2, "last_id": p1[-1]["id"]})).json()
    assert len(p1) == 2 and len(p2) == 2
    assert not {p["id"] for p in p1} & {p["id"] for p in p2}


async def test_unidades_distintas_de_projetos_ativos(api, base):
    r = await api.get("/api/projetos/unidades")
    assert r.json() == ["CAMPUS PORTO VELHO", "DEPARTAMENTO DE AGRONOMIA", "ESCOLA DE MEDICINA E CIRURGIA"]
    r = await api.get("/api/projetos/unidades", params={"modulo": "extensao"})
    assert r.json() == ["DEPARTAMENTO DE AGRONOMIA", "ESCOLA DE MEDICINA E CIRURGIA"]
    r = await api.get("/api/projetos/unidades", params={"modulo": "extensao", "instituicao": "UNIR"})
    assert r.json() == ["DEPARTAMENTO DE AGRONOMIA"]


async def test_filtros_agrupados_por_instituicao(api, base):
    r = await api.get("/api/projetos/filtros")
    assert r.status_code == 200, r.text
    insts = r.json()["instituicoes"]
    # fontes externas primeiro (UNIR, UNIRIO), depois a instituição livre do projeto manual (nenhuma aqui)
    assert [i["sigla"] for i in insts] == ["UNIR", "UNIRIO"]
    unir = insts[0]
    assert unir["externa"] is True and unir["rotulo"] == "SIGAA/UNIR"
    # só projetos visíveis: "Projeto finalizado" e "Sumiu do SIGAA" ficam de fora
    assert unir["total"] == 3 and unir["modulos"] == {"pesquisa": 2, "extensao": 1}
    assert unir["unidades"] == [
        {"nome": "CAMPUS PORTO VELHO", "total": 2, "modulos": {"pesquisa": 2}},
        {"nome": "DEPARTAMENTO DE AGRONOMIA", "total": 1, "modulos": {"extensao": 1}},
    ]
    unirio = insts[1]
    assert unirio["total"] == 1 and [u["nome"] for u in unirio["unidades"]] == ["ESCOLA DE MEDICINA E CIRURGIA"]


async def test_filtros_incluem_instituicao_livre_dos_projetos_manuais(api, base):
    await base.projetos.insert_one({"titulo": "Manual com instituição", "nome_professor": "Prof.",
                                    "instituicao": "Universidade Federal de Minas Gerais"})
    insts = (await api.get("/api/projetos/filtros")).json()["instituicoes"]
    assert [i["sigla"] for i in insts] == ["UNIR", "UNIRIO", "Universidade Federal de Minas Gerais"]
    assert insts[2] == {"sigla": "Universidade Federal de Minas Gerais", "rotulo": "Universidade Federal de Minas Gerais",
                        "externa": False, "total": 1, "modulos": {}, "unidades": []}
    # e o valor é aceito pelo filtro da busca (sem 422)
    r = await api.get("/api/projetos/buscar", params={"instituicao": "Universidade Federal de Minas Gerais"})
    assert titulos(r) == ["Manual com instituição"]


async def test_status_exige_professor_ou_pesquisador(api, db):
    # a fixture `api` loga um aluno: a data da coleta é interna da equipe
    assert (await api.get("/api/projetos/fontes/status")).status_code == 403


@pytest.fixture
async def api_professor(db):
    from auth.autenticacao import get_usuario_atual
    from main import app
    from httpx import ASGITransport, AsyncClient
    app.dependency_overrides[get_usuario_atual] = lambda: {"id": "prof-1", "email": "prof@unir.br",
                                                             "papel": "professor", "nome": "Prof."}
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        yield client
    app.dependency_overrides.clear()


async def test_status_sem_runs(api_professor, db):
    api = api_professor
    r = (await api.get("/api/projetos/fontes/status")).json()
    assert r["ultima_atualizacao"] is None
    assert r["fontes"]["sigaa"] == {"instituicao": "UNIR", "rotulo": "SIGAA/UNIR", "ultima_atualizacao": None}
    assert r["fontes"]["unirio"]["ultima_atualizacao"] is None


async def test_status_por_fonte_ignora_falhas_e_dry_runs(api_professor, db):
    api = api_professor
    await db.sigaa_sync_runs.insert_many([
        # runs antigas do SIGAA, sem o campo `fonte`
        {"status": "sucesso", "finalizada_em": datetime(2026, 9, 20, 6, 0, tzinfo=timezone.utc)},
        {"status": "sucesso_com_erros", "finalizada_em": datetime(2026, 9, 27, 6, 0, tzinfo=timezone.utc)},
        {"status": "falha", "finalizada_em": datetime(2026, 9, 28, 6, 0, tzinfo=timezone.utc)},
        {"fonte": "unirio", "status": "sucesso", "finalizada_em": datetime(2026, 9, 21, 7, 0, tzinfo=timezone.utc)},
        {"fonte": "unirio", "status": "sucesso", "dry_run": True,
         "finalizada_em": datetime(2026, 9, 29, 7, 0, tzinfo=timezone.utc)},
    ])
    r = (await api.get("/api/projetos/fontes/status")).json()
    assert r["ultima_atualizacao"].startswith("2026-09-27T06:00:00")
    assert r["fontes"]["sigaa"]["ultima_atualizacao"].startswith("2026-09-27T06:00:00")
    assert r["fontes"]["unirio"]["ultima_atualizacao"].startswith("2026-09-21T07:00:00")
    # rota antiga continua respondendo
    assert (await api.get("/api/projetos/sigaa/status")).json() == r


async def test_projeto_manual_ganha_area_do_conhecimento_ao_ser_criado(api_professor, db):
    api = api_professor
    r = await api.post("/api/projetos", json={"titulo": "Horta na escola",
                                               "descricao": "Cultivo de hortaliças com os alunos"})
    assert r.status_code == 201, r.text
    assert r.json()["area_conhecimento"] == AGRARIAS
    doc = await db.projetos.find_one({"titulo": "Horta na escola"})
    assert doc["area_conhecimento"] == AGRARIAS and doc["autor_id"] == "prof-1"

    # informada pelo autor (aceita sem acentos e em minúsculas, grava o nome canônico)
    r = await api.post("/api/projetos", json={"titulo": "Horta na escola", "descricao": "Cultivo",
                                               "area_conhecimento": "ciencias humanas"})
    assert r.status_code == 201 and r.json()["area_conhecimento"] == HUMANAS

    # fora da tabela do CNPq
    r = await api.post("/api/projetos", json={"titulo": "X", "descricao": "Y", "area_conhecimento": "Tecnologias"})
    assert r.status_code == 422
    assert "Área do conhecimento desconhecida" in r.text

    # vazio conta como não informado
    r = await api.post("/api/projetos", json={"titulo": "Sarau de poesia", "descricao": "Z", "area_conhecimento": ""})
    assert r.status_code == 201 and r.json()["area_conhecimento"] == "Linguística, Letras e Artes"


async def test_editar_projeto_manual_reclassifica_quando_a_area_nao_vem(api_professor, db):
    api = api_professor
    criado = (await api.post("/api/projetos", json={"titulo": "Horta na escola", "descricao": "Cultivo"})).json()
    assert criado["area_conhecimento"] == AGRARIAS

    r = await api.put(f"/api/projetos/{criado['id']}", json={"titulo": "Oficina de violão", "descricao": "Música"})
    assert r.status_code == 200, r.text
    assert r.json()["area_conhecimento"] == "Linguística, Letras e Artes"

    r = await api.put(f"/api/projetos/{criado['id']}", json={"titulo": "Oficina de violão", "descricao": "Música",
                                                              "area_conhecimento": HUMANAS})
    assert r.status_code == 200 and r.json()["area_conhecimento"] == HUMANAS
    assert (await db.projetos.find_one({"_id": ObjectId(criado["id"])}))["area_conhecimento"] == HUMANAS

    # e o projeto manual aparece na busca pública pela área
    r = await api.get("/api/projetos/buscar", params={"area": HUMANAS})
    assert titulos(r) == ["Oficina de violão"]


async def test_projeto_coletado_sem_situacao_nao_aparece(api, base):
    # detalhe da pesquisa da UNIRIO falhou: situação desconhecida, fica de fora
    await base.projetos.insert_one({"origem": "unirio", "chave_unirio": "pesquisa|x", "modulo": "pesquisa",
                                    "titulo": "Situação desconhecida", "instituicao": "UNIRIO", "ativo": True})
    r = await api.get("/api/projetos/buscar")
    assert "Situação desconhecida" not in titulos(r)
    assert "Projeto manual do professor" in titulos(r)  # manual sem situação continua
