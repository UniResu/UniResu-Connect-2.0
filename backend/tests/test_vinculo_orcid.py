"""Conta do ORCID: vinculação a uma conta por senha já existente, perfil
incompleto bloqueado nas ações, limpeza de campos no PATCH."""

import pytest
from bson import ObjectId
from httpx import ASGITransport, AsyncClient

from auth.autenticacao import get_usuario_atual, token_para_usuario
from main import app

ORCID_EMAIL = "0000-0002-1234-5678@orcid.placeholder"


async def _conta_orcid(db, completa=False):
    oid = ObjectId()
    await db.usuarios.insert_one({
        "_id": oid, "email": ORCID_EMAIL, "nome": "Carlos Lima", "username": "carlos-lima",
        "papel": "pesquisador", "perfil_completo": completa, "orcid": {"orcid_id": "0000-0002-1234-5678"},
        "instituicao": "UNIRIO", "interesses": [], "habilidades": [], "ativo": True,
    })
    return oid


@pytest.fixture
async def api_real(db):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        yield client


def _headers(oid, email=ORCID_EMAIL):
    return {"Authorization": f"Bearer {token_para_usuario({'_id': oid, 'email': email})}"}


async def test_orcid_vincula_a_conta_por_senha_ao_confirmar_o_email(api_real, db):
    dona = (await db.usuarios.insert_one({
        "email": "ana.souza@unirio.br", "nome": "Ana Souza", "papel": "professor", "senha_hash": "x",
        "email_verificado": True, "dados_professor": {"linhas_pesquisa": []}})).inserted_id
    prov = await _conta_orcid(db)
    # algo feito pela conta provisória antes da vinculação
    await db.candidaturas.insert_one({"usuario_id": str(prov), "nome_aluno": "Carlos"})
    await db.topicos_forum.insert_one({"titulo": "Pergunta", "autor_id": str(prov), "likes": [], "dislikes": []})
    await db.respostas_forum.insert_one({"topico_id": "x", "autor_id": str(prov), "conteudo": "Resposta"})

    r = await api_real.patch("/api/perfil", json={"email": "Ana.Souza@unirio.br"}, headers=_headers(prov))
    assert r.status_code == 200, r.text
    assert r.json()["email_pendente"] == "ana.souza@unirio.br" and r.json()["email_pendente_vincula"] is True

    token = (await db.usuarios.find_one({"_id": prov}))["token_verificacao_email"]
    r = await api_real.get("/api/auth/verificar-email", params={"token": token})
    assert r.status_code == 200, r.text
    assert r.json()["mesclada"] is True and "vinculado" in r.json()["message"]

    destino = await db.usuarios.find_one({"_id": dona})
    assert destino["orcid"]["orcid_id"] == "0000-0002-1234-5678" and destino["email_verificado"] is True
    assert destino["papel"] == "professor"  # dados da conta existente prevalecem
    provisoria = await db.usuarios.find_one({"_id": prov})
    assert provisoria["ativo"] is False and "orcid" not in provisoria and provisoria["mesclada_em"] == dona
    assert (await db.candidaturas.find_one({"nome_aluno": "Carlos"}))["usuario_id"] == str(dona)
    assert (await db.topicos_forum.find_one({"titulo": "Pergunta"}))["autor_id"] == str(dona)
    assert (await db.respostas_forum.find_one({"conteudo": "Resposta"}))["autor_id"] == str(dona)
    # o token da provisória morre; o login ORCID encontra a conta de destino
    assert (await api_real.get("/api/auth/me", headers=_headers(prov))).status_code == 401
    assert (await db.usuarios.find_one({"orcid.orcid_id": "0000-0002-1234-5678"}))["_id"] == dona


async def test_email_de_outra_conta_orcid_continua_recusado(api_real, db):
    await db.usuarios.insert_one({"email": "bia@unirio.br", "nome": "Bia", "papel": "aluno",
                                  "orcid": {"orcid_id": "0000-0009-9999-9999"}})
    prov = await _conta_orcid(db)
    r = await api_real.patch("/api/perfil", json={"email": "bia@unirio.br"}, headers=_headers(prov))
    assert r.status_code == 400 and "já está cadastrado" in r.text


async def test_registro_recusa_email_pendente_de_outra_conta(api_real, db):
    await db.usuarios.insert_one({"email": ORCID_EMAIL, "nome": "C", "papel": "aluno",
                                  "email_pendente": "carlos.lima@unirio.br"})
    r = await api_real.post("/api/usuarios/registrar", json={
        "nome": "Outro", "email": "carlos.lima@unirio.br", "senha": "segredo1", "papel": "aluno",
        "aceite_regras": True, "aceite_dados": True})
    assert r.status_code == 400 and "já está cadastrado" in r.text


async def test_reenviar_verificacao_responde_igual_para_qualquer_email(api_real, db):
    await db.usuarios.insert_one({"email": "verificada@unir.br", "nome": "V", "papel": "aluno",
                                  "email_verificado": True})
    await _conta_orcid(db)
    for email in ("verificada@unir.br", "ninguem@unir.br", ORCID_EMAIL):
        r = await api_real.post("/api/auth/reenviar-verificacao", json={"email": email})
        assert r.status_code == 200, (email, r.text)


async def test_perfil_incompleto_nao_candidata_nem_publica_nem_cadastra_projeto(api_real, db):
    prov = await _conta_orcid(db, completa=False)
    pid = (await db.projetos.insert_one({"titulo": "P", "nome_professor": "X", "email_professor": "x@unir.br"})).inserted_id
    r = await api_real.post(f"/api/projetos/{pid}/candidatar", headers=_headers(prov), json={
        "nome": "Carlos", "curso_periodo": "Med 3", "email": "c@unirio.br", "carta": "x" * 300})
    assert r.status_code == 403 and "Complete seu perfil" in r.text
    r = await api_real.post("/api/forum/topicos", headers=_headers(prov), json={"titulo": "T", "conteudo": "C"})
    assert r.status_code == 403
    assert (await api_real.get("/api/projetos/meus", headers=_headers(prov))).status_code == 403
    # leitura e o próprio perfil continuam liberados
    assert (await api_real.get("/api/perfil", headers=_headers(prov))).status_code == 200
    assert (await api_real.get("/api/candidaturas/me", headers=_headers(prov))).status_code == 200

    # depois de concluir, passa
    await db.usuarios.update_one({"_id": prov}, {"$set": {"perfil_completo": True}})
    r = await api_real.post("/api/forum/topicos", headers=_headers(prov), json={"titulo": "T", "conteudo": "C"})
    assert r.status_code in (200, 201), r.text


@pytest.fixture
async def api_prof(db):
    oid = ObjectId()
    await db.usuarios.insert_one({
        "_id": oid, "email": "prof@unirio.br", "nome": "Prof", "papel": "professor", "perfil_completo": True,
        "instituicao": "UNIRIO", "departamento": "Dep. X", "interesses": ["a"], "habilidades": [],
        "dados_professor": {"titulo": "Dr.", "cargo": "Adjunto", "linhas_pesquisa": ["x"], "laboratorio": "Lab X"},
    })
    app.dependency_overrides[get_usuario_atual] = lambda: {"id": str(oid), "email": "prof@unirio.br",
                                                             "papel": "professor", "nome": "Prof"}
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        client.oid = oid
        yield client
    app.dependency_overrides.clear()


async def test_patch_com_null_limpa_o_campo_e_campo_ausente_mantem(api_prof, db):
    r = await api_prof.patch("/api/perfil", json={"departamento": None, "dados_professor": {"laboratorio": None}})
    assert r.status_code == 200, r.text
    corpo = r.json()
    assert corpo["departamento"] is None and corpo["dados_professor"]["laboratorio"] is None
    assert corpo["dados_professor"]["titulo"] == "Dr." and corpo["instituicao"] == "UNIRIO"  # não enviados: ficam
    # null em campos que não podem ficar vazios é ignorado
    r = await api_prof.patch("/api/perfil", json={"nome": None, "interesses": None, "bio": "Oi"})
    assert r.status_code == 200 and r.json()["nome"] == "Prof" and r.json()["interesses"] == ["a"]


async def test_trocar_vinculo_preserva_sub_documento_anterior(api_prof, db):
    r = await api_prof.patch("/api/perfil", json={"papel": "tecnico", "dados_tecnico": {"setor": "Biblioteca", "cargo": "Técnico"}})
    assert r.status_code == 200, r.text
    assert r.json()["dados_tecnico"]["cargo"] == "Técnico"
    assert r.json()["dados_professor"]["cargo"] == "Adjunto"  # intacto
    r = await api_prof.patch("/api/perfil", json={"papel": "egresso", "dados_egresso": None})
    assert r.status_code == 200 and r.json()["dados_egresso"] == {"ano_conclusao": None, "atuacao": None}
