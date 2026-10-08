"""Correções da revisão pré-deploy: usernames longos, seed/votos atômicos,
login sem senha, migração dos tópicos legados do fórum."""

from datetime import datetime, timezone

from bson import ObjectId
from httpx import ASGITransport, AsyncClient

from auth.autenticacao import get_usuario_atual
from controllers.usuario_controller import registrar_usuario_controller
from database.indexes import criar_indices, migrar_dados, migrar_forum_legado
from jobs import seed_forum as seed
from main import app
from models.usuario_model import UsuarioCreate
from services import usernames


# ── usernames ───────────────────────────────────────────────────────────────

async def test_homonimos_com_nome_comprido_recebem_usernames_distintos(db):
    await criar_indices(db)
    nome = "Maria Aparecida dos Santos Oliveira Ferreira"
    gerados = []
    for i in range(4):
        u = await usernames.gerar_username_unico(db, nome)
        await db.usuarios.insert_one({"email": f"m{i}@ufrj.br", "nome": nome, "username": u})
        gerados.append(u)
    assert len(set(gerados)) == 4
    assert all(len(u) <= usernames.USERNAME_MAX for u in gerados)
    assert gerados[0] == "maria-aparecida-dos-santos-oli"
    assert gerados[1].endswith("-2") and gerados[2].endswith("-3") and gerados[3].endswith("-4")


def test_prefixo_comum_cobre_o_encurtamento():
    assert usernames._prefixo_comum("ana-souza") == "ana-souza"
    longo = "maria-aparecida-dos-santos-oli"
    assert len(longo) == 30
    prefixo = usernames._prefixo_comum(longo)
    assert all(c.startswith(prefixo) for c, _ in zip(usernames.candidatos_username(longo), range(200)))


async def test_backfill_tolera_colisao_com_o_indice(db):
    await criar_indices(db)
    await db.usuarios.insert_many([
        {"email": "a@ufrj.br", "nome": "João Silva", "username": "joao-silva"},
        {"email": "b@ufrj.br", "nome": "João Silva", "username": "joao-silva-2"},
        {"email": "c@ufrj.br", "nome": "João Silva"},
        {"email": "d@ufrj.br", "nome": "João Silva"},
    ])
    assert await usernames.preencher_usernames(db) == 2
    todos = sorted(u["username"] for u in await db.usuarios.find().to_list(None))
    assert todos == ["joao-silva", "joao-silva-2", "joao-silva-3", "joao-silva-4"]


async def test_registro_sobrevive_a_corrida_no_username(db, monkeypatch):
    await criar_indices(db)
    # alguém cria "ana-souza" entre a consulta e o insert
    original = usernames.gerar_username_unico
    chamadas = []

    async def com_corrida(db_, nome, evitar=()):
        u = await original(db_, nome, evitar=evitar)
        if not chamadas:
            await db_.usuarios.insert_one({"email": "rival@ufrj.br", "nome": nome, "username": u})
        chamadas.append(u)
        return u

    monkeypatch.setattr("controllers.usuario_controller.gerar_username_unico", com_corrida)
    criado = await registrar_usuario_controller(UsuarioCreate(
        email="ana@ufrj.br", senha="segredo1", nome="Ana Souza", papel="aluno",
        aceite_regras=True, aceite_dados=True))
    assert criado["username"] == "ana-souza-2"


# ── login sem senha ─────────────────────────────────────────────────────────

async def test_login_em_conta_sem_senha_da_401_e_nao_500(db):
    await seed.garantir_usuario_sistema(db)
    await db.usuarios.insert_one({"email": "so-orcid@ufrj.br", "nome": "X", "papel": "pesquisador",
                                  "orcid": {"orcid_id": "0000-0001-0000-0000"}})
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        for email in (seed.USUARIO_SISTEMA["email"], "so-orcid@ufrj.br", "ninguem@ufrj.br"):
            r = await client.post("/api/auth/login", json={"email": email, "senha": "qualquer"})
            assert r.status_code == 401, (email, r.text)


# ── seed idempotente ────────────────────────────────────────────────────────

async def test_seed_duas_vezes_nao_duplica_usuario_nem_perguntas(db):
    agora = datetime(2026, 10, 1, 12, tzinfo=timezone.utc)
    assert await seed.seed_forum(db, agora=agora) == seed.TOTAL_SEED
    assert await seed.seed_forum(db, agora=agora) == 0
    assert await db.usuarios.count_documents({"email": seed.USUARIO_SISTEMA["email"]}) == 1
    assert await db.topicos_forum.count_documents({"seed": seed.SEED_VERSAO}) == seed.TOTAL_SEED
    indices = await db.topicos_forum.index_information()
    assert "uniq_seed_chave" in indices


# ── votos atômicos ──────────────────────────────────────────────────────────

async def _cliente(usuario: dict):
    app.dependency_overrides[get_usuario_atual] = lambda: dict(usuario)
    return AsyncClient(transport=ASGITransport(app=app), base_url="http://test")


async def test_reagir_em_topico_legado_e_toggle(db):
    tid = (await db.topicos_forum.insert_one({
        "titulo": "RNA", "conteudo_original": "DNA", "autor_email": "x@gmail.com", "likes": 0, "dislikes": 0,
        "visualizacoes": 0, "data_criacao": datetime.now(timezone.utc)})).inserted_id
    ana = {"id": str(ObjectId()), "email": "ana@ufrj.br", "papel": "aluno", "nome": "Ana"}
    bia = {"id": str(ObjectId()), "email": "bia@ufrj.br", "papel": "aluno", "nome": "Bia"}
    try:
        async with await _cliente(ana) as c:
            r = await c.post(f"/api/forum/topicos/{tid}/reagir", json={"tipo": "like"})
            assert r.status_code == 200, r.text
            assert r.json()["likes"] == [ana["id"]] and r.json()["dislikes"] == []
            # troca para dislike: sai de likes, entra em dislikes
            r = await c.post(f"/api/forum/topicos/{tid}/reagir", json={"tipo": "dislike"})
            assert r.json()["likes"] == [] and r.json()["dislikes"] == [ana["id"]]
            # mesmo voto de novo: toggle off
            r = await c.post(f"/api/forum/topicos/{tid}/reagir", json={"tipo": "dislike"})
            assert r.json()["dislikes"] == []
            await c.post(f"/api/forum/topicos/{tid}/reagir", json={"tipo": "like"})
        async with await _cliente(bia) as c:
            r = await c.post(f"/api/forum/topicos/{tid}/reagir", json={"tipo": "like"})
            # o voto da Ana continua lá: nada de read-modify-write
            assert sorted(r.json()["likes"]) == sorted([ana["id"], bia["id"]])
            assert "autor_email" not in r.json()
    finally:
        app.dependency_overrides.clear()


# ── migração dos tópicos legados ────────────────────────────────────────────

async def test_migrar_forum_legado_troca_email_por_autor_id(db):
    uid = (await db.usuarios.insert_one({"email": "heysovietju@gmail.com", "nome": "Ju", "papel": "aluno"})).inserted_id
    await db.topicos_forum.insert_many([
        {"titulo": "RNA", "descricao": "DNA", "autor_email": "heysovietju@gmail.com", "likes": 0, "dislikes": 0,
         "visualizacoes": 0, "votos_usuarios": {}},
        {"titulo": "Sem dono", "autor_email": "ninguem@x.com", "likes": [], "dislikes": []},
        {"titulo": "Novo", "autor_id": "abc", "likes": [], "dislikes": []},
    ])
    contagem = await migrar_forum_legado(db)
    assert contagem == {"autores": 1, "emails_removidos": 2, "votos": 1}
    rna = await db.topicos_forum.find_one({"titulo": "RNA"})
    assert rna["autor_id"] == str(uid) and "autor_email" not in rna
    assert rna["likes"] == [] and rna["dislikes"] == []
    assert "autor_email" not in await db.topicos_forum.find_one({"titulo": "Sem dono"})
    assert await db.topicos_forum.count_documents({"autor_email": {"$exists": True}}) == 0
    # idempotente
    assert await migrar_forum_legado(db) == {"autores": 0, "emails_removidos": 0, "votos": 0}
    # a dona do e-mail agora é reconhecida como autora pelo app (autor_id)
    await migrar_dados(db)
    assert (await db.topicos_forum.find_one({"titulo": "RNA"}))["autor_id"] == str(uid)
