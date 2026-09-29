"""Upsert idempotente, desativação e isolamento dos projetos manuais."""

from services.sigaa import repositorio


def reg(**campos):
    base = {
        "tipo_sigaa": "pesquisa",
        "sigaa_id": "100",
        "codigo": "PVC1-2026",
        "titulo": "Projeto Alfa",
        "coordenador": "ANA PAULA SOUZA",
        "email": "ana@unir.br",
        "unidade": "CAMPUS PORTO VELHO",
        "situacao": "EM EXECUÇÃO",
        "ano": "2026",
        "categoria": "INTERNO",
        "detalhe_ok": True,
    }
    base.update(campos)
    return base


async def test_upsert_e_idempotente(db):
    registros = [reg(), reg(sigaa_id="101", titulo="Projeto Beta", coordenador="BRUNO LIMA")]

    r1 = await repositorio.upsert_projetos(db, registros)
    docs_1 = await db.projetos.find({}, {"_id": 1, "chave_sigaa": 1}).to_list(None)
    r2 = await repositorio.upsert_projetos(db, registros)
    docs_2 = await db.projetos.find({}, {"_id": 1, "chave_sigaa": 1}).to_list(None)

    assert (r1.novos, r1.atualizados) == (2, 0)
    assert (r2.novos, r2.atualizados) == (0, 2)
    assert docs_1 == docs_2  # mesmos _id — candidaturas continuam válidas


async def test_chave_natural_ignora_acentos_caixa_e_espacos(db):
    await repositorio.upsert_projetos(db, [reg(titulo="Projeto  Ação", coordenador="Ana Paula Souza")])
    r = await repositorio.upsert_projetos(db, [reg(titulo="PROJETO ACAO", coordenador="ANA PAULA SOUZA ")])
    assert r.novos == 0
    assert await db.projetos.count_documents({}) == 1


async def test_grava_campos_para_listagem(db):
    await repositorio.upsert_projetos(db, [reg()])
    doc = await db.projetos.find_one({})
    assert doc["origem"] == "sigaa"
    assert doc["tipo"] == "Pesquisa"
    assert doc["nome_professor"] == "ANA PAULA SOUZA"
    assert doc["email_professor"] == "ana@unir.br"
    assert doc["ativo"] is True
    assert doc["primeira_coleta"] == doc["ultima_coleta"]


async def test_nunca_toca_projetos_manuais(db):
    manual = {"titulo": "Projeto Alfa", "nome_professor": "ANA PAULA SOUZA", "ano": "2026",
              "tipo_sigaa": "pesquisa", "ativo": True, "email_professor": "manual@unir.br"}
    manual_id = (await db.projetos.insert_one(dict(manual))).inserted_id

    await repositorio.upsert_projetos(db, [reg()])
    desativados = await repositorio.desativar_ausentes(db, "pesquisa", ["2026"], chaves_vistas=[])

    depois = await db.projetos.find_one({"_id": manual_id})
    assert {k: depois[k] for k in manual} == manual
    assert "origem" not in depois
    assert desativados == 1  # só o doc do SIGAA
    assert await db.projetos.count_documents({}) == 2


async def test_desativa_ausentes_so_no_escopo(db):
    await repositorio.upsert_projetos(db, [
        reg(),
        reg(sigaa_id="2", titulo="Some da fonte"),
        reg(sigaa_id="3", titulo="Outro ano", ano="2025"),
        reg(sigaa_id="4", titulo="Extensão", tipo_sigaa="extensao"),
    ])
    vistos = await repositorio.upsert_projetos(db, [reg()])

    n = await repositorio.desativar_ausentes(db, "pesquisa", ["2026"], vistos.chaves)

    assert n == 1
    inativos = await db.projetos.find({"ativo": False}).to_list(None)
    assert [d["titulo"] for d in inativos] == ["Some da fonte"]
    assert inativos[0]["desativado_em"] is not None


async def test_reaparecer_reativa(db):
    await repositorio.upsert_projetos(db, [reg()])
    await repositorio.desativar_ausentes(db, "pesquisa", ["2026"], [])
    await repositorio.upsert_projetos(db, [reg()])
    assert (await db.projetos.find_one({}))["ativo"] is True


async def test_nao_sobrescreve_contato_manual_do_admin(db):
    await repositorio.upsert_projetos(db, [reg(email=None)])
    await db.projetos.update_one({}, {"$set": {"email_contato_manual": "admin-cadastrou@unir.br"}})

    await repositorio.upsert_projetos(db, [reg(email=None)])
    assert (await db.projetos.find_one({}))["email_contato_manual"] == "admin-cadastrou@unir.br"


async def test_detalhe_falho_preserva_coordenador_ja_conhecido(db):
    await repositorio.upsert_projetos(db, [reg(tipo_sigaa="extensao")])
    original = await db.projetos.find_one({})

    sem_detalhe = reg(tipo_sigaa="extensao", coordenador=None, email=None, detalhe_ok=False)
    r = await repositorio.upsert_projetos(db, [sem_detalhe])

    doc = await db.projetos.find_one({})
    assert r.novos == 0
    assert await db.projetos.count_documents({}) == 1
    assert doc["_id"] == original["_id"]
    assert doc["email_professor"] == "ana@unir.br"
    assert doc["detalhe_ok"] is False
    assert r.chaves == [original["chave_sigaa"]]  # não será desativado


async def test_item_novo_sem_detalhe_e_salvo_sem_contato_e_depois_completado(db):
    sem_detalhe = reg(tipo_sigaa="extensao", coordenador=None, email=None, detalhe_ok=False)
    await repositorio.upsert_projetos(db, [sem_detalhe])
    primeiro = await db.projetos.find_one({})
    assert primeiro["email_professor"] is None

    # Na semana seguinte o detalhe funciona: mesmo doc (mesmo _id), agora completo.
    await repositorio.upsert_projetos(db, [reg(tipo_sigaa="extensao")])
    docs = await db.projetos.find({}).to_list(None)
    assert len(docs) == 1
    assert docs[0]["_id"] == primeiro["_id"]
    assert docs[0]["email_professor"] == "ana@unir.br"
