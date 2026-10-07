"""Coleta da extensão da UFV (dados abertos, API DataStore do CKAN)."""

import json
from datetime import date

import pytest

from jobs.sync_ufv import executar_sync
from services.ufv import coleta
from services.ufv.coleta import UfvConfig, coordenador_atual, registro_extensao, registro_pesquisa

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
SO_EXTENSAO = {"extensao": (coleta.listar_extensao, registro_extensao)}


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
                              coletores=SO_EXTENSAO)
    assert run["status"] == "sucesso" and run["modulos"]["extensao"]["novos"] == 2
    doc = await db.projetos.find_one({"ufv_id": "1"})
    assert doc["origem"] == "ufv" and doc["instituicao"] == "UFV" and doc["modulo"] == "extensao"
    assert doc["area_cnpq"] == "Ciências Exatas e da Terra" and doc["situacao"] == "EM EXECUÇÃO"
    assert doc["area_conhecimento"] == "Ciências Exatas e da Terra"  # a área CNPq dos dados abertos
    assert doc["nome_professor"] == "ARIANE PIOVEZAN ENTRINGER" and doc["ativo"] is True

    # o projeto 2 terminou: some da consulta e fica inativo; projetos de outras fontes não mudam
    await db.projetos.insert_one({"origem": "unirio", "modulo": "extensao", "titulo": "X", "ativo": True,
                                  "chave_unirio": "x"})
    run = await executar_sync(db, cfg, client=_ClienteCkan([[_linha(1)]]), coletores=SO_EXTENSAO)
    assert run["modulos"]["extensao"]["desativados"] == 1
    assert (await db.projetos.find_one({"ufv_id": "2"}))["ativo"] is False
    assert (await db.projetos.find_one({"origem": "unirio"}))["ativo"] is True
    salvo = await db.sigaa_sync_runs.find_one({"_id": run["_id"]})
    assert salvo["fonte"] == "ufv" and salvo["status"] == "sucesso"


async def test_consulta_vazia_ou_com_erro_e_falha_e_nao_desativa(db):
    await executar_sync(db, UfvConfig(), client=_ClienteCkan([[_linha(1)]]), coletores=SO_EXTENSAO)
    run = await executar_sync(db, UfvConfig(), client=_ClienteCkan([[]]), coletores=SO_EXTENSAO)
    assert run["status"] == "falha" and "0 projetos" in run["erros"][0]["erro"]
    run = await executar_sync(db, UfvConfig(), client=_ClienteCkan([], sucesso=False), coletores=SO_EXTENSAO)
    assert run["status"] == "falha" and "consulta falhou" in run["erros"][0]["erro"]
    assert (await db.projetos.find_one({"ufv_id": "1"}))["ativo"] is True


async def test_dry_run_nao_grava(capsys):
    run = await executar_sync(None, UfvConfig(), client=_ClienteCkan([[_linha(1)]]), dry_run=True,
                              coletores=SO_EXTENSAO)
    assert run["status"] == "sucesso" and run["_id"] is None
    assert "Projeto 1" in capsys.readouterr().out


@pytest.mark.parametrize("fin, esperado", [("Sim", "Com financiamento"), ("", None)])
def test_financiamento(fin, esperado):
    assert registro_extensao({**LINHA, "Financiado": fin}, HOJE)["extras"].get("financiamento") == esperado


# ── Pesquisa (CSV completo) ──────────────────────────────────────────────────

CABECALHO = ("codigo_projeto;numero_registro;titulo;palavra_chave;ano;data_inicio;data_fim;situacao;natureza;"
             "modalidade_projeto;modalidade_treinamento;grupo_pesquisa;linha_pesquisa;area_conhecimento_cnpq;"
             "sigla_depto;nome_linha_pesquisa;local_execucao;num_convenio;tipo_financiamento;valor_financiamento;"
             "outra_instituicao;nome_pessoa;tipo_participacao_projeto;resumo_dos_objetivos")


def _csv(*linhas):
    return ("﻿" + CABECALHO + "\n" + "\n".join(linhas) + "\n").encode("utf-8")


def _linha_pesquisa(codigo, pessoa, funcao, situacao="Registrado", ano="2025.0", inicio="2025-03-01", fim="",
                    registro="00000504460"):
    return (f'{codigo};{registro};"Projeto {codigo}";"solo; água";{ano};{inicio};{fim};{situacao};Interno;'
            f'Projeto Autônomo;Iniciação Científica;Grupo X;Linha Y;Ciência do Solo;DPS;Linha Y nome;Lab;;'
            f'Financiamento;36000.0;;{pessoa};{funcao};Objetivo do projeto {codigo}')


CSV_PESQUISA = _csv(
    _linha_pesquisa(10, "ANA LIMA", "Membro"),
    _linha_pesquisa(10, "JOSE SOUZA", "Líder"),
    _linha_pesquisa(10, "RITA DIAS", "Executor"),
    _linha_pesquisa(11, "PAULO REIS", "Executor", registro=""),                 # sem líder: executor coordena
    _linha_pesquisa(12, "MARIA ALVES", "Líder", situacao="Concluído"),          # fora: concluído
    _linha_pesquisa(13, "CARLOS NUNES", "Líder", ano="2015.0", inicio="2015-03-01"),  # fora: registrado há muito tempo
    _linha_pesquisa(14, "LUCIA PRADO", "Líder", situacao="Seleção de IC - Projeto inscrito", ano="2027.0",
                    inicio="2027-03-01"),                                      # fora: ainda não começou
    _linha_pesquisa(15, "PEDRO MOTA", "Líder", fim="2026-01-31"),               # fora: terminou
)


class _RespostaCsv:
    def __init__(self, conteudo):
        self.content = conteudo


class _ClienteCsv:
    def __init__(self, conteudo=CSV_PESQUISA, ano_minimo=2022):
        self.cfg = UfvConfig(pesquisa_ano_minimo=ano_minimo)
        self.conteudo = conteudo
        self.total_requisicoes = 0

    def request_raw(self, method, url, **kw):
        self.total_requisicoes += 1
        assert url == self.cfg.url_csv_pesquisa
        return _RespostaCsv(self.conteudo)


def test_agrupa_so_os_projetos_vigentes():
    estat = {}
    grupos = coleta.listar_pesquisa(_ClienteCsv(), HOJE, estat)
    assert sorted(g["codigo_projeto"] for g in grupos) == ["10", "11"]
    assert estat["linhas"] == 8 and estat["projetos_vigentes"] == 2
    assert estat["por_situacao_ano"][("Registrado", 2025)] == 5
    g10 = next(g for g in grupos if g["codigo_projeto"] == "10")
    assert [p["nome"] for p in g10["equipe"]] == ["ANA LIMA", "JOSE SOUZA", "RITA DIAS"]


def test_registro_de_pesquisa():
    grupos = {g["codigo_projeto"]: g for g in coleta.listar_pesquisa(_ClienteCsv(), HOJE)}
    r = registro_pesquisa(grupos["10"])
    assert r["modulo"] == "pesquisa" and r["ufv_id"] == "p10" and r["codigo"] == "00000504460"
    assert r["titulo"] == "Projeto 10" and r["coordenador"] == "JOSE SOUZA" and r["email"] is None
    assert r["unidade"] == "DPS" and r["ano"] == "2025" and r["situacao"] == "EM EXECUÇÃO"
    assert r["categoria"] == "Iniciação Científica" and r["periodo_inicio"] == "2025-03-01" and r["periodo_fim"] is None
    assert r["link_detalhe"] == "https://www2.dti.ufv.br/sisppg/scripts/projetos/verProjeto.php?registro=00000504460"
    assert r["descricao"] == "Objetivo do projeto 10"
    assert r["extras"]["area_cnpq"] == "Ciência do Solo" and r["extras"]["palavras_chave"] == ["solo", "água"]
    assert r["extras"]["financiamento"] == "Com financiamento" and r["extras"]["linha_pesquisa"] == "Linha Y nome"
    assert len(r["extras"]["equipe"]) == 3
    r11 = registro_pesquisa(grupos["11"])
    assert r11["coordenador"] == "PAULO REIS" and r11["link_detalhe"] is None and r11["codigo"] is None


async def test_sync_dos_dois_modulos_desativa_por_modulo(db):
    cfg = UfvConfig(pesquisa_ano_minimo=2022)
    ckan = _ClienteCkan([[_linha(1)]])
    csv_client = _ClienteCsv()

    class _Cliente:
        cfg = csv_client.cfg
        total_requisicoes = 0

        def get(self, *a, **kw):
            return ckan.get(*a, **kw)

        def request_raw(self, *a, **kw):
            return csv_client.request_raw(*a, **kw)

    coletores = {"extensao": (coleta.listar_extensao, registro_extensao),
                 "pesquisa": (lambda c, hoje, estat: coleta.listar_pesquisa(c, HOJE, estat), registro_pesquisa)}
    run = await executar_sync(db, cfg, client=_Cliente(), coletores=coletores)
    assert run["status"] == "sucesso"
    assert run["modulos"]["extensao"]["novos"] == 1 and run["modulos"]["pesquisa"]["novos"] == 2
    doc = await db.projetos.find_one({"ufv_id": "p10"})
    assert doc["origem"] == "ufv" and doc["modulo"] == "pesquisa" and doc["nome_professor"] == "JOSE SOUZA"
    assert doc["link_detalhe"].endswith("registro=00000504460")

    # pesquisa com falha (CSV vazio) não desativa a pesquisa nem encosta na extensão
    csv_client.conteudo = _csv()
    ckan.paginas = [[_linha(1)]]
    run = await executar_sync(db, cfg, client=_Cliente(), coletores=coletores)
    assert run["status"] == "falha" and run["modulos"]["pesquisa"]["status"] == "falha"
    assert run["modulos"]["extensao"]["status"] == "sucesso"
    assert (await db.projetos.find_one({"ufv_id": "p10"}))["ativo"] is True
    assert (await db.projetos.find_one({"ufv_id": "1"}))["ativo"] is True


def test_config_de_pesquisa_pelo_ambiente(monkeypatch):
    monkeypatch.setenv("UFV_MODULOS", "pesquisa")
    monkeypatch.setenv("UFV_PESQUISA_SITUACOES", "Registrado, Revisado")
    monkeypatch.setenv("UFV_PESQUISA_ANO_MINIMO", "2020")
    cfg = UfvConfig.from_env()
    assert cfg.modulos == ["pesquisa"] and cfg.pesquisa_situacoes == ("Registrado", "Revisado")
    assert cfg.pesquisa_ano_minimo == 2020
