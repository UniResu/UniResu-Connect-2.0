"""Remoção dos projetos de teste (manuais) sem tocar nos coletados."""

from datetime import datetime, timedelta, timezone

from bson import ObjectId

from jobs.remover_projetos_teste import data_corte, listar_projetos_teste, remover_projetos_teste

COLETA = datetime(2026, 9, 29, 9, 0, tzinfo=timezone.utc)


def _oid_em(quando: datetime) -> ObjectId:
    return ObjectId.from_datetime(quando)


async def _base(db):
    antes = COLETA - timedelta(days=10)
    depois = COLETA + timedelta(days=3)
    await db.projetos.insert_many([
        # testes antigos: um com data_publicacao, outro só com o timestamp do _id
        {"titulo": "Teste (UERJ)", "nome_professor": "UniResu", "data_publicacao": antes.isoformat()},
        {"_id": _oid_em(antes), "titulo": "Sepse", "nome_professor": "Luiz"},
        # cadastro manual legítimo, depois da coleta
        {"titulo": "Projeto novo do professor", "nome_professor": "Prof.", "data_publicacao": depois.isoformat()},
        # coletados: nunca são alvo
        {"origem": "sigaa", "chave_sigaa": "pesquisa|x", "titulo": "SIGAA", "primeira_coleta": COLETA},
        {"origem": "unirio", "chave_unirio": "extensao|1", "titulo": "UNIRIO", "primeira_coleta": COLETA},
    ])
    teste = await db.projetos.find_one({"titulo": "Teste (UERJ)"})
    await db.candidaturas.insert_many([
        {"projeto_id": str(teste["_id"]), "nome_aluno": "A"},
        {"projeto_id": "outro", "nome_aluno": "B"},
    ])


async def test_corte_padrao_e_a_primeira_coleta_do_sigaa(db):
    await _base(db)
    assert await data_corte(db, None) == COLETA
    assert await data_corte(db, "2026-01-02") == datetime(2026, 1, 2, tzinfo=timezone.utc)


async def test_lista_so_manuais_anteriores_ao_corte(db):
    await _base(db)
    alvos = await listar_projetos_teste(db, COLETA)
    assert sorted(p["titulo"] for p in alvos) == ["Sepse", "Teste (UERJ)"]
    # --todos (sem corte): inclui o manual novo, mas nunca os coletados
    todos = await listar_projetos_teste(db, None)
    assert sorted(p["titulo"] for p in todos) == ["Projeto novo do professor", "Sepse", "Teste (UERJ)"]


async def test_dry_run_nao_apaga_e_confirmar_apaga_com_candidaturas(db):
    await _base(db)
    resumo = await remover_projetos_teste(db, COLETA, confirmar=False)
    assert resumo["projetos"] == 2 and resumo["candidaturas"] == 1 and resumo["removido"] is False
    assert await db.projetos.count_documents({}) == 5

    resumo = await remover_projetos_teste(db, COLETA, confirmar=True)
    assert resumo["removido"] is True
    restantes = sorted(p["titulo"] for p in await db.projetos.find().to_list(None))
    assert restantes == ["Projeto novo do professor", "SIGAA", "UNIRIO"]
    assert [c["nome_aluno"] for c in await db.candidaturas.find().to_list(None)] == ["B"]


async def test_manter_candidaturas(db):
    await _base(db)
    await remover_projetos_teste(db, None, confirmar=True, manter_candidaturas=True)
    assert await db.candidaturas.count_documents({}) == 2
    assert await db.projetos.count_documents({"origem": {"$exists": False}}) == 0
