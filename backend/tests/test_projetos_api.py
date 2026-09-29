"""Listagem/filtros da aba Projetos Acadêmicos (GET /api/projetos/*)."""

from datetime import datetime, timezone

import pytest


def sigaa(titulo, tipo="pesquisa", unidade="CAMPUS PORTO VELHO", situacao="EM EXECUÇÃO", ativo=True,
          coordenador="ANA PAULA SOUZA", email="ana@unir.br"):
    return {"origem": "sigaa", "chave_sigaa": f"{tipo}|{titulo}", "tipo_sigaa": tipo,
            "tipo": "Pesquisa" if tipo == "pesquisa" else "Extensão", "titulo": titulo,
            "nome_professor": coordenador, "email_professor": email, "unidade": unidade,
            "situacao": situacao, "ano": "2026", "ativo": ativo}


@pytest.fixture
async def base(db):
    await db.projetos.insert_many([
        sigaa("Robótica educacional"),
        sigaa("Horta comunitária", tipo="extensao", unidade="DEPARTAMENTO DE AGRONOMIA", coordenador="BRUNO LIMA"),
        sigaa("Projeto finalizado", situacao="FINALIZADO"),
        sigaa("Sumiu do SIGAA", ativo=False),
        sigaa("Sem contato", email=None),
        {"titulo": "Projeto manual do professor", "descricao": "Cadastrado na plataforma",
         "nome_professor": "Prof. Manual", "email_professor": "manual@unir.br", "tipo_projeto": "voluntario_aberto"},
    ])
    return db


def titulos(resp):
    assert resp.status_code == 200, resp.text
    return sorted(p["titulo"] for p in resp.json())


async def test_padrao_mostra_so_ativos_em_execucao_e_manuais(api, base):
    r = await api.get("/api/projetos/buscar")
    assert titulos(r) == ["Horta comunitária", "Projeto manual do professor", "Robótica educacional", "Sem contato"]


async def test_incluir_inativos(api, base):
    r = await api.get("/api/projetos/buscar", params={"incluir_inativos": "true"})
    assert len(r.json()) == 6


async def test_filtro_por_tipo(api, base):
    r = await api.get("/api/projetos/buscar", params={"tipo_sigaa": "extensao"})
    assert titulos(r) == ["Horta comunitária"]
    r = await api.get("/api/projetos/buscar", params={"tipo_sigaa": "invalido"})
    assert r.status_code == 422


async def test_filtro_por_unidade(api, base):
    r = await api.get("/api/projetos/buscar", params={"unidade": "DEPARTAMENTO DE AGRONOMIA"})
    assert titulos(r) == ["Horta comunitária"]


async def test_busca_por_titulo_e_por_coordenador(api, base):
    assert titulos(await api.get("/api/projetos/buscar", params={"q": "robótica"})) == ["Robótica educacional"]
    assert titulos(await api.get("/api/projetos/buscar", params={"q": "bruno"})) == ["Horta comunitária"]


async def test_busca_escapa_regex(api, base):
    r = await api.get("/api/projetos/buscar", params={"q": ".*("})
    assert titulos(r) == []


async def test_filtros_combinados_sem_resultado(api, base):
    r = await api.get("/api/projetos/buscar", params={"tipo_sigaa": "extensao", "q": "robótica"})
    assert r.json() == []


async def test_resposta_publica_nao_expoe_email(api, base):
    projetos = (await api.get("/api/projetos/buscar")).json()
    for p in projetos:
        assert "email_professor" not in p
        assert "email_contato_manual" not in p
    contato = {p["titulo"]: p["tem_contato"] for p in projetos}
    assert contato["Robótica educacional"] is True
    assert contato["Sem contato"] is False
    assert contato["Projeto manual do professor"] is True


async def test_paginacao_por_cursor(api, base):
    p1 = (await api.get("/api/projetos/buscar", params={"page_size": 2})).json()
    p2 = (await api.get("/api/projetos/buscar", params={"page_size": 2, "last_id": p1[-1]["id"]})).json()
    assert len(p1) == 2 and len(p2) == 2
    assert not {p["id"] for p in p1} & {p["id"] for p in p2}


async def test_unidades_distintas_de_projetos_ativos(api, base):
    r = await api.get("/api/projetos/unidades")
    assert r.json() == ["CAMPUS PORTO VELHO", "DEPARTAMENTO DE AGRONOMIA"]
    r = await api.get("/api/projetos/unidades", params={"tipo_sigaa": "extensao"})
    assert r.json() == ["DEPARTAMENTO DE AGRONOMIA"]


async def test_status_sem_runs(api, db):
    assert (await api.get("/api/projetos/sigaa/status")).json() == {"ultima_atualizacao": None}


async def test_status_ignora_runs_com_falha(api, db):
    await db.sigaa_sync_runs.insert_many([
        {"status": "sucesso", "finalizada_em": datetime(2026, 9, 20, 6, 0, tzinfo=timezone.utc)},
        {"status": "sucesso_com_erros", "finalizada_em": datetime(2026, 9, 27, 6, 0, tzinfo=timezone.utc)},
        {"status": "falha", "finalizada_em": datetime(2026, 9, 28, 6, 0, tzinfo=timezone.utc)},
    ])
    r = await api.get("/api/projetos/sigaa/status")
    assert r.json()["ultima_atualizacao"].startswith("2026-09-27T06:00:00")
