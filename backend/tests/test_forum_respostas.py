"""Fórum: respostas aos tópicos (um único nível), contador `total_respostas`,
paginação, autoria, perfil incompleto, exclusão em cascata e privacidade."""

import json
from datetime import datetime, timedelta, timezone

import pytest
from bson import ObjectId
from httpx import ASGITransport, AsyncClient

from auth.autenticacao import get_usuario_atual
from database.indexes import criar_indices
from main import app
from routes import forum_routes

T0 = datetime(2026, 9, 1, 12, tzinfo=timezone.utc)


def _entrar(usuario: dict) -> None:
    """Troca o usuário logado do cliente `api` (o fixture limpa no fim)."""
    app.dependency_overrides[get_usuario_atual] = lambda: dict(usuario)


async def _conta(db, nome: str, username: str, **extra) -> dict:
    oid = ObjectId()
    email = f"{username}@unirio.br"
    await db.usuarios.insert_one({"_id": oid, "email": email, "nome": nome, "username": username,
                                  "papel": "aluno", **extra})
    return {"id": str(oid), "email": email, "papel": "aluno", "nome": nome, **extra}


@pytest.fixture
async def ana(db):
    return await _conta(db, "Ana Souza", "ana-souza")


@pytest.fixture
async def bia(db):
    return await _conta(db, "Beatriz Lima", "beatriz-lima", nome_social="Bia")


async def _topico(db, **extra) -> str:
    doc = {
        "titulo": "Como funciona o PIBIC?", "conteudo_original": "Texto da pergunta.",
        "data_criacao": T0, "visualizacoes": 0, "likes": [], "dislikes": [],
    }
    doc.update(extra)
    return str((await db.topicos_forum.insert_one(doc)).inserted_id)


async def _respostas_no_banco(db, topico_id: str, quantidade: int, autor_id: str = "", inicio=T0) -> None:
    """Respostas gravadas direto no banco, uma por minuto a partir de `inicio`."""
    await db.respostas_forum.insert_many([
        {"topico_id": topico_id, "autor_id": autor_id, "conteudo": f"Resposta {i}",
         "data_criacao": inicio + timedelta(minutes=i)}
        for i in range(quantidade)
    ])


async def _total_no_banco(db, topico_id: str):
    return (await db.topicos_forum.find_one({"_id": ObjectId(topico_id)})).get("total_respostas")


@pytest.fixture
def finds_em_usuarios(db, monkeypatch):
    """Conta as chamadas a `find` na collection `usuarios`."""
    chamadas = []
    classe = type(db.usuarios)
    original = classe.find

    def find_contado(self, *args, **kwargs):
        if self.name == "usuarios":
            chamadas.append(args)
        return original(self, *args, **kwargs)

    monkeypatch.setattr(classe, "find", find_contado)
    return chamadas


# ── Criar e listar ──────────────────────────────────────────────────────────

async def test_resposta_criada_com_autor_e_texto_sem_espacos_nas_pontas(api, db, ana):
    tid = await _topico(db)
    _entrar(ana)

    r = await api.post(f"/api/forum/topicos/{tid}/respostas", json={"conteudo": "  Procure a PROPESQ.\n\nBoa sorte!  "})
    assert r.status_code == 201, r.text
    corpo = r.json()
    assert corpo["topico_id"] == tid and corpo["conteudo"] == "Procure a PROPESQ.\n\nBoa sorte!"
    assert (corpo["autor_id"], corpo["autor_username"], corpo["autor_nome"]) == (ana["id"], "ana-souza", "Ana Souza")
    assert corpo["data_criacao"] and corpo["editado_em"] is None

    doc = await db.respostas_forum.find_one({"_id": ObjectId(corpo["id"])})
    assert set(doc) == {"_id", "topico_id", "autor_id", "conteudo", "data_criacao"}


async def test_lista_em_ordem_cronologica_com_o_total(api, db, ana, bia):
    tid = await _topico(db)
    # Gravadas fora de ordem: a API devolve da mais antiga para a mais nova.
    await db.respostas_forum.insert_many([
        {"topico_id": tid, "autor_id": bia["id"], "conteudo": "terceira", "data_criacao": T0 + timedelta(hours=2)},
        {"topico_id": tid, "autor_id": ana["id"], "conteudo": "primeira", "data_criacao": T0},
        {"topico_id": tid, "autor_id": "nao-e-objectid", "conteudo": "segunda", "data_criacao": T0 + timedelta(hours=1)},
    ])
    await _respostas_no_banco(db, await _topico(db, titulo="Outro"), 4)  # de outro tópico: não entram

    r = await api.get(f"/api/forum/topicos/{tid}/respostas")
    assert r.status_code == 200, r.text
    assert r.json()["total"] == 3
    respostas = r.json()["respostas"]
    assert [x["conteudo"] for x in respostas] == ["primeira", "segunda", "terceira"]
    assert [x["autor_username"] for x in respostas] == ["ana-souza", "usuario", "beatriz-lima"]
    assert [x["autor_nome"] for x in respostas] == ["Ana Souza", "Usuário", "Bia"]


async def test_limite_padrao_de_10_e_paginacao(api, db):
    tid = await _topico(db)
    await _respostas_no_banco(db, tid, 25)
    url = f"/api/forum/topicos/{tid}/respostas"

    padrao = (await api.get(url)).json()
    assert padrao["total"] == 25
    assert [x["conteudo"] for x in padrao["respostas"]] == [f"Resposta {i}" for i in range(10)]

    meio = (await api.get(url, params={"limite": 10, "pular": 10})).json()["respostas"]
    assert [x["conteudo"] for x in meio] == [f"Resposta {i}" for i in range(10, 20)]
    fim = (await api.get(url, params={"limite": 10, "pular": 20})).json()["respostas"]
    assert [x["conteudo"] for x in fim] == [f"Resposta {i}" for i in range(20, 25)]
    assert (await api.get(url, params={"pular": 30})).json() == {"total": 25, "respostas": []}

    todas = (await api.get(url, params={"limite": 50})).json()["respostas"]
    assert len(todas) == 25

    for params in ({"limite": 0}, {"limite": 51}, {"pular": -1}, {"limite": "x"}):
        assert (await api.get(url, params=params)).status_code == 422, params


async def test_paginacao_estavel_com_respostas_no_mesmo_instante(api, db):
    tid = await _topico(db)
    await db.respostas_forum.insert_many([
        {"topico_id": tid, "autor_id": "", "conteudo": f"R{i}", "data_criacao": T0} for i in range(7)
    ])
    url = f"/api/forum/topicos/{tid}/respostas"
    vistas = []
    for pular in (0, 3, 6):
        vistas += [x["id"] for x in (await api.get(url, params={"limite": 3, "pular": pular})).json()["respostas"]]
    assert len(vistas) == 7 and len(set(vistas)) == 7
    assert vistas == sorted(vistas)  # desempate pelo _id, que cresce com a inserção


async def test_obter_topico_traz_as_primeiras_10_respostas_e_autores_em_lote(api, db, ana, bia, finds_em_usuarios):
    tid = await _topico(db, autor_id=bia["id"])
    _entrar(ana)
    for i in range(12):
        r = await api.post(f"/api/forum/topicos/{tid}/respostas", json={"conteudo": f"Resposta {i}"})
        assert r.status_code == 201, r.text

    finds_em_usuarios.clear()
    r = await api.get(f"/api/forum/topicos/{tid}")
    assert r.status_code == 200, r.text
    corpo = r.json()
    assert corpo["total_respostas"] == 12 and corpo["visualizacoes"] == 1
    assert [x["conteudo"] for x in corpo["respostas"]] == [f"Resposta {i}" for i in range(10)]
    assert corpo["autor_username"] == "beatriz-lima"
    assert {x["autor_username"] for x in corpo["respostas"]} == {"ana-souza"}
    # Autor do tópico e das respostas resolvidos numa única consulta.
    assert len(finds_em_usuarios) == 1
    assert set(finds_em_usuarios[0][0]["_id"]["$in"]) == {ObjectId(ana["id"]), ObjectId(bia["id"])}

    todas = (await api.get(f"/api/forum/topicos/{tid}", params={"limite_respostas": 50})).json()
    assert len(todas["respostas"]) == 12
    assert (await api.get(f"/api/forum/topicos/{tid}", params={"limite_respostas": 0})).json()["respostas"] == []
    assert (await api.get(f"/api/forum/topicos/{tid}", params={"limite_respostas": 51})).status_code == 422

    # A listagem de tópicos traz só o contador, não as respostas.
    lista = (await api.get("/api/forum/topicos")).json()
    assert lista[0]["total_respostas"] == 12 and "respostas" not in lista[0]


# ── Contador total_respostas ────────────────────────────────────────────────

async def test_total_respostas_sobe_ao_responder_e_desce_ao_excluir(api, db):
    criado = await api.post("/api/forum/topicos", json={"titulo": "Dúvida", "conteudo": "Conteúdo"})
    assert criado.status_code == 201 and criado.json()["total_respostas"] == 0
    tid = criado.json()["id"]
    legado = await _topico(db, titulo="Legado sem contador")

    ids = []
    for alvo in (tid, tid, legado):
        r = await api.post(f"/api/forum/topicos/{alvo}/respostas", json={"conteudo": "Uma resposta"})
        assert r.status_code == 201, r.text
        ids.append(r.json()["id"])
    assert await _total_no_banco(db, tid) == 2
    assert await _total_no_banco(db, legado) == 1  # $inc cria o campo

    por_id = {t["id"]: t for t in (await api.get("/api/forum/topicos")).json()}
    assert por_id[tid]["total_respostas"] == 2 and por_id[legado]["total_respostas"] == 1

    assert (await api.delete(f"/api/forum/respostas/{ids[0]}")).status_code == 204
    assert await _total_no_banco(db, tid) == 1
    # Excluir de novo não desconta outra vez.
    assert (await api.delete(f"/api/forum/respostas/{ids[0]}")).status_code == 404
    assert await _total_no_banco(db, tid) == 1
    assert (await api.get(f"/api/forum/topicos/{tid}")).json()["total_respostas"] == 1


async def test_topico_antigo_sem_contador_aparece_com_zero(api, db):
    tid = await _topico(db)
    assert (await api.get("/api/forum/topicos")).json()[0]["total_respostas"] == 0
    assert (await api.get(f"/api/forum/topicos/{tid}")).json()["total_respostas"] == 0


async def test_contador_nunca_fica_negativo(api, db):
    tid = await _topico(db, total_respostas=0)
    rid = (await db.respostas_forum.insert_one(
        {"topico_id": tid, "autor_id": "aluno-1", "conteudo": "x", "data_criacao": T0})).inserted_id
    assert (await api.delete(f"/api/forum/respostas/{rid}")).status_code == 204
    assert await _total_no_banco(db, tid) == 0


# ── Privacidade ─────────────────────────────────────────────────────────────

async def test_nenhuma_resposta_da_api_expoe_email(api, db, ana):
    tid = await _topico(db, autor_id=ana["id"])
    # Resposta antiga com um e-mail gravado por engano: mesmo assim não sai.
    await db.respostas_forum.insert_one({"topico_id": tid, "autor_id": ana["id"], "autor_email": ana["email"],
                                         "conteudo": "antiga", "data_criacao": T0})
    _entrar(ana)

    criada = await api.post(f"/api/forum/topicos/{tid}/respostas", json={"conteudo": "nova"})
    rid = criada.json()["id"]
    editada = await api.patch(f"/api/forum/respostas/{rid}", json={"conteudo": "editada"})
    lista = await api.get(f"/api/forum/topicos/{tid}/respostas")
    topico = await api.get(f"/api/forum/topicos/{tid}")
    topicos = await api.get("/api/forum/topicos")

    for r in (criada, editada, lista, topico, topicos):
        assert r.status_code in (200, 201), r.text
        texto = json.dumps(r.json())
        assert ana["email"] not in texto and "autor_email" not in texto and "@unirio.br" not in texto

    doc = await db.respostas_forum.find_one({"_id": ObjectId(rid)})
    assert "autor_email" not in doc and "email" not in doc


# ── Autoria ─────────────────────────────────────────────────────────────────

async def test_apenas_o_autor_edita_e_exclui_a_resposta(api, db, ana, bia):
    tid = await _topico(db)
    _entrar(ana)
    rid = (await api.post(f"/api/forum/topicos/{tid}/respostas", json={"conteudo": "da Ana"})).json()["id"]

    _entrar(bia)
    r = await api.patch(f"/api/forum/respostas/{rid}", json={"conteudo": "da Bia"})
    assert r.status_code == 403 and "Apenas o autor" in r.json()["detail"]
    assert (await api.delete(f"/api/forum/respostas/{rid}")).status_code == 403
    assert (await db.respostas_forum.find_one({"_id": ObjectId(rid)}))["conteudo"] == "da Ana"
    assert await _total_no_banco(db, tid) == 1

    _entrar(ana)
    r = await api.patch(f"/api/forum/respostas/{rid}", json={"conteudo": "  da Ana, revisada  "})
    assert r.status_code == 200, r.text
    assert r.json()["conteudo"] == "da Ana, revisada" and r.json()["editado_em"]
    assert r.json()["autor_username"] == "ana-souza"
    assert (await api.delete(f"/api/forum/respostas/{rid}")).status_code == 204
    assert await db.respostas_forum.count_documents({}) == 0
    assert await _total_no_banco(db, tid) == 0


async def test_perfil_incompleto_recebe_403_e_continua_lendo(api, db, ana):
    tid = await _topico(db)
    _entrar(ana)
    rid = (await api.post(f"/api/forum/topicos/{tid}/respostas", json={"conteudo": "ok"})).json()["id"]

    _entrar({**ana, "perfil_completo": False})
    r = await api.post(f"/api/forum/topicos/{tid}/respostas", json={"conteudo": "sem perfil"})
    assert r.status_code == 403 and "Complete seu perfil" in r.json()["detail"]
    assert (await api.patch(f"/api/forum/respostas/{rid}", json={"conteudo": "x"})).status_code == 403
    assert (await api.delete(f"/api/forum/respostas/{rid}")).status_code == 403
    assert await db.respostas_forum.count_documents({}) == 1 and await _total_no_banco(db, tid) == 1

    r = await api.get(f"/api/forum/topicos/{tid}/respostas")
    assert r.status_code == 200 and r.json()["total"] == 1


async def test_visitante_le_mas_nao_responde(db):
    tid = await _topico(db)
    await _respostas_no_banco(db, tid, 2)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as visitante:
        assert (await visitante.get(f"/api/forum/topicos/{tid}/respostas")).json()["total"] == 2
        r = await visitante.post(f"/api/forum/topicos/{tid}/respostas", json={"conteudo": "oi"})
        assert r.status_code == 401


# ── Validação do conteúdo ───────────────────────────────────────────────────

async def test_conteudo_de_1_a_5000_caracteres_depois_do_strip(api, db):
    tid = await _topico(db)
    url = f"/api/forum/topicos/{tid}/respostas"

    vazio = await api.post(url, json={"conteudo": "   \n  "})
    assert vazio.status_code == 422 and "Escreva o texto da resposta" in vazio.text
    longo = await api.post(url, json={"conteudo": "a" * 5001})
    assert longo.status_code == 422 and "5.000" in longo.text
    assert (await api.post(url, json={})).status_code == 422

    no_limite = await api.post(url, json={"conteudo": "  " + "a" * 5000 + "  "})
    assert no_limite.status_code == 201 and len(no_limite.json()["conteudo"]) == 5000
    assert (await api.post(url, json={"conteudo": "a"})).status_code == 201

    rid = no_limite.json()["id"]
    assert (await api.patch(f"/api/forum/respostas/{rid}", json={"conteudo": " "})).status_code == 422
    assert await db.respostas_forum.count_documents({}) == 2 and await _total_no_banco(db, tid) == 2


async def test_resposta_tem_um_unico_nivel(api, db):
    """Não há resposta de resposta: campos extras (ex.: um "pai") são ignorados."""
    tid = await _topico(db)
    url = f"/api/forum/topicos/{tid}/respostas"
    rid = (await api.post(url, json={"conteudo": "primeira"})).json()["id"]
    r = await api.post(url, json={"conteudo": "segunda", "resposta_pai_id": rid})
    assert r.status_code == 201
    assert "resposta_pai_id" not in await db.respostas_forum.find_one({"_id": ObjectId(r.json()["id"])})
    assert (await api.post(f"/api/forum/respostas/{rid}/respostas", json={"conteudo": "x"})).status_code in (404, 405)


# ── Exclusão do tópico ──────────────────────────────────────────────────────

async def test_excluir_topico_apaga_as_respostas_dele(api, db):
    tid = (await api.post("/api/forum/topicos", json={"titulo": "Apagar", "conteudo": "x"})).json()["id"]
    outro = await _topico(db, titulo="Fica")
    for alvo in (tid, tid, tid, outro):
        assert (await api.post(f"/api/forum/topicos/{alvo}/respostas", json={"conteudo": "r"})).status_code == 201

    assert (await api.delete(f"/api/forum/topicos/{tid}")).status_code == 204
    assert await db.respostas_forum.count_documents({"topico_id": tid}) == 0
    assert await db.respostas_forum.count_documents({"topico_id": outro}) == 1
    assert (await api.get(f"/api/forum/topicos/{tid}/respostas")).status_code == 404


async def test_resposta_nao_fica_orfa_se_o_topico_some_no_meio(api, db, monkeypatch):
    """Tópico excluído entre a checagem e o insert: 404 e nenhuma resposta sobra."""
    async def checagem_que_passa(db_, oid):
        return None

    monkeypatch.setattr(forum_routes, "_exigir_topico", checagem_que_passa)
    r = await api.post(f"/api/forum/topicos/{ObjectId()}/respostas", json={"conteudo": "tarde demais"})
    assert r.status_code == 404
    assert await db.respostas_forum.count_documents({}) == 0


# ── IDs inválidos e inexistentes ────────────────────────────────────────────

async def test_ids_invalidos_dao_400_e_inexistentes_404(api, db):
    corpo = {"conteudo": "texto"}
    assert (await api.get("/api/forum/topicos/nao-e-id/respostas")).status_code == 400
    assert (await api.post("/api/forum/topicos/nao-e-id/respostas", json=corpo)).status_code == 400
    assert (await api.patch("/api/forum/respostas/nao-e-id", json=corpo)).status_code == 400
    assert (await api.delete("/api/forum/respostas/nao-e-id")).status_code == 400

    r = await api.get(f"/api/forum/topicos/{ObjectId()}/respostas")
    assert r.status_code == 404 and r.json()["detail"] == "Tópico não encontrado."
    assert (await api.post(f"/api/forum/topicos/{ObjectId()}/respostas", json=corpo)).status_code == 404
    r = await api.patch(f"/api/forum/respostas/{ObjectId()}", json=corpo)
    assert r.status_code == 404 and r.json()["detail"] == "Resposta não encontrada."
    assert (await api.delete(f"/api/forum/respostas/{ObjectId()}")).status_code == 404
    assert await db.respostas_forum.count_documents({}) == 0


# ── Índice ──────────────────────────────────────────────────────────────────

async def test_criar_indices_inclui_respostas_por_topico(db):
    await criar_indices(db)
    indice = (await db.respostas_forum.index_information())["respostas_por_topico"]
    assert indice["key"] == [("topico_id", 1), ("data_criacao", 1), ("_id", 1)]
