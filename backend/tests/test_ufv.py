"""Coleta da extensão da UFV (dados abertos, API DataStore do CKAN)."""

import json
from datetime import date

import pytest

from jobs.sync_ufv import executar_sync
from services.ufv import coleta
from services.ufv.coleta import UfvConfig, coordenador_atual, registro_extensao

# Linha real do conjunto "Projetos e programas de extensão" (envolvidos encurtados).
LINHA = {
    "CodigoLancamento": 847, "NumeroRegistro": "PRJ-037/2008", "Tipo": "Projeto",
    "Titulo": "LUDICIDADE NO ENSINO DE MATEMÁTICA", "AreaCNPQ": "Ciências Exatas e da Terra",
    "AreaTematica": "", "AreaTematica2": "",
    "Envolvidos": ("JAQUES SILVEIRA LOPES (Coordenador, 04/03/2010 a 30/12/2010), GABRIELA LUCHEZE "
                   "(Colaborador(a) Voluntário(a), 04/03/2010 a 30/12/2010), ARIANE PIOVEZAN ENTRINGER "
                   "(Coordenador, 01/02/2015 a 14/05/2027), CAMILA DE SOUZA COSTA (Bolsista PIBEX, "
                   "04/03/2010 a 30/12/2010), MARLI DUFFLES DONATO MOREIRA (Coordenador, 15/05/2017 a 31/12/2017)"),
    "DataInicio": "2010-03-04T00:00:00", "DataTermino": "2027-05-14T00:00:00",
    "LinhaExtensao": "Formação Docente", "Objetivo": "Estimular os professores da escola básica...",
    "PalavrasChave": "jogos, raciocínio lógico, minicursos", "Financiado": "Não",
    "URL": "https://www2.dti.ufv.br/raex/scripts/dadosAtividadeConsulta.php?tipo=2&codigoLancamento=847",
}

HOJE = date(2026, 10, 7)


def test_coordenador_vigente_e_o_do_periodo_atual():
    assert coordenador_atual(LINHA["Envolvidos"], HOJE) == "ARIANE PIOVEZAN ENTRINGER"
    # ninguém vigente: o que coordenou por último
    assert coordenador_atual(LINHA["Envolvidos"], date(2030, 1, 1)) == "ARIANE PIOVEZAN ENTRINGER"
    assert coordenador_atual(LINHA["Envolvidos"], date(2017, 6, 1)) == "MARLI DUFFLES DONATO MOREIRA"
    # papel com parênteses "(a)" não confunde o nome
    assert coordenador_atual("FULANA DE TAL (Colaborador(a) Voluntário(a), 01/01/2020 a 01/01/2030)", HOJE) is None
    assert coordenador_atual("MARIA SOUZA (Coordenadora, 01/01/2025 a 31/12/2026)", HOJE) == "MARIA SOUZA"
    assert coordenador_atual(None) is None and coordenador_atual("") is None


def test_registro_de_extensao():
    r = registro_extensao(LINHA, HOJE)
    assert r["modulo"] == "extensao" and r["ufv_id"] == "847" and r["codigo"] == "PRJ-037/2008"
    assert r["titulo"] == "LUDICIDADE NO ENSINO DE MATEMÁTICA"
    assert r["coordenador"] == "ARIANE PIOVEZAN ENTRINGER" and r["email"] is None
    assert r["situacao"] == "EM EXECUÇÃO" and r["ano"] == "2010"
    assert r["periodo_inicio"] == "2010-03-04" and r["periodo_fim"] == "2027-05-14"
    assert r["categoria"] == "Projeto" and r["link_detalhe"].endswith("codigoLancamento=847")
    assert r["extras"] == {"area_cnpq": "Ciências Exatas e da Terra", "linhas_extensao": ["Formação Docente"],
                           "palavras_chave": ["jogos", "raciocínio lógico", "minicursos"],
                           "financiamento": "Sem financiamento"}


def test_sql_pede_so_os_em_execucao_paginado():
    sql = coleta.sql_extensao_em_execucao("abc", 200, 400)
    assert 'FROM "abc"' in sql and '"DataInicio" <= NOW()' in sql and '"DataTermino" >= NOW()' in sql
    assert sql.endswith("LIMIT 200 OFFSET 400")


class _ClienteCkan:
    """Responde a API do CKAN com páginas de linhas."""

    def __init__(self, paginas, sucesso=True):
        self.cfg = UfvConfig(tamanho_pagina=2)
        self.paginas = list(paginas)
        self.sucesso = sucesso
        self.total_requisicoes = 0
        self.consultas = []

    def get(self, url, params=None, **kw):
        self.total_requisicoes += 1
        self.consultas.append(params["sql"])
        if not self.sucesso:
            return json.dumps({"success": False, "error": {"message": "sql inválido"}})
        return json.dumps({"success": True, "result": {"records": self.paginas.pop(0) if self.paginas else []}})


def _linha(i, **extra):
    return {**LINHA, "CodigoLancamento": i, "Titulo": f"Projeto {i}", **extra}


def test_listar_extensao_pagina_ate_acabar():
    cliente = _ClienteCkan([[_linha(1), _linha(2)], [_linha(3)]])
    assert [r["CodigoLancamento"] for r in coleta.listar_extensao(cliente)] == [1, 2, 3]
    assert cliente.consultas[0].endswith("OFFSET 0") and cliente.consultas[1].endswith("OFFSET 2")


async def test_sync_grava_com_origem_ufv_e_desativa_encerrados(db):
    cfg = UfvConfig()
    run = await executar_sync(db, cfg, client=_ClienteCkan([[_linha(1), _linha(2)]]),
                              listar=coleta.listar_extensao)
    assert run["status"] == "sucesso" and run["modulos"]["extensao"]["novos"] == 2
    doc = await db.projetos.find_one({"ufv_id": "1"})
    assert doc["origem"] == "ufv" and doc["instituicao"] == "UFV" and doc["modulo"] == "extensao"
    assert doc["area_cnpq"] == "Ciências Exatas e da Terra" and doc["situacao"] == "EM EXECUÇÃO"
    assert doc["area_conhecimento"] == "Ciências Exatas e da Terra"  # a área CNPq dos dados abertos
    assert doc["nome_professor"] == "ARIANE PIOVEZAN ENTRINGER" and doc["ativo"] is True

    # o projeto 2 terminou: some da consulta e fica inativo; projetos de outras fontes não mudam
    await db.projetos.insert_one({"origem": "unirio", "modulo": "extensao", "titulo": "X", "ativo": True,
                                  "chave_unirio": "x"})
    run = await executar_sync(db, cfg, client=_ClienteCkan([[_linha(1)]]), listar=coleta.listar_extensao)
    assert run["modulos"]["extensao"]["desativados"] == 1
    assert (await db.projetos.find_one({"ufv_id": "2"}))["ativo"] is False
    assert (await db.projetos.find_one({"origem": "unirio"}))["ativo"] is True
    salvo = await db.sigaa_sync_runs.find_one({"_id": run["_id"]})
    assert salvo["fonte"] == "ufv" and salvo["status"] == "sucesso"


async def test_consulta_vazia_ou_com_erro_e_falha_e_nao_desativa(db):
    await executar_sync(db, UfvConfig(), client=_ClienteCkan([[_linha(1)]]), listar=coleta.listar_extensao)
    run = await executar_sync(db, UfvConfig(), client=_ClienteCkan([[]]), listar=coleta.listar_extensao)
    assert run["status"] == "falha" and "0 projetos" in run["erros"][0]["erro"]
    run = await executar_sync(db, UfvConfig(), client=_ClienteCkan([], sucesso=False), listar=coleta.listar_extensao)
    assert run["status"] == "falha" and "consulta falhou" in run["erros"][0]["erro"]
    assert (await db.projetos.find_one({"ufv_id": "1"}))["ativo"] is True


async def test_dry_run_nao_grava(capsys):
    run = await executar_sync(None, UfvConfig(), client=_ClienteCkan([[_linha(1)]]), dry_run=True,
                              listar=coleta.listar_extensao)
    assert run["status"] == "sucesso" and run["_id"] is None
    assert "Projeto 1" in capsys.readouterr().out


@pytest.mark.parametrize("fin, esperado", [("Sim", "Com financiamento"), ("", None)])
def test_financiamento(fin, esperado):
    assert registro_extensao({**LINHA, "Financiado": fin}, HOJE)["extras"].get("financiamento") == esperado
