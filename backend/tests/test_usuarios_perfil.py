"""Registro por vínculo institucional e conclusão do perfil (PATCH /api/perfil)."""

import pytest
from bson import ObjectId
from httpx import ASGITransport, AsyncClient

from auth.autenticacao import get_usuario_atual
from main import app


def payload(**extra):
    base = {
        "nome": "Ana Beatriz Souza", "email": "ana.souza@unirio.br", "senha": "segredo1",
        "papel": "aluno", "aceite_regras": True, "aceite_dados": True,
    }
    base.update(extra)
    return base


async def test_registro_discente_grava_aceites_e_dados_do_vinculo(api, db):
    r = await api.post("/api/usuarios/registrar", json=payload(
        curso="Enfermagem", dados_aluno={"nivel": "mestrado", "semestre": 3}))
    assert r.status_code == 201, r.text
    corpo = r.json()
    assert corpo["papel"] == "aluno" and corpo["perfil_completo"] is True
    assert corpo["dados_aluno"] == {"nivel": "mestrado", "semestre": 3, "orientador": None, "linha_pesquisa": None}
    assert corpo["username"] == "ana-beatriz-souza"
    assert "senha_hash" not in corpo
    doc = await db.usuarios.find_one({"email": "ana.souza@unirio.br"})
    assert doc["aceite_regras"] is True and doc["aceite_dados"] is True and doc["aceites_em"] is not None
    assert doc["email_verificado"] is False


@pytest.mark.parametrize("papel, campo, dados", [
    ("professor", "dados_professor", {"titulo": "Dra.", "cargo": "Professora Adjunta", "linhas_pesquisa": []}),
    ("pesquisador", "dados_pesquisador", {"titulo": "Dr.", "vinculo": "Pós-doc", "linhas_pesquisa": []}),
    ("tecnico", "dados_tecnico", {"setor": "Laboratório de Microbiologia", "cargo": "Técnica de laboratório"}),
    ("egresso", "dados_egresso", {"ano_conclusao": 2022, "atuacao": "Hospital Universitário"}),
])
async def test_registro_aceita_todos_os_vinculos(api, db, papel, campo, dados):
    r = await api.post("/api/usuarios/registrar", json=payload(
        papel=papel, departamento="Departamento de Enfermagem", **{campo: dados}))
    assert r.status_code == 201, r.text
    corpo = r.json()
    assert corpo["papel"] == papel and corpo["departamento"] == "Departamento de Enfermagem"
    for chave, valor in dados.items():
        assert corpo[campo][chave] == valor
    # só o sub-documento do vínculo escolhido é criado
    doc = await db.usuarios.find_one({"email": "ana.souza@unirio.br"})
    outros = {"dados_aluno", "dados_professor", "dados_pesquisador", "dados_tecnico", "dados_egresso"} - {campo}
    assert not any(doc.get(o) for o in outros)


async def test_registro_sem_dados_do_vinculo_usa_o_minimo_do_tipo(api, db):
    r = await api.post("/api/usuarios/registrar", json=payload(papel="professor"))
    assert r.status_code == 201, r.text
    assert r.json()["dados_professor"]["linhas_pesquisa"] == []
    r = await api.post("/api/usuarios/registrar", json=payload(papel="tecnico", email="t@unir.br"))
    assert r.status_code == 201, r.text
    assert (await db.usuarios.find_one({"email": "t@unir.br"}))["dados_tecnico"] == {}


async def test_registro_exige_os_dois_aceites(api):
    r = await api.post("/api/usuarios/registrar", json=payload(aceite_dados=False))
    assert r.status_code == 422
    assert "aceitar" in r.text
    r = await api.post("/api/usuarios/registrar", json={k: v for k, v in payload().items() if k != "aceite_regras"})
    assert r.status_code == 422


async def test_registro_rejeita_vinculo_desconhecido_e_email_nao_institucional(api):
    assert (await api.post("/api/usuarios/registrar", json=payload(papel="visitante"))).status_code == 422
    r = await api.post("/api/usuarios/registrar", json=payload(email="ana@gmail.com"))
    assert r.status_code == 422
    assert "institucionais" in r.text


# ── PATCH /api/perfil ───────────────────────────────────────────────────────

@pytest.fixture
async def api_orcid(db):
    """Cliente logado como uma conta recém-criada pelo ORCID (perfil incompleto)."""
    oid = ObjectId()
    await db.usuarios.insert_one({
        "_id": oid, "email": "0000-0002-1234-5678@orcid.placeholder", "nome": "Carlos Lima",
        "username": "carlos-lima", "papel": "pesquisador", "perfil_completo": False,
        "orcid": {"orcid_id": "0000-0002-1234-5678"}, "interesses": [], "habilidades": [],
    })
    app.dependency_overrides[get_usuario_atual] = lambda: {
        "id": str(oid), "email": "0000-0002-1234-5678@orcid.placeholder", "papel": "pesquisador", "nome": "Carlos Lima"}
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        client.oid = oid
        yield client
    app.dependency_overrides.clear()


async def test_conta_orcid_nasce_incompleta_na_resposta(api_orcid):
    r = await api_orcid.get("/api/perfil")
    assert r.status_code == 200, r.text
    assert r.json()["perfil_completo"] is False


async def test_completar_perfil_escolhe_vinculo_email_e_aceites(api_orcid, db):
    r = await api_orcid.patch("/api/perfil", json={
        "papel": "professor", "instituicao": "UNIRIO", "departamento": "Escola de Medicina e Cirurgia",
        "email": "carlos.lima@unirio.br", "aceite_regras": True, "aceite_dados": True, "perfil_completo": True,
        "dados_professor": {"titulo": "Dr.", "cargo": "Professor Associado", "linhas_pesquisa": ["Saúde coletiva"]},
    })
    assert r.status_code == 200, r.text
    corpo = r.json()
    assert corpo["papel"] == "professor" and corpo["perfil_completo"] is True
    assert corpo["email"] == "carlos.lima@unirio.br"
    assert corpo["dados_professor"]["linhas_pesquisa"] == ["Saúde coletiva"]
    doc = await db.usuarios.find_one({"_id": api_orcid.oid})
    # o e-mail informado ainda precisa ser confirmado
    assert doc["email_verificado"] is False
    assert doc["aceite_regras"] is True and doc["aceite_dados"] is True and doc["aceites_em"] is not None


async def test_trocar_vinculo_cria_sub_documento_do_novo_tipo(api_orcid, db):
    r = await api_orcid.patch("/api/perfil", json={"papel": "egresso"})
    assert r.status_code == 200, r.text
    assert r.json()["dados_egresso"] == {"ano_conclusao": None, "atuacao": None}
    r = await api_orcid.patch("/api/perfil", json={"papel": "tecnico", "dados_tecnico": {"setor": "Biblioteca"}})
    assert r.status_code == 200, r.text
    assert r.json()["dados_tecnico"]["setor"] == "Biblioteca"


async def test_email_so_muda_enquanto_for_o_provisorio(api_orcid, db):
    r = await api_orcid.patch("/api/perfil", json={"email": "carlos@gmail.com"})
    assert r.status_code == 400 and "institucionais" in r.text
    assert (await api_orcid.patch("/api/perfil", json={"email": "carlos.lima@unirio.br"})).status_code == 200
    r = await api_orcid.patch("/api/perfil", json={"email": "outro@unirio.br"})
    assert r.status_code == 400 and "não pode ser alterado" in r.text


async def test_email_informado_nao_pode_pertencer_a_outra_conta(api_orcid, db):
    await db.usuarios.insert_one({"email": "carlos.lima@unirio.br", "nome": "Outro", "papel": "aluno"})
    r = await api_orcid.patch("/api/perfil", json={"email": "carlos.lima@unirio.br"})
    assert r.status_code == 400 and "já está cadastrado" in r.text


async def test_perfil_publico_expoe_username_e_vinculo_sem_email(api_orcid, db):
    await api_orcid.patch("/api/perfil", json={"papel": "tecnico", "dados_tecnico": {"setor": "Biblioteca"}})
    r = await api_orcid.get(f"/api/perfil/{api_orcid.oid}")
    assert r.status_code == 200, r.text
    corpo = r.json()
    assert corpo["username"] == "carlos-lima" and corpo["papel"] == "tecnico"
    assert corpo["dados_tecnico"]["setor"] == "Biblioteca"
    assert "email" not in corpo
