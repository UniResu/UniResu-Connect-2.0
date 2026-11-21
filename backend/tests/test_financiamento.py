"""Classificação de quem financia os projetos (filtro "Projetos financiados")."""

import re

import pytest

from conftest import ler_fixture
from services.financiamento import classificar_financiador, juntar
from services.sigaa import parser

UNIR = ("UNIR", "Universidade Federal de Rondônia")
UFRN = ("UFRN", "Universidade Federal do Rio Grande do Norte")
UFS = ("UFS", "Universidade Federal de Sergipe")
SEM = (None, None)


@pytest.mark.parametrize("texto, inst, esperado", [
    ("CAPES", UNIR, ["capes"]),
    ("CNPQ", UNIR, ["cnpq"]),
    ("Finep+CnPq", UNIR, ["cnpq"]),
    ("MCT/CNPq/MEC/CAPES", UNIR, ["capes", "cnpq"]),
    ("CNPq + UFRN", UFRN, ["cnpq", "instituicao"]),
    ("FAPERO", UNIR, ["fap", "fap:FAPERO"]),
    ("Fundação Araucária", UFRN, ["fap", "fap:Fundação Araucária"]),
    ("Fundação de Amparo à Pesquisa do Estado de São Paulo", UFRN, ["fap", "fap:FAPESP"]),
    ("Fundação de Amparo à Pesquisa do Estado de Minas Gerais", UFRN, ["fap", "fap:FAPEMIG"]),
    ("Fundação de Amparo a Ciência e Tecnologia do estado de Pernambuco", UFRN, ["fap", "fap:FACEPE"]),
    ("Fundação Cearense de Apoio ao Desenvolvimento Científico e Tecnológico", UFRN, ["fap", "fap:FUNCAP"]),
    ("Fundação de Apoio a Pesquisa do Distrito Federal", UFRN, ["fap", "fap:FAPDF"]),
    ("Fundação Carlos Chagas Filho de Amparo à Pesquisa do Estado do Rio de Janeiro", UFRN, ["fap", "fap:FAPERJ"]),
    ("Fundação de Amparo à Pesquisa do Estado do Rio Grande do Sul", UFRN, ["fap", "fap:FAPERGS"]),
    ("Fundação de Apoio ao Desenvolvimento do Ensino, Ciência e Tecnologia do Estado de Mato Grosso do Sul",
     UFRN, ["fap", "fap:FUNDECT"]),
    ("Fundação Amazônia de Amparo a Estudos e Pesquisas", UFRN, ["fap", "fap:FAPESPA"]),
    ("FUNDAÇÃO UNIVERSIDADE FEDERAL DE RONDÔNIA", UNIR, ["instituicao"]),
    ("UNIR/ PROART", UNIR, ["instituicao"]),
    ("UFRN Emenda Parlamentar", UFRN, ["instituicao"]),
    ("Pró-Reitoria de Pesquisa da UFRN", UFRN, ["instituicao"]),
    ("FINANCIAMENTO INTERNO", SEM, ["instituicao"]),
    # Pró-reitoria de outra universidade não é recurso próprio.
    ("Pró-Reitoria de Pesquisa da UFRN", UNIR, []),
    # Fora das categorias do filtro.
    ("FINANCIAMENTO EXTERNO", SEM, []),
    ("AÇÃO AUTO-FINANCIADA", SEM, []),
    ("Sem Financiamento", UNIR, []),
    ("FINEP", UNIR, []),
    ("FAPAM", UNIR, []),
    ("Fundação Carlos Chagas", UFRN, []),
    ("Fundação Oswaldo Cruz", UFRN, []),
    # Fundações de apoio de universidades, que não são FAPs.
    ("Fundação de Apoio da UFMG", UFRN, []),
    ("Fundação de Apoio à Pesquisa e à Extensão", UFRN, []),
    ("Fundação de Apoio à Pesquisa e Extensão de Sergipe", UFS, []),
    ("Fundação de Amparo e Desenvolvimento da Pesquisa", UFRN, []),
    ("Fundação de Apoio à Educação e ao Desenvolvimento Tecnológico do Rio Grande do Norte", UFRN, []),
    ("Fundação Espírito-santense de Tecnologia", UFRN, []),
    ("", UNIR, []),
    (None, UNIR, []),
])
def test_classificar_financiador(texto, inst, esperado):
    assert classificar_financiador(texto, *inst) == esperado


def test_juntar_une_sem_repetir():
    assert juntar(["cnpq"], None, ["fap", "cnpq"], []) == ["cnpq", "fap"]


def test_detalhe_da_extensao_traz_bolsas_e_fonte():
    detalhe = parser.parse_detalhe_extensao(ler_fixture("sigaa_extensao_detalhe.html"))
    assert detalhe["bolsas_concedidas"] == 0
    assert detalhe["fonte_financiamento"] == "FINANCIAMENTO EXTERNO"
    # Só número e fonte: nada sobre quem recebe a bolsa.
    assert not any("bolsista" in k.lower() for k in detalhe)


def test_detalhe_da_extensao_com_bolsas():
    html = re.sub(r"(<th>Nº Bolsas Concedidas:</th>\s*<td>)\s*0\s*", r"\g<1>3", ler_fixture("sigaa_extensao_detalhe.html"))
    html = html.replace("FINANCIAMENTO EXTERNO", "FINANCIAMENTO INTERNO")
    detalhe = parser.parse_detalhe_extensao(html)
    assert detalhe["bolsas_concedidas"] == 3
    assert detalhe["fonte_financiamento"] == "FINANCIAMENTO INTERNO"
