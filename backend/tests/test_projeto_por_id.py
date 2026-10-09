"""GET /api/projetos/{id}: um projeto visível no formato da busca pública."""

from bson import ObjectId

from tests.test_projetos_api import sigaa


async def test_projeto_visivel_por_id_sem_contatos(api, db):
    inserido = await db.projetos.insert_one(sigaa("Robótica educacional"))
    r = await api.get(f"/api/projetos/{inserido.inserted_id}")
    assert r.status_code == 200, r.text
    corpo = r.json()
    assert corpo["id"] == str(inserido.inserted_id)
    assert corpo["titulo"] == "Robótica educacional"
    assert corpo["tem_contato"] is True
    assert "email_professor" not in corpo and "email_contato_manual" not in corpo


async def test_projeto_oculto_invalido_ou_inexistente_da_404(api, db):
    finalizado = await db.projetos.insert_one(sigaa("Projeto finalizado", situacao="FINALIZADO"))
    inativo = await db.projetos.insert_one(sigaa("Sumiu do SIGAA", ativo=False))
    for alvo in (finalizado.inserted_id, inativo.inserted_id, ObjectId(), "nao-e-id"):
        r = await api.get(f"/api/projetos/{alvo}")
        assert r.status_code == 404, (alvo, r.text)


async def test_indice_lista_so_os_visiveis_em_paginas(api, db):
    visiveis = [str((await db.projetos.insert_one(sigaa(f"Projeto {i}"))).inserted_id) for i in range(3)]
    await db.projetos.insert_one(sigaa("Projeto finalizado", situacao="FINALIZADO"))
    await db.projetos.insert_one(sigaa("Sumiu do SIGAA", ativo=False))

    r = await api.get("/api/projetos/indice?limite=2")
    assert r.status_code == 200, r.text
    corpo = r.json()
    assert corpo["total"] == 3
    assert [item["id"] for item in corpo["itens"]] == sorted(visiveis)[:2]
    assert all(item["atualizado_em"] for item in corpo["itens"])

    resto = (await api.get("/api/projetos/indice?pular=2&limite=2")).json()
    assert [item["id"] for item in resto["itens"]] == sorted(visiveis)[2:]
    # A rota não é confundida com /projetos/{id}.
    assert (await api.get("/api/projetos/indice?limite=0")).status_code == 422
