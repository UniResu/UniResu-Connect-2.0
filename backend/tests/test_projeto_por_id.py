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
