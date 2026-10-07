"""Upsert idempotente, desativação e isolamento dos projetos manuais."""

from services.sigaa import repositorio


def reg(**campos):
    base = {
        "modulo": "pesquisa",
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
    assert doc["modulo"] == "pesquisa"
    assert doc["tipo_sigaa"] == "pesquisa"  # nome histórico, mantido para índices e leitores antigos
    assert doc["instituicao"] == "UNIR"
    assert doc["nome_professor"] == "ANA PAULA SOUZA"
    assert doc["email_professor"] == "ana@unir.br"
    assert doc["ativo"] is True
    assert doc["primeira_coleta"] == doc["ultima_coleta"]


async def test_grava_area_do_conhecimento_para_cada_fonte(db):
    from services.fontes import UNIRIO

    await repositorio.upsert_projetos(db, [
        reg(titulo="Horta comunitária", unidade="DEPARTAMENTO DE AGRONOMIA"),
        reg(sigaa_id="2", titulo="Robótica educacional", unidade="CAMPUS PORTO VELHO"),
        reg(sigaa_id="3", titulo="Encontro de egressos", unidade="CAMPUS PORTO VELHO"),
    ])
    await repositorio.upsert_projetos(db, [
        {"modulo": "extensao", "unirio_id": "9", "titulo": "Maré de Saúde", "coordenador": "BRUNO LIMA",
         "unidade": "Departamento de Interpretacao Teatral", "ano": "2018", "detalhe_ok": True,
         "extras": {"area_tematica": "Saúde"}},
    ], fonte=UNIRIO)

    areas = {d["titulo"]: d["area_conhecimento"] async for d in db.projetos.find({})}
    assert areas == {
        "Horta comunitária": "Ciências Agrárias",            # pela unidade
        "Robótica educacional": "Engenharias",               # pelo título (o campus não diz a área)
        "Encontro de egressos": "Multidisciplinar",          # sem pista
        "Maré de Saúde": "Linguística, Letras e Artes",      # pela unidade (teatro)
    }

    # uma nova coleta com o detalhe (unidade por extenso) reclassifica o mesmo documento
    await repositorio.upsert_projetos(db, [reg(sigaa_id="3", titulo="Encontro de egressos",
                                               unidade="DEPARTAMENTO DE ENFERMAGEM")])
    assert (await db.projetos.find_one({"sigaa_id": "3"}))["area_conhecimento"] == "Ciências da Saúde"


async def test_garantir_modulo_migra_docs_antigos_do_sigaa(db):
    await db.projetos.insert_many([
        {"origem": "sigaa", "tipo_sigaa": "extensao", "titulo": "Antigo", "chave_sigaa": "x"},
        {"origem": "sigaa", "tipo_sigaa": "pesquisa", "modulo": "pesquisa", "titulo": "Já migrado", "chave_sigaa": "y"},
        {"titulo": "Manual", "tipo_sigaa": "pesquisa"},
    ])
    assert await repositorio.garantir_modulo(db) == 1
    assert (await db.projetos.find_one({"titulo": "Antigo"}))["modulo"] == "extensao"
    assert "modulo" not in await db.projetos.find_one({"titulo": "Manual"})
    assert await repositorio.garantir_modulo(db) == 0  # idempotente


async def test_nunca_toca_projetos_manuais(db):
    manual = {"titulo": "Projeto Alfa", "nome_professor": "ANA PAULA SOUZA", "ano": "2026",
              "modulo": "pesquisa", "ativo": True, "email_professor": "manual@unir.br"}
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
        reg(sigaa_id="4", titulo="Extensão", modulo="extensao"),
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
    await repositorio.upsert_projetos(db, [reg(modulo="extensao")])
    original = await db.projetos.find_one({})

    sem_detalhe = reg(modulo="extensao", coordenador=None, email=None, detalhe_ok=False)
    r = await repositorio.upsert_projetos(db, [sem_detalhe])

    doc = await db.projetos.find_one({})
    assert r.novos == 0
    assert await db.projetos.count_documents({}) == 1
    assert doc["_id"] == original["_id"]
    assert doc["email_professor"] == "ana@unir.br"
    assert doc["detalhe_ok"] is False
    assert r.chaves == [original["chave_sigaa"]]  # não será desativado


async def test_item_novo_sem_detalhe_e_salvo_sem_contato_e_depois_completado(db):
    sem_detalhe = reg(modulo="extensao", coordenador=None, email=None, detalhe_ok=False)
    await repositorio.upsert_projetos(db, [sem_detalhe])
    primeiro = await db.projetos.find_one({})
    assert primeiro["email_professor"] is None

    # Na semana seguinte o detalhe funciona: mesmo doc (mesmo _id), agora completo.
    await repositorio.upsert_projetos(db, [reg(modulo="extensao")])
    docs = await db.projetos.find({}).to_list(None)
    assert len(docs) == 1
    assert docs[0]["_id"] == primeiro["_id"]
    assert docs[0]["email_professor"] == "ana@unir.br"


async def test_script_de_contato_manual(db):
    from jobs.definir_contato import definir_contato

    await repositorio.upsert_projetos(db, [reg(email=None, codigo="PVC9-2026")])
    filtro = {"origem": "sigaa", "codigo": "PVC9-2026"}

    assert await definir_contato(db, filtro, "secretaria@unir.br") == 1
    assert (await db.projetos.find_one(filtro))["email_contato_manual"] == "secretaria@unir.br"
    assert await definir_contato(db, {"origem": "sigaa", "codigo": "NAO-EXISTE"}, "x@unir.br") == 0

    assert await definir_contato(db, filtro, None) == 1
    assert "email_contato_manual" not in await db.projetos.find_one(filtro)


# ── Várias instituições na mesma plataforma (SIGAA) ─────────────────────────

async def test_instituicoes_sigaa_nao_se_misturam(db):
    from services.fontes import fonte_sigaa
    from services.sigaa.repositorio import desativar_ausentes, upsert_projetos

    unir, ufrn = fonte_sigaa("UNIR"), fonte_sigaa("UFRN")
    assert unir.prefixo_chave == "" and ufrn.prefixo_chave == "ufrn|"
    reg = {"modulo": "extensao", "sigaa_id": "77", "titulo": "Horta comunitária", "coordenador": "ANA",
           "ano": "2026", "situacao": "EM EXECUÇÃO"}

    a = await upsert_projetos(db, [reg], fonte=unir)
    b = await upsert_projetos(db, [reg], fonte=ufrn)
    assert a.novos == 1 and b.novos == 1
    docs = await db.projetos.find({"origem": "sigaa"}).to_list(10)
    assert sorted(d["instituicao"] for d in docs) == ["UFRN", "UNIR"]
    assert {d["chave_sigaa"] for d in docs} == {a.chaves[0], "ufrn|" + a.chaves[0]}

    # a UFRN sumiu com o projeto: só o doc da UFRN é desativado
    assert await desativar_ausentes(db, "extensao", ["2026"], [], fonte=ufrn) == 1
    assert (await db.projetos.find_one({"instituicao": "UNIR"}))["ativo"] is True
    assert (await db.projetos.find_one({"instituicao": "UFRN"}))["ativo"] is False

    # id igual em instituições diferentes não confunde a confirmação de presença
    c = await upsert_projetos(db, [{**reg, "so_listagem": True}], fonte=ufrn)
    assert c.atualizados == 1
    assert (await db.projetos.find_one({"instituicao": "UFRN"}))["ativo"] is True


def test_urls_e_links_seguem_o_endereco_da_instituicao():
    from services.sigaa import parser, scraper
    from services.sigaa.config import SigaaConfig

    cfg = SigaaConfig.para("ufrn")
    assert cfg.instituicao == "UFRN" and cfg.base_url == "https://sigaa.ufrn.br"
    urls = scraper.urls_consulta(cfg.base_url)
    assert urls["extensao"].startswith("https://sigaa.ufrn.br/sigaa/public/extensao/")
    assert scraper.URLS["pesquisa"].startswith("https://sigaa.unir.br/")
    assert parser.url_detalhe_extensao("12", "https://sig.ufca.edu.br/") == (
        "https://sig.ufca.edu.br/sigaa/link/public/extensao/visualizacaoAcaoExtensao/12")
    html = open("tests/fixtures/sigaa_extensao_listagem.html", encoding="iso-8859-1").read()
    itens = parser.parse_listagem_extensao(html, "https://sigaa.ufpb.br")
    assert itens and all(i["link_detalhe"].startswith("https://sigaa.ufpb.br/") for i in itens if i["link_detalhe"])


def test_config_por_ambiente_escolhe_a_instituicao(monkeypatch):
    import pytest as _pytest
    from services.sigaa.config import SigaaConfig

    monkeypatch.setenv("SIGAA_INSTITUICAO", "ufpi")
    cfg = SigaaConfig.from_env()
    assert cfg.instituicao == "UFPI" and cfg.base_url == "https://sigaa.ufpi.br"
    monkeypatch.setenv("SIGAA_INSTITUICAO", "XPTO")
    with _pytest.raises(ValueError):
        SigaaConfig.from_env()


async def test_troca_de_coordenacao_mantem_o_mesmo_documento(db):
    from services.fontes import SIGAA
    from services.sigaa.repositorio import upsert_projetos

    reg = {"modulo": "extensao", "sigaa_id": "4191", "titulo": "Busca ativa de tuberculose",
           "coordenador": "MATHEUS", "ano": "2026", "situacao": "EM EXECUÇÃO"}
    a = await upsert_projetos(db, [reg], fonte=SIGAA)
    antes = await db.projetos.find_one({"sigaa_id": "4191"})

    b = await upsert_projetos(db, [{**reg, "coordenador": "JANDRA"}], fonte=SIGAA)
    assert a.novos == 1 and b.novos == 0 and b.atualizados == 1
    docs = await db.projetos.find({"sigaa_id": "4191"}).to_list(10)
    assert len(docs) == 1 and docs[0]["_id"] == antes["_id"]
    assert docs[0]["nome_professor"] == "JANDRA" and docs[0]["chave_sigaa"] == b.chaves[0]
