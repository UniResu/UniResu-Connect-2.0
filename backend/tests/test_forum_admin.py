"""Moderação do fórum via job (listar e remover tópico com respostas)."""

from datetime import datetime, timezone

import pytest

from jobs import forum_admin


async def test_listar_e_remover_topico_com_respostas(db):
    lucas = await db.usuarios.insert_one({"email": "lucas@x.br", "username": "lucas", "nome": "Lucas"})
    ana = await db.usuarios.insert_one({"email": "ana@x.br", "username": "ana", "nome": "Ana"})
    t1 = await db.topicos_forum.insert_one({"titulo": "Do Lucas", "autor_id": str(lucas.inserted_id),
                                            "data_criacao": datetime(2026, 10, 1, tzinfo=timezone.utc)})
    t2 = await db.topicos_forum.insert_one({"titulo": "Da Ana", "autor_id": str(ana.inserted_id),
                                            "data_criacao": datetime(2026, 10, 2, tzinfo=timezone.utc)})
    await db.respostas_forum.insert_many([{"topico_id": str(t1.inserted_id)}, {"topico_id": str(t1.inserted_id)},
                                          {"topico_id": str(t2.inserted_id)}])

    linhas = await forum_admin.listar(db)
    assert [(linha["username"], linha["titulo"], linha["respostas"]) for linha in linhas] == [
        ("lucas", "Do Lucas", 2), ("ana", "Da Ana", 1)]

    # Sem confirmar, nada muda.
    previa = await forum_admin.remover(db, str(t1.inserted_id), confirmar=False)
    assert previa["removido"] is False and previa["respostas"] == 2
    assert await db.topicos_forum.count_documents({}) == 2

    feito = await forum_admin.remover(db, str(t1.inserted_id), confirmar=True)
    assert feito["removido"] is True
    assert await db.topicos_forum.count_documents({}) == 1
    assert await db.respostas_forum.count_documents({}) == 1

    with pytest.raises(LookupError):
        await forum_admin.remover(db, str(t1.inserted_id), confirmar=True)
    with pytest.raises(ValueError):
        await forum_admin.remover(db, "nao-e-id", confirmar=True)
