"""Job de sync: log da run, falha com 0 resultados e alerta."""

from jobs.sync_sigaa import executar_sync
from services.sigaa.config import SigaaConfig
from services.sigaa.scraper import ResultadoColeta, SigaaErro


class ClienteNulo:
    total_requisicoes = 7


def item(modulo, titulo, **extra):
    return {"modulo": modulo, "sigaa_id": titulo, "titulo": titulo, "coordenador": "COORD",
            "email": "c@unir.br", "ano": "2026", "situacao": "EM EXECUÇÃO", "detalhe_ok": True, **extra}


def coletores(pesquisa=None, extensao=None, erros_ext=None):
    def fazer(modulo, itens, erros=None):
        def coletar(client, ano):
            if isinstance(itens, Exception):
                raise itens
            return ResultadoColeta(modulo, list(itens), list(erros or []))
        return coletar
    return {"pesquisa": fazer("pesquisa", pesquisa or []), "extensao": fazer("extensao", extensao or [], erros_ext)}


CFG = SigaaConfig(anos=["2026"])


async def test_sucesso_registra_run_e_desativa_ausentes(db):
    await executar_sync(db, CFG, coletores([item("pesquisa", "A"), item("pesquisa", "B")],
                                           [item("extensao", "X")]), ClienteNulo())
    run = await executar_sync(db, CFG, coletores([item("pesquisa", "A")], [item("extensao", "X")]), ClienteNulo())

    assert run["status"] == "sucesso"
    assert run["modulos"]["pesquisa"] == {"coletados": 1, "novos": 0, "atualizados": 1, "desativados": 1,
                                         "erros_detalhe": 0, "status": "sucesso"}
    salvo = await db.sigaa_sync_runs.find_one({"_id": run["_id"]})
    assert salvo["status"] == "sucesso" and salvo["finalizada_em"] and salvo["requisicoes"] == 7
    assert await db.sigaa_sync_runs.count_documents({}) == 2


async def test_zero_resultados_e_falha_nao_desativa_e_alerta(db):
    await executar_sync(db, CFG, coletores([item("pesquisa", "A")], [item("extensao", "X")]), ClienteNulo())
    alertas = []

    async def alertar(run):
        alertas.append(run)

    run = await executar_sync(db, CFG, coletores([], [item("extensao", "X")]), ClienteNulo(), alertar)

    assert run["status"] == "falha"
    assert run["modulos"]["pesquisa"]["status"] == "falha"
    assert run["modulos"]["extensao"]["status"] == "sucesso"
    assert await db.projetos.count_documents({"ativo": False}) == 0
    assert len(alertas) == 1


async def test_busca_que_levanta_excecao_e_falha_sem_desativar(db):
    await executar_sync(db, CFG, coletores([item("pesquisa", "A")], [item("extensao", "X")]), ClienteNulo())
    run = await executar_sync(db, CFG, coletores(SigaaErro("SIGAA fora do ar"), [item("extensao", "X")]),
                              ClienteNulo())
    assert run["status"] == "falha"
    assert await db.projetos.count_documents({"ativo": False}) == 0
    assert any("SIGAA fora do ar" in e["erro"] for e in run["erros"])


async def test_erros_de_detalhe_nao_abortam(db):
    erros = [{"modulo": "extensao", "sigaa_id": "Y", "titulo": "Y", "erro": "timeout"}]
    run = await executar_sync(
        db, CFG,
        coletores([item("pesquisa", "A")],
                  [item("extensao", "X"), item("extensao", "Y", coordenador=None, email=None, detalhe_ok=False)],
                  erros_ext=erros),
        ClienteNulo(),
    )
    assert run["status"] == "sucesso_com_erros"
    assert run["modulos"]["extensao"]["coletados"] == 2
    assert run["modulos"]["extensao"]["erros_detalhe"] == 1
    assert await db.projetos.count_documents({"modulo": "extensao"}) == 2
