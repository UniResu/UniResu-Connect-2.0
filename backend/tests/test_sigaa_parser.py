"""Parser do HTML do SIGAA, contra páginas reais salvas (dados pessoais anonimizados)."""

from datetime import date

import pytest

from conftest import ler_fixture
from services.sigaa import parser
from services.sigaa.scraper import montar_payload_busca


class TestListagemPesquisa:
    def test_extrai_projetos_com_campos_da_listagem(self):
        itens = parser.parse_listagem_pesquisa(ler_fixture("sigaa_pesquisa_listagem.html"))

        assert len(itens) == 3
        primeiro = itens[0]
        assert primeiro["codigo"] == "PVC2148-2026"
        assert primeiro["titulo"] == "Formulações, processos e desdobramentos de políticas educacionais na Amazônia"
        assert primeiro["coordenador"] == "ANA PAULA SOUZA"
        assert primeiro["categoria"] == "EXTERNO"
        assert primeiro["situacao"] == "EM EXECUÇÃO"
        assert primeiro["ano"] == "2026"
        assert primeiro["unidade"] == "CAMPUS ARIQUEMES"
        assert primeiro["sigaa_id"] == "8120935"

    def test_unidade_acompanha_agrupamento_por_centro(self):
        itens = parser.parse_listagem_pesquisa(ler_fixture("sigaa_pesquisa_listagem.html"))
        assert [i["unidade"] for i in itens] == ["CAMPUS ARIQUEMES", "CAMPUS CACOAL", "CAMPUS CACOAL"]

    def test_guarda_parametros_do_link_de_detalhe(self):
        item = parser.parse_listagem_pesquisa(ler_fixture("sigaa_pesquisa_listagem.html"))[1]
        assert item["detalhe_params"]["id"] == "8167592"
        assert any(k.startswith("formConsulta:") for k in item["detalhe_params"])

    def test_html_sem_tabela_retorna_lista_vazia(self):
        assert parser.parse_listagem_pesquisa("<html><body>Nenhum projeto</body></html>") == []


class TestListagemExtensao:
    def test_extrai_acoes(self):
        itens = parser.parse_listagem_extensao(ler_fixture("sigaa_extensao_listagem.html"))

        assert len(itens) == 8
        projeto = next(i for i in itens if i["sigaa_id"] == "4527")
        assert projeto["ano"] == "2026"
        assert projeto["titulo"].startswith("Núcleo Educacional do Observatório Regional")
        assert projeto["categoria"] == "PROJETO"
        assert projeto["unidade"] == "CCPDG"
        assert projeto["link_detalhe"] == (
            "https://sigaa.unir.br/sigaa/link/public/extensao/visualizacaoAcaoExtensao/4527"
        )

    def test_mantem_categorias_para_filtrar_depois(self):
        categorias = {i["categoria"] for i in parser.parse_listagem_extensao(ler_fixture("sigaa_extensao_listagem.html"))}
        assert {"PROJETO", "PROGRAMA", "EVENTO", "CURSO"} <= categorias


class TestDetalhes:
    def test_detalhe_pesquisa(self):
        d = parser.parse_detalhe_pesquisa(ler_fixture("sigaa_pesquisa_detalhe.html"))
        assert d["coordenador"] == "ANA PAULA SOUZA"
        assert d["email"] == "coordenador@unir.br"
        assert d["unidade"] == "CAMPUS ARIQUEMES"
        assert d["situacao"] == "EM EXECUÇÃO"
        assert (d["periodo_inicio"], d["periodo_fim"]) == ("2026-06-06", "2028-12-31")
        assert d["descricao"].startswith("A pesquisa problematiza")

    def test_detalhe_extensao(self):
        d = parser.parse_detalhe_extensao(ler_fixture("sigaa_extensao_detalhe.html"))
        # A coordenação vem da equipe (docente com função de coordenação); o
        # "Responsável pela Ação" fica à parte, porque pode ser um discente.
        assert d["coordenador"] == "MEMBRO DA EQUIPE"
        assert d["responsavel_acao"] == "ANA PAULA SOUZA"
        assert [m["categoria"] for m in d["equipe"]] == ["DISCENTE", "DOCENTE", "DISCENTE"]
        assert d["equipe"][1]["funcao"] == "COORDENADOR(A)"
        assert d["email"] == "coordenador@unir.br"
        assert d["unidade"] == "COORDENAÇÃO DO CURSO DE PEDAGOGIA"
        assert (d["periodo_inicio"], d["periodo_fim"]) == ("2026-09-21", "2027-09-20")
        assert "Observatório Regional" in d["descricao"]

    @pytest.mark.parametrize("funcao", [parser.parse_detalhe_pesquisa, parser.parse_detalhe_extensao])
    def test_pagina_inesperada_levanta_erro(self, funcao):
        with pytest.raises(ValueError):
            funcao("<html><body><p>Sessão expirada</p></body></html>")

    @pytest.mark.parametrize("hoje, esperado", [
        (date(2026, 9, 1), "NÃO INICIADO"),
        (date(2026, 9, 21), "EM EXECUÇÃO"),
        (date(2027, 9, 20), "EM EXECUÇÃO"),
        (date(2027, 9, 21), "FINALIZADO"),
    ])
    def test_situacao_derivada_do_periodo(self, hoje, esperado):
        assert parser.situacao_por_periodo("2026-09-21", "2027-09-20", hoje) == esperado

    def test_situacao_sem_periodo_e_none(self):
        assert parser.situacao_por_periodo(None, None) is None


class TestFormularioJSF:
    """A página de resultados traz o mesmo form da consulta — serve de fixture."""

    def test_payload_pesquisa_tem_viewstate_filtros_e_botao(self):
        dados = montar_payload_busca(ler_fixture("sigaa_pesquisa_listagem.html"), "pesquisa", "2025", "EM EXECUÇÃO")

        assert "javax.faces.ViewState" in dados
        assert dados["formConsulta:ano"] == "2025"
        assert dados["formConsulta:checkAno"] == "on"
        assert dados["formConsulta:situacaoProjeto"] not in ("", "0")
        assert dados["formConsulta:checkSituacaoProjeto"] == "on"
        assert dados["formConsulta:buscar"] == "Buscar"
        assert "formConsulta:cancelar" not in dados

    def test_payload_extensao_ignora_situacao(self):
        dados = montar_payload_busca(ler_fixture("sigaa_extensao_listagem.html"), "extensao", "2026", "EM EXECUÇÃO")
        assert dados["formBuscaAtividade:buscaAno"] == "2026"
        assert dados["formBuscaAtividade:selectBuscaAno"] == "on"
        assert dados["formBuscaAtividade:btBuscar"] == "Buscar"

    def test_params_link_jsf(self):
        onclick = ("if(typeof jsfcljs == 'function'){jsfcljs(document.getElementById('form'),"
                   "{'form:j_id_1':'form:j_id_1','idAtividadeExtensaoSelecionada':'4695','acao':'2'},'');}return false")
        assert parser.params_link_jsf(onclick) == {
            "form:j_id_1": "form:j_id_1", "idAtividadeExtensaoSelecionada": "4695", "acao": "2",
        }


class TestEquipe:
    def test_coordenacao_prefere_docente_e_cai_no_responsavel(self):
        equipe = [{"nome": "JOAO", "categoria": "DISCENTE", "funcao": "COORDENADOR(A)"},
                  {"nome": "JANDRA", "categoria": "DOCENTE", "funcao": "COORDENADOR(A)"}]
        assert parser.coordenacao_da_equipe(equipe) == "JANDRA"
        assert parser.coordenacao_da_equipe(equipe[:1]) == "JOAO"
        assert parser.coordenacao_da_equipe([{"nome": "X", "categoria": "DOCENTE", "funcao": "MEMBRO"}]) is None
        assert parser.coordenacao_da_equipe([]) is None

    def test_sem_equipe_publicada_usa_o_responsavel(self):
        html = """<html><body><table><tr><th>Responsável pela Ação:</th><td>MARIA</td></tr>
        <tr><th>E-mail do Responsável:</th><td>m@unir.br</td></tr></table></body></html>"""
        d = parser.parse_detalhe_extensao(html)
        assert d["coordenador"] == "MARIA" and d["responsavel_acao"] == "MARIA" and d["equipe"] == []


class TestEquipeComEmail:
    HTML = """<html><body><table><tr><th>Título:</th><td>Ação X</td></tr>
    <tr><th>Responsável pela Ação:</th><td>JOAO DISCENTE</td></tr></table>
    <table class="equipeProjeto"><tr><td class="descricao"><span class="nome">
    <a href="#">MARIA DOCENTE</a><br/>Categoria: DOCENTE<br/>Função : COORDENADOR(A) MARIA.DOCENTE@ACADEMICO.UFPB.BR
    </span></td></tr></table>
    <table class="equipeProjeto"><tr><td class="descricao"><span class="nome">
    JOAO DISCENTE<br/>Categoria: DISCENTE<br/>Função : ALUNO(A) VOLUNTARIO(A) JOAO@GMAIL.COM
    </span></td></tr></table></body></html>"""

    def test_funcao_separada_do_email_e_email_da_coordenacao(self):
        d = parser.parse_detalhe_extensao(self.HTML)
        assert d["equipe"][0] == {"nome": "MARIA DOCENTE", "categoria": "DOCENTE", "funcao": "COORDENADOR(A)",
                                  "email": "maria.docente@academico.ufpb.br"}
        assert d["coordenador"] == "MARIA DOCENTE" and d["responsavel_acao"] == "JOAO DISCENTE"
        # sem "E-mail do Responsável", vale o e-mail da coordenação publicado na equipe
        assert d["email"] == "maria.docente@academico.ufpb.br"
        assert d["periodo_inicio"] is None

    def test_coordenacao_adjunta_nao_vence_a_titular(self):
        equipe = [{"nome": "ADJ", "categoria": "DOCENTE", "funcao": "COORDENADOR(A) ADJUNTO(A)"},
                  {"nome": "TIT", "categoria": "DOCENTE", "funcao": "COORDENADOR(A)"}]
        assert parser.coordenacao_da_equipe(equipe) == "TIT"

    def test_periodo_em_outros_rotulos(self):
        html = """<html><body><table><tr><th>Título:</th><td>Ação</td></tr>
        <tr><th>Data de Início:</th><td>01/03/2026</td></tr><tr><th>Data de Término:</th><td>30/11/2026</td></tr>
        </table></body></html>"""
        d = parser.parse_detalhe_extensao(html)
        assert (d["periodo_inicio"], d["periodo_fim"]) == ("2026-03-01", "2026-11-30")
