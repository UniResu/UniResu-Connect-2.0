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
    # o valor antigo "mestrado" vira o nível atual em andamento
    assert corpo["dados_aluno"] == {"nivel": "mestrado_incompleto", "semestre": 3, "orientador": None,
                                    "linha_pesquisa": None}
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


async def test_perfil_completo_nao_e_aceito_sem_vinculo_aceites_e_email(api_orcid, db):
    # só a flag: nada muda
    r = await api_orcid.patch("/api/perfil", json={"perfil_completo": True})
    assert r.status_code == 400 and "aceitar" in r.text and "e-mail" in r.text
    assert (await db.usuarios.find_one({"_id": api_orcid.oid}))["perfil_completo"] is False
    # aceites sem e-mail: ainda falta
    r = await api_orcid.patch("/api/perfil", json={"perfil_completo": True, "papel": "aluno",
                                                   "aceite_regras": True, "aceite_dados": True})
    assert r.status_code == 400 and "e-mail institucional" in r.text
    # com tudo (e-mail pendente conta): conclui
    r = await api_orcid.patch("/api/perfil", json={"perfil_completo": True, "papel": "aluno", "email": "c@unirio.br",
                                                   "aceite_regras": True, "aceite_dados": True})
    assert r.status_code == 200, r.text
    assert r.json()["perfil_completo"] is True


async def test_unicidade_de_email_ignora_maiusculas(api, api_orcid, db):
    await db.usuarios.insert_one({"email": "Carlos.Lima@unirio.br", "nome": "Outro", "papel": "aluno",
                                  "email_verificado": True, "orcid": {"orcid_id": "0000-0001-1111-1111"}})
    r = await api_orcid.patch("/api/perfil", json={"email": "carlos.lima@unirio.br"})
    assert r.status_code == 400 and "já está cadastrado" in r.text
    r = await api.post("/api/usuarios/registrar", json=payload(email="CARLOS.LIMA@unirio.br"))
    assert r.status_code == 400 and "já está cadastrado" in r.text
    # registro grava em minúsculas e o login aceita qualquer caixa
    r = await api.post("/api/usuarios/registrar", json=payload(email="Nova.Conta@unirio.br"))
    assert r.status_code == 201 and r.json()["email"] == "nova.conta@unirio.br"
    await db.usuarios.update_one({"email": "nova.conta@unirio.br"}, {"$set": {"email_verificado": True}})
    r = await api.post("/api/auth/login", json={"email": "NOVA.conta@unirio.br", "senha": "segredo1"})
    assert r.status_code == 200, r.text


async def test_usuarios_lista_contas_legadas_sem_papel(api, db):
    await db.usuarios.insert_one({"email": "legado@unir.br", "nome": "Legado", "vinculo": "professor"})
    r = await api.get("/api/usuarios")
    assert r.status_code == 200, r.text
    assert [u["papel"] for u in r.json()] == ["professor"]


async def test_completar_perfil_escolhe_vinculo_email_e_aceites(api_orcid, db):
    r = await api_orcid.patch("/api/perfil", json={
        "papel": "professor", "instituicao": "UNIRIO", "departamento": "Escola de Medicina e Cirurgia",
        "email": "Carlos.Lima@unirio.br", "aceite_regras": True, "aceite_dados": True, "perfil_completo": True,
        "dados_professor": {"titulo": "Dr.", "cargo": "Professor Associado", "linhas_pesquisa": ["Saúde coletiva"]},
    })
    assert r.status_code == 200, r.text
    corpo = r.json()
    assert corpo["papel"] == "professor" and corpo["perfil_completo"] is True
    assert corpo["dados_professor"]["linhas_pesquisa"] == ["Saúde coletiva"]
    # o e-mail informado fica pendente até a confirmação pelo link; a conta
    # continua com o provisório (e logada pelo ORCID)
    assert corpo["email"] == "0000-0002-1234-5678@orcid.placeholder"
    assert corpo["email_pendente"] == "carlos.lima@unirio.br"
    doc = await db.usuarios.find_one({"_id": api_orcid.oid})
    assert doc["token_verificacao_email"] and doc["token_verificacao_expira"]
    assert "email_verificado" not in doc  # nada bloqueia o acesso enquanto isso
    assert doc["aceite_regras"] is True and doc["aceite_dados"] is True and doc["aceites_em"] is not None

    # confirmação pelo link: o e-mail institucional passa a ser o da conta
    r = await api_orcid.get("/api/auth/verificar-email", params={"token": doc["token_verificacao_email"]})
    assert r.status_code == 200, r.text
    doc = await db.usuarios.find_one({"_id": api_orcid.oid})
    assert doc["email"] == "carlos.lima@unirio.br" and doc["email_verificado"] is True
    assert "email_pendente" not in doc and "token_verificacao_email" not in doc


async def test_confirmacao_vincula_se_o_email_virou_conta_por_senha_nesse_meio_tempo(api_orcid, db):
    await api_orcid.patch("/api/perfil", json={"email": "carlos.lima@unirio.br"})
    token = (await db.usuarios.find_one({"_id": api_orcid.oid}))["token_verificacao_email"]
    outra = (await db.usuarios.insert_one({"email": "carlos.lima@unirio.br", "nome": "Outro", "papel": "aluno",
                                           "senha_hash": "x"})).inserted_id
    # quem clica no link é dono da caixa postal: o ORCID vai para a conta por senha
    r = await api_orcid.get("/api/auth/verificar-email", params={"token": token})
    assert r.status_code == 200 and r.json()["mesclada"] is True
    doc = await db.usuarios.find_one({"_id": api_orcid.oid})
    assert doc["email"] == "0000-0002-1234-5678@orcid.placeholder" and doc["ativo"] is False
    assert (await db.usuarios.find_one({"_id": outra}))["orcid"]["orcid_id"] == "0000-0002-1234-5678"
    # já se for outra conta do ORCID, é conflito
    await api_orcid.patch("/api/perfil", json={"email": "c2@unirio.br"})


async def test_reenviar_verificacao_aceita_o_email_pendente(api_orcid, db):
    await api_orcid.patch("/api/perfil", json={"email": "carlos.lima@unirio.br"})
    antes = (await db.usuarios.find_one({"_id": api_orcid.oid}))["token_verificacao_email"]
    r = await api_orcid.post("/api/auth/reenviar-verificacao", json={"email": "carlos.lima@unirio.br"})
    assert r.status_code == 200, r.text
    depois = (await db.usuarios.find_one({"_id": api_orcid.oid}))["token_verificacao_email"]
    assert depois and depois != antes


# ── sessão (token) sobrevive à troca de e-mail ─────────────────────────────

@pytest.fixture
async def api_sem_override(db):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        yield client


async def test_token_com_uid_continua_valido_depois_da_troca_de_email(api_sem_override, db):
    from auth.autenticacao import token_para_usuario
    oid = ObjectId()
    await db.usuarios.insert_one({"_id": oid, "email": "0000-0002-9999-0000@orcid.placeholder", "nome": "Dani",
                                  "papel": "pesquisador", "orcid": {"orcid_id": "0000-0002-9999-0000"}})
    token = token_para_usuario({"_id": oid, "email": "0000-0002-9999-0000@orcid.placeholder", "papel": "pesquisador"})
    headers = {"Authorization": f"Bearer {token}"}

    assert (await api_sem_override.get("/api/auth/me", headers=headers)).status_code == 200
    # a conta troca de e-mail (como na confirmação do e-mail institucional)
    await db.usuarios.update_one({"_id": oid}, {"$set": {"email": "dani@unirio.br", "email_verificado": True}})
    r = await api_sem_override.get("/api/auth/me", headers=headers)
    assert r.status_code == 200, r.text
    assert r.json()["email"] == "dani@unirio.br"


async def test_token_antigo_so_com_email_continua_aceito(api_sem_override, db):
    from auth.autenticacao import create_access_token
    await db.usuarios.insert_one({"email": "antiga@unir.br", "nome": "Conta antiga", "papel": "aluno",
                                  "email_verificado": True})
    token = create_access_token({"sub": "antiga@unir.br", "papel": "aluno"})
    r = await api_sem_override.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200, r.text
    # uid inválido não derruba a requisição: cai no e-mail
    token = create_access_token({"sub": "antiga@unir.br", "uid": "nao-e-objectid"})
    assert (await api_sem_override.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})).status_code == 200


async def test_conta_por_senha_sem_email_verificado_segue_bloqueada(api_sem_override, db):
    from auth.autenticacao import token_para_usuario
    oid = ObjectId()
    await db.usuarios.insert_one({"_id": oid, "email": "nova@unir.br", "nome": "Nova", "papel": "aluno",
                                  "email_verificado": False})
    token = token_para_usuario({"_id": oid, "email": "nova@unir.br"})
    assert (await api_sem_override.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})).status_code == 403


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
    # enquanto não confirmou, pode corrigir o e-mail informado
    r = await api_orcid.patch("/api/perfil", json={"email": "c.lima@unirio.br"})
    assert r.status_code == 200 and r.json()["email_pendente"] == "c.lima@unirio.br"
    # depois de confirmado, o e-mail da conta não muda mais por aqui
    token = (await db.usuarios.find_one({"_id": api_orcid.oid}))["token_verificacao_email"]
    assert (await api_orcid.get("/api/auth/verificar-email", params={"token": token})).status_code == 200
    r = await api_orcid.patch("/api/perfil", json={"email": "outro@unirio.br"})
    assert r.status_code == 400 and "não pode ser alterado" in r.text


async def test_email_de_conta_por_senha_vira_vinculacao_e_de_conta_orcid_e_recusado(api_orcid, db):
    # conta por senha dona do e-mail: aceito como pendente de vinculação
    await db.usuarios.insert_one({"email": "carlos.lima@unirio.br", "nome": "Outro", "papel": "aluno",
                                  "senha_hash": "x"})
    r = await api_orcid.patch("/api/perfil", json={"email": "carlos.lima@unirio.br"})
    assert r.status_code == 200 and r.json()["email_pendente_vincula"] is True
    # pendente em outra conta: conflito
    await db.usuarios.insert_one({"email": "x@orcid.placeholder", "email_pendente": "c2@unirio.br", "nome": "Y",
                                  "papel": "aluno"})
    r = await api_orcid.patch("/api/perfil", json={"email": "c2@unirio.br"})
    assert r.status_code == 400 and "já está cadastrado" in r.text
    # e-mail de outra conta que também entra pelo ORCID: conflito
    await db.usuarios.insert_one({"email": "c3@unirio.br", "nome": "Z", "papel": "aluno",
                                  "orcid": {"orcid_id": "0000-0001-1111-1111"}})
    r = await api_orcid.patch("/api/perfil", json={"email": "c3@unirio.br"})
    assert r.status_code == 400 and "já está cadastrado" in r.text


async def test_perfil_publico_expoe_username_e_vinculo_sem_email(api_orcid, db):
    await api_orcid.patch("/api/perfil", json={"papel": "tecnico", "dados_tecnico": {"setor": "Biblioteca"}})
    r = await api_orcid.get(f"/api/perfil/{api_orcid.oid}")
    assert r.status_code == 200, r.text
    corpo = r.json()
    assert corpo["username"] == "carlos-lima" and corpo["papel"] == "tecnico"
    assert corpo["dados_tecnico"]["setor"] == "Biblioteca"
    assert "email" not in corpo



def test_niveis_academicos_novos_e_antigos():
    from models.usuario_model import DadosAluno

    assert DadosAluno(nivel="graduacao").nivel.value == "graduacao_incompleta"
    assert DadosAluno(nivel="graduacao_incompleta", semestre=7).semestre == 7
    assert DadosAluno(nivel="graduacao_completa", semestre=7).semestre is None
    assert DadosAluno(nivel="doutorado_incompleto").semestre == 1
    assert DadosAluno(nivel="pos_doutorado").semestre is None


async def test_migracao_dos_niveis_academicos(db):
    from database.indexes import migrar_niveis_academicos

    await db.usuarios.insert_many([
        {"email": "a@unir.br", "dados_aluno": {"nivel": "graduacao", "semestre": 3}},
        {"email": "b@unir.br", "dados_aluno": {"nivel": "doutorado", "semestre": 2}},
        {"email": "c@unir.br", "dados_aluno": {"nivel": "mestrado_completo", "semestre": None}},
    ])
    assert await migrar_niveis_academicos(db) == 2
    assert (await db.usuarios.find_one({"email": "a@unir.br"}))["dados_aluno"]["nivel"] == "graduacao_incompleta"
    assert (await db.usuarios.find_one({"email": "b@unir.br"}))["dados_aluno"]["nivel"] == "doutorado_incompleto"
    assert await migrar_niveis_academicos(db) == 0
