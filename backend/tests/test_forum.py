"""Fórum: privacidade (sem e-mail), autores em lote, visualizações, seed e usernames."""

import json
from datetime import datetime, timedelta, timezone

import pytest
from bson import ObjectId

from controllers.usuario_controller import registrar_usuario_controller
from database.indexes import criar_indices, migrar_dados
from jobs import seed_forum as seed
from models.usuario_model import UsuarioCreate
from services import usernames
from tests.conftest import ALUNO


def _sem_email(payload) -> bool:
    """Nenhum objeto da resposta (lista ou dict) traz a chave `autor_email`."""
    itens = payload if isinstance(payload, list) else [payload]
    return all("autor_email" not in item for item in itens)


async def _usuario(db, nome, **extra):
    doc = {"email": f"{ObjectId()}@exemplo.com", "nome": nome, "papel": "aluno", **extra}
    return str((await db.usuarios.insert_one(doc)).inserted_id)


async def _topico(db, **extra):
    doc = {
        "titulo": "Como funciona o PIBIC?", "conteudo_original": "Texto da pergunta.",
        "data_criacao": datetime.now(timezone.utc), "visualizacoes": 0, "likes": [], "dislikes": [],
    }
    doc.update(extra)
    return str((await db.topicos_forum.insert_one(doc)).inserted_id)


@pytest.fixture
def finds_em_usuarios(db, monkeypatch):
    """Conta as chamadas a `find` na collection `usuarios` (uma por listagem)."""
    chamadas = []
    classe = type(db.usuarios)
    original = classe.find

    def find_contado(self, *args, **kwargs):
        if self.name == "usuarios":
            chamadas.append(args)
        return original(self, *args, **kwargs)

    monkeypatch.setattr(classe, "find", find_contado)
    return chamadas


# ── Privacidade: e-mail nunca sai da API ──

async def test_nenhuma_resposta_do_forum_expoe_email(api, db):
    # Doc legado: só e-mail, likes como inteiro.
    await _topico(db, autor_email="antigo@exemplo.com", likes=0, dislikes=0, descricao="legado")

    criado = await api.post("/api/forum/topicos", json={"titulo": "Dúvida", "conteudo": "Conteúdo"})
    assert criado.status_code == 201, criado.text
    assert _sem_email(criado.json())
    tid = criado.json()["id"]

    # O tópico novo nem grava o e-mail: autoria só por `autor_id`.
    doc = await db.topicos_forum.find_one({"_id": ObjectId(tid)})
    assert "autor_email" not in doc and doc["autor_id"] == ALUNO["id"]

    editado = await api.patch(f"/api/forum/topicos/{tid}", json={"titulo": "Dúvida editada"})
    assert editado.status_code == 200 and _sem_email(editado.json())
    assert editado.json()["titulo"] == "Dúvida editada"

    reagido = await api.post(f"/api/forum/topicos/{tid}/reagir", json={"tipo": "like"})
    assert reagido.status_code == 200 and _sem_email(reagido.json())
    assert reagido.json()["likes"] == [ALUNO["id"]]

    um = await api.get(f"/api/forum/topicos/{tid}")
    assert um.status_code == 200 and _sem_email(um.json())

    lista = await api.get("/api/forum/topicos")
    assert lista.status_code == 200, lista.text
    assert len(lista.json()) == 2 and _sem_email(lista.json())
    assert "antigo@exemplo.com" not in json.dumps(lista.json())

    legado = next(t for t in lista.json() if t["descricao"] == "legado")
    assert legado["likes"] == [] and legado["dislikes"] == []
    assert legado["autor_username"] == "usuario" and legado["autor_nome"] == "Usuário"


async def test_autoria_por_id_e_fallback_por_email_em_docs_legados(api, db):
    de_outro = await _topico(db, autor_id="outra-pessoa")
    assert (await api.patch(f"/api/forum/topicos/{de_outro}", json={"titulo": "x"})).status_code == 403
    assert (await api.delete(f"/api/forum/topicos/{de_outro}")).status_code == 403

    legado_meu = await _topico(db, autor_email=ALUNO["email"])
    assert (await api.patch(f"/api/forum/topicos/{legado_meu}", json={"titulo": "ok"})).status_code == 200
    assert (await api.delete(f"/api/forum/topicos/{legado_meu}")).status_code == 204


async def test_limite_devolve_so_os_mais_recentes(api, db):
    agora = datetime.now(timezone.utc)
    for dias, titulo in ((3, "antigo"), (1, "recente"), (2, "meio"), (0, "hoje")):
        await _topico(db, titulo=titulo, data_criacao=agora - timedelta(days=dias))

    r = await api.get("/api/forum/topicos?limite=3")
    assert r.status_code == 200, r.text
    assert [t["titulo"] for t in r.json()] == ["hoje", "recente", "meio"]

    assert len((await api.get("/api/forum/topicos")).json()) == 4
    assert (await api.get("/api/forum/topicos?limite=0")).status_code == 422


# ── Autores resolvidos em lote ──

async def test_autores_resolvidos_com_uma_consulta(api, db, finds_em_usuarios):
    ana = await _usuario(db, "Ana Souza", username="ana-souza")
    bia = await _usuario(db, "Beatriz Lima", nome_social="Bia", username="beatriz-lima")
    await _topico(db, autor_id=ana, titulo="A")
    await _topico(db, autor_id=bia, titulo="B")
    await _topico(db, autor_id=ana, titulo="A2")
    await _topico(db, autor_id="nao-e-objectid", titulo="C")
    await _topico(db, autor_id=str(ObjectId()), titulo="D")  # conta apagada
    await _topico(db, autor_email="legado@exemplo.com", titulo="E")

    r = await api.get("/api/forum/topicos")
    assert r.status_code == 200, r.text
    por_titulo = {t["titulo"]: t for t in r.json()}

    assert (por_titulo["A"]["autor_username"], por_titulo["A"]["autor_nome"]) == ("ana-souza", "Ana Souza")
    assert (por_titulo["A2"]["autor_username"], por_titulo["A2"]["autor_nome"]) == ("ana-souza", "Ana Souza")
    assert (por_titulo["B"]["autor_username"], por_titulo["B"]["autor_nome"]) == ("beatriz-lima", "Bia")
    for titulo in ("C", "D", "E"):
        assert (por_titulo[titulo]["autor_username"], por_titulo[titulo]["autor_nome"]) == ("usuario", "Usuário")

    assert len(finds_em_usuarios) == 1
    filtro = finds_em_usuarios[0][0]
    assert set(filtro["_id"]["$in"]) == {ObjectId(ana), ObjectId(bia), ObjectId(por_titulo["D"]["autor_id"])}


async def test_usuario_sem_username_aparece_como_usuario(api, db):
    sem_username = await _usuario(db, "Carlos Antigo")
    await _topico(db, autor_id=sem_username)
    t = (await api.get("/api/forum/topicos")).json()[0]
    assert t["autor_username"] == "usuario" and t["autor_nome"] == "Carlos Antigo"


# ── GET de um tópico ──

async def test_obter_topico_incrementa_visualizacoes(api, db):
    autor = await _usuario(db, "Ana Souza", username="ana-souza")
    tid = await _topico(db, autor_id=autor)

    r1 = await api.get(f"/api/forum/topicos/{tid}")
    r2 = await api.get(f"/api/forum/topicos/{tid}")
    assert r1.status_code == r2.status_code == 200
    assert r1.json()["visualizacoes"] == 1 and r2.json()["visualizacoes"] == 2
    assert r2.json()["autor_username"] == "ana-souza"
    assert (await db.topicos_forum.find_one({"_id": ObjectId(tid)}))["visualizacoes"] == 2

    assert (await api.get(f"/api/forum/topicos/{ObjectId()}")).status_code == 404
    assert (await api.get("/api/forum/topicos/nao-e-id")).status_code == 400


# ── Seed ──

async def test_seed_e_idempotente_e_cria_usuario_de_sistema_uma_vez(api, db):
    assert 12 <= len(seed.PERGUNTAS) <= 15
    agora = datetime(2026, 10, 7, 12, tzinfo=timezone.utc)

    assert await seed.seed_forum(db, agora=agora) == seed.TOTAL_SEED
    assert await seed.seed_forum(db, agora=agora) == 0
    assert await db.topicos_forum.count_documents({"seed": "forum_v1"}) == seed.TOTAL_SEED

    sistemas = await db.usuarios.find({"email": "forum@uniresu.org"}).to_list(10)
    assert len(sistemas) == 1
    sistema = sistemas[0]
    assert sistema["username"] == "uniresu" and sistema["nome"] == "Equipe UniResu"
    assert sistema["papel"] == "professor" and sistema["sistema"] is True
    assert "senha_hash" not in sistema  # não consegue logar

    topicos = await db.topicos_forum.find({"seed": "forum_v1"}).to_list(100)
    chaves = [t["seed_chave"] for t in topicos]
    assert len(set(chaves)) == len(chaves)
    for t in topicos:
        assert t["autor_id"] == str(sistema["_id"]) and "autor_email" not in t
        assert len(t["titulo"]) >= 20 and len(t["conteudo_original"]) >= 600
        assert t["conteudo_original"].count("\n\n") >= 1  # 2 a 5 parágrafos
        assert t["conteudo_original"].count("\n\n") <= 4
        assert "·" not in t["titulo"] + t["conteudo_original"]
        assert agora - timedelta(days=60) <= t["data_criacao"].replace(tzinfo=timezone.utc) <= agora
    assert len({t["data_criacao"] for t in topicos}) == len(topicos)

    # Apagado um tópico, só ele volta.
    await db.topicos_forum.delete_one({"seed_chave": chaves[0]})
    assert await seed.seed_forum(db, agora=agora) == 1

    lista = (await api.get("/api/forum/topicos")).json()
    assert len(lista) == seed.TOTAL_SEED and _sem_email(lista)
    assert {t["autor_username"] for t in lista} == {"uniresu"}
    assert {t["autor_nome"] for t in lista} == {"Equipe UniResu"}


async def test_seed_boas_vindas_da_equipe_abre_a_linha_do_tempo(db):
    agora = datetime(2026, 10, 7, 12, tzinfo=timezone.utc)
    # Um tópico de usuário mais antigo que as perguntas do seed.
    await db.topicos_forum.insert_one({"titulo": "Pergunta antiga", "autor_id": "x",
                                       "data_criacao": datetime(2026, 7, 1, 15, tzinfo=timezone.utc)})
    await seed.seed_forum(db, agora=agora)
    sistema = await db.usuarios.find_one({"username": "uniresu"})
    post = await db.topicos_forum.find_one({"seed_chave": seed.POST_BOAS_VINDAS["seed_chave"]})
    assert post["autor_id"] == str(sistema["_id"])
    assert post["data_criacao"].replace(tzinfo=timezone.utc) == datetime(2026, 6, 30, 10, tzinfo=timezone.utc)
    outros = await db.topicos_forum.find({"_id": {"$ne": post["_id"]}}).to_list(100)
    assert all(post["data_criacao"] < t["data_criacao"] for t in outros)
    assert await seed.seed_forum(db, agora=agora) == 0  # idempotente


async def test_seed_completa_conta_de_sistema_antiga(db):
    antigo = await db.usuarios.insert_one({"email": "forum@uniresu.org", "nome": "Equipe UniResu", "papel": "professor"})
    usuario = await seed.garantir_usuario_sistema(db)
    assert usuario["_id"] == antigo.inserted_id
    assert usuario["username"] == "uniresu" and usuario["sistema"] is True
    assert await db.usuarios.count_documents({}) == 1


# ── Usernames ──

@pytest.mark.parametrize("nome, esperado", [
    ("Matheus Gabriel", "matheus-gabriel"),
    ("José Müller da Conceição", "jose-muller-da-conceicao"),
    ("  Ana   Paula!!  ", "ana-paula"),
    ("Dr. João D'Ávila-Neto", "dr-joao-d-avila-neto"),
    ("A", "usuario"),
    ("", "usuario"),
    (None, "usuario"),
    ("Maria Aparecida dos Santos Oliveira Ferreira", "maria-aparecida-dos-santos-oli"),
])
def test_gerar_username_base(nome, esperado):
    assert usernames.gerar_username_base(nome) == esperado
    assert usernames.username_valido(esperado)


def test_escolher_username_livre_com_sufixo_e_limite():
    assert usernames.escolher_username_livre("ana-souza", []) == "ana-souza"
    assert usernames.escolher_username_livre("ana-souza", ["ana-souza"]) == "ana-souza-2"
    assert usernames.escolher_username_livre("ana-souza", ["ana-souza", "ana-souza-2"]) == "ana-souza-3"
    # Reservados contam como ocupados.
    assert usernames.escolher_username_livre("usuario", []) == "usuario-2"
    assert usernames.escolher_username_livre("uniresu", []) == "uniresu-2"
    # Sufixo nunca estoura 30 caracteres.
    longo = "a" * 30
    assert usernames.escolher_username_livre(longo, [longo]) == "a" * 28 + "-2"
    assert usernames.escolher_username_livre(longo, [longo] + ["a" * 28 + f"-{n}" for n in range(2, 10)]) == "a" * 27 + "-10"


async def test_gerar_username_unico_e_disponivel(db):
    await db.usuarios.insert_many([{"nome": "x", "username": "ana-souza"}, {"nome": "x", "username": "ana-souza-2"}])
    assert await usernames.gerar_username_unico(db, "Ana Souza") == "ana-souza-3"
    assert await usernames.gerar_username_unico(db, "Ana Souza Lima") == "ana-souza-lima"
    assert await usernames.username_disponivel(db, "ana-souza") is False
    assert await usernames.username_disponivel(db, "ana-souza-3") is True
    assert await usernames.username_disponivel(db, "usuario") is False  # reservado
    assert await usernames.username_disponivel(db, "Ana Souza") is False  # inválido


def _registro(email, nome="Ana Souza"):
    return UsuarioCreate(email=email, senha="segredo1", nome=nome, papel="aluno",
                         aceite_regras=True, aceite_dados=True)


async def test_registro_gera_username_do_nome_e_nunca_do_email(db):
    primeiro = await registrar_usuario_controller(_registro("ana.xavier@ufrj.br"))
    segundo = await registrar_usuario_controller(_registro("outra.ana@unb.br"))
    assert primeiro["username"] == "ana-souza"
    assert segundo["username"] == "ana-souza-2"
    for u in (primeiro, segundo):
        assert "ana.xavier" not in u["username"] and "outra" not in u["username"]
    assert (await db.usuarios.find_one({"email": "ana.xavier@ufrj.br"}))["username"] == "ana-souza"


async def test_migrar_dados_preenche_usernames_e_roda_seed(db):
    await db.usuarios.insert_many([
        {"email": "a@ufrj.br", "nome": "João Silva", "papel": "aluno"},
        {"email": "b@ufrj.br", "nome": "João Silva", "papel": "aluno"},
        {"email": "c@ufrj.br", "nome": "Ana Souza", "papel": "aluno", "username": None},
        {"email": "ja.tem@ufrj.br", "nome": "Carla", "papel": "aluno", "username": "carla"},
        {"email": "sem.nome@ufrj.br", "papel": "aluno"},
    ])

    await migrar_dados(db)

    docs = {u["email"]: u for u in await db.usuarios.find({}).to_list(100)}
    assert docs["a@ufrj.br"]["username"] == "joao-silva"
    assert docs["b@ufrj.br"]["username"] == "joao-silva-2"
    assert docs["c@ufrj.br"]["username"] == "ana-souza"
    assert docs["ja.tem@ufrj.br"]["username"] == "carla"  # não é tocado
    assert docs["sem.nome@ufrj.br"]["username"].startswith("usuario-")  # nunca "sem.nome"
    assert docs["forum@uniresu.org"]["username"] == "uniresu"  # seed rodou
    todos = [u["username"] for u in docs.values()]
    assert len(set(todos)) == len(todos)
    assert await db.topicos_forum.count_documents({"seed": "forum_v1"}) == seed.TOTAL_SEED

    # Idempotente: segunda rodada não muda nada.
    await migrar_dados(db)
    assert {u["email"]: u["username"] for u in await db.usuarios.find({}).to_list(100)} == {
        e: u["username"] for e, u in docs.items()
    }
    assert await db.topicos_forum.count_documents({"seed": "forum_v1"}) == seed.TOTAL_SEED


async def test_criar_indices_inclui_username_unico_sparse(db):
    await migrar_dados(db)
    await criar_indices(db)
    indice = (await db.usuarios.index_information())["uniq_username"]
    assert indice["key"] == [("username", 1)] and indice["unique"] and indice["sparse"]
