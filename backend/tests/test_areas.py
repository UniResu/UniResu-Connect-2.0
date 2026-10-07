"""Classificação dos projetos nas grandes áreas do CNPq (services.areas).

Os casos reais vêm das fixtures de HTML do SIGAA/UNIR e dos portais da
UNIRIO (títulos e unidades verdadeiros, pessoas anonimizadas).
"""

import pytest

from conftest import FIXTURES, ler_fixture
from services import areas
from services.areas import (
    AGRARIAS, AREAS_CONHECIMENTO, BIOLOGICAS, ENGENHARIAS, EXATAS, HUMANAS, LINGUISTICA, MULTIDISCIPLINAR,
    SAUDE, SOCIAIS_APLICADAS, area_valida, classificar_area, garantir_area_conhecimento,
)
from services.sigaa import parser as sigaa
from services.unirio import parser as unirio

URL_EXT = "https://sistemas2.unirio.br/extensao/busca/projetos?f_status=1&f_uni=0&termos="
URL_PESQ = "https://sistemas.unirio.br/projetos/default/index"


def fixture_utf8(nome: str) -> str:
    return (FIXTURES / nome).read_text(encoding="utf-8")


def test_tabela_fixa_do_cnpq_na_ordem_de_exibicao():
    assert AREAS_CONHECIMENTO == (
        "Ciências Exatas e da Terra", "Ciências Biológicas", "Engenharias", "Ciências da Saúde",
        "Ciências Agrárias", "Ciências Sociais Aplicadas", "Ciências Humanas", "Linguística, Letras e Artes",
        "Multidisciplinar",
    )


@pytest.mark.parametrize("valor, esperado", [
    ("Ciências Exatas e da Terra", EXATAS),
    ("ciencias exatas e da terra", EXATAS),           # sem acentos e em minúsculas
    ("LINGUÍSTICA LETRAS E ARTES", LINGUISTICA),      # sem a vírgula
    ("Lingüística, Letras e Artes", LINGUISTICA),     # grafia antiga, com trema
    (" Ciências da Saúde ", SAUDE),
    ("Outra", None),
    ("Saúde", None),                                  # área temática da extensão, não é grande área
    ("", None),
    (None, None),
    (3, None),
])
def test_area_valida_normaliza_acentos_caixa_e_pontuacao(valor, esperado):
    assert area_valida(valor) == esperado


# ── 1. campo que já traz a grande área ──────────────────────────────────────

def test_area_cnpq_da_ufv_prevalece_sobre_tudo():
    doc = {"area_cnpq": "Ciências Exatas e da Terra", "titulo": "LUDICIDADE NO ENSINO DE MATEMÁTICA",
           "unidade": "Departamento de Educação"}
    assert classificar_area(doc) == EXATAS


def test_area_cnpq_fora_da_tabela_cai_nas_regras():
    assert classificar_area({"area_cnpq": "Outra", "titulo": "LUDICIDADE NO ENSINO DE MATEMÁTICA"}) == EXATAS
    assert classificar_area({"area_cnpq": "Outra", "titulo": "Mutirão"}) == MULTIDISCIPLINAR


def test_classificacao_cnpq_do_portal_da_pesquisa_da_unirio_vence_a_unidade():
    # O Portal da Pesquisa publica a grande área em `area_tematica` ("Classificação CNPq (principal)").
    d = unirio.parse_detalhe(fixture_utf8("unirio_pesquisa_detalhe.html"))
    assert d["extras"]["area_tematica"] == "CIÊNCIAS HUMANAS"
    assert classificar_area({**d, **d["extras"]}) == HUMANAS
    doc = {"unidade": "Departamento de Interpretacao Teatral", "area_tematica": "CIÊNCIAS DA SAÚDE"}
    assert classificar_area(doc) == SAUDE


def test_area_tematica_da_extensao_nao_e_grande_area_e_so_entra_como_pista():
    d = unirio.parse_detalhe(fixture_utf8("unirio_extensao_detalhe.html"))
    assert d["extras"]["area_tematica"] == "Saúde"
    # a unidade (teatro) decide antes das palavras-chave
    assert classificar_area({**d, **d["extras"]}) == LINGUISTICA
    # sem unidade, a área temática e o título apontam para a saúde
    assert classificar_area({**d, **d["extras"], "unidade": None}) == SAUDE


# ── 2. unidade/departamento ─────────────────────────────────────────────────

@pytest.mark.parametrize("unidade, esperado", [
    ("ESCOLA DE MEDICINA E CIRURGIA", SAUDE),
    ("Departamento de Alimentacao e Nutricao em Saude Coletiva", SAUDE),
    ("Departamento de Educação Física", SAUDE),           # antes de "Educação" e de "Física"
    ("Departamento de Engenharia Civil", ENGENHARIAS),
    ("Departamento de Engenharia Florestal", AGRARIAS),   # antes de "Engenharia"
    ("Departamento de Engenharia Agrícola", AGRARIAS),
    ("Departamento de Letras", LINGUISTICA),
    ("Departamento de Interpretacao Teatral", LINGUISTICA),
    ("Departamento de Ensino do Teatro", LINGUISTICA),
    ("Departamento de Composicao e Regencia", LINGUISTICA),
    ("Departamento de Cenografia", LINGUISTICA),
    ("Departamento de Servico Social", SOCIAIS_APLICADAS),
    ("Núcleo de Ciências Sociais Aplicadas", SOCIAIS_APLICADAS),  # antes de "Ciências Sociais"
    ("Departamento de Ciencias Sociais", HUMANAS),
    ("Departamento de Didatica", HUMANAS),
    ("COORDENAÇÃO DO CURSO DE PEDAGOGIA", HUMANAS),
    ("DEPARTAMENTO DE AGRONOMIA", AGRARIAS),
    ("Departamento de Botanica", BIOLOGICAS),
    ("Departamento de Ciencias Fisiologicas", BIOLOGICAS),
    ("Departamento de Farmácia", SAUDE),
    ("Departamento de Farmacologia", BIOLOGICAS),
    ("Departamento de Física", EXATAS),
    ("Departamento de Ciência da Computação", EXATAS),
    ("CAMPUS PORTO VELHO", None),                          # campus não diz a área
    ("DAENF", None),                                       # sigla do SIGAA: só o título ajuda
    (None, None),
])
def test_regras_por_unidade(unidade, esperado):
    assert areas._area_por_unidade(unidade) == esperado


# ── 3. palavras-chave ───────────────────────────────────────────────────────

SIGAA_PESQUISA = {
    "Formulações, processos e desdobramentos de políticas educacionais na Amazônia": HUMANAS,
    "Estimativa do Potencial Eólico na Camada Superficial Atmosférica no Sudeste de Rondônia": EXATAS,
    "A valorização dos Saberes Tradicionais Indígenas na Amazônia Brasileira: decolonialismo e políticas públicas":
        HUMANAS,
}


def test_pesquisa_do_sigaa_classifica_pelo_titulo_porque_a_unidade_e_o_campus():
    itens = sigaa.parse_listagem_pesquisa(ler_fixture("sigaa_pesquisa_listagem.html"))
    assert len(itens) == 3 and {i["unidade"] for i in itens} == {"CAMPUS ARIQUEMES", "CAMPUS CACOAL"}
    for item in itens:
        assert classificar_area(item) == SIGAA_PESQUISA[item["titulo"]], item["titulo"]


SIGAA_EXTENSAO = {
    "CODIR": SOCIAIS_APLICADAS,    # "...discurso jurídico e seu impacto nas políticas públicas..."
    "DCRM": AGRARIAS,              # "Implantação de um pomar urbano na cidade de Rolim de Moura"
    "DNCSA": MULTIDISCIPLINAR,     # "XXI Jornada Científica CEDSA": nenhuma pista
    "DCJP": EXATAS,                # "...aulões de matemática para o fortalecimento da aprendizagem"
    "CCPDG": HUMANAS,              # "Núcleo Educacional do Observatório Regional da Violência contra Educadoras/es"
    "DNS": SAUDE,                  # "MEDPOP - Informação instantânea sobre saúde"
    "DCA": LINGUISTICA,            # "Letras Info Hub: Literatura, Linguística, Cultura e Comunidade"
    "DAENF": SAUDE,                # "LETRAMENTO EM AVALIAÇÃO DE TECNOLOGIAS EM SAÚDE ... NO SUS"
}


def test_extensao_do_sigaa_classifica_pelo_titulo_porque_a_unidade_e_uma_sigla():
    itens = sigaa.parse_listagem_extensao(ler_fixture("sigaa_extensao_listagem.html"))
    assert len(itens) == 8
    assert {i["unidade"]: classificar_area(i) for i in itens} == SIGAA_EXTENSAO


def test_detalhe_do_sigaa_traz_a_unidade_por_extenso_e_a_descricao():
    listagem = sigaa.parse_listagem_extensao(ler_fixture("sigaa_extensao_listagem.html"))
    item = next(i for i in listagem if i["sigaa_id"] == "4527")
    detalhe = sigaa.parse_detalhe_extensao(ler_fixture("sigaa_extensao_detalhe.html"))
    assert detalhe["unidade"] == "COORDENAÇÃO DO CURSO DE PEDAGOGIA"
    assert classificar_area({**item, **detalhe}) == HUMANAS

    item = sigaa.parse_listagem_pesquisa(ler_fixture("sigaa_pesquisa_listagem.html"))[0]
    detalhe = sigaa.parse_detalhe_pesquisa(ler_fixture("sigaa_pesquisa_detalhe.html"))
    assert detalhe["descricao"].startswith("A pesquisa problematiza")
    assert classificar_area({**item, **detalhe}) == HUMANAS


UNIRIO_EXTENSAO = {
    "Maré de Saúde": LINGUISTICA,                        # Departamento de Interpretacao Teatral
    "Maré de espetáculos": LINGUISTICA,                  # Departamento de Ensino do Teatro
    "PERCEPÇÃO": LINGUISTICA,                            # Departamento de Composicao e Regencia
    "Teatro na Prisão: Uma experiência pedagógica em busca do sujeito cidadão": LINGUISTICA,
    "Documentação e Divulgação do Monumento Natural do Pão de Açúcar": BIOLOGICAS,  # Departamento de Botanica
}


def test_extensao_da_unirio_classifica_pela_unidade():
    itens = unirio.parse_listagem(fixture_utf8("unirio_extensao_listagem.html"), "extensao", URL_EXT)
    assert len(itens) == 5
    assert {i["titulo"]: classificar_area(i) for i in itens} == UNIRIO_EXTENSAO


UNIRIO_PESQUISA = {
    "Departamento de Didatica": HUMANAS,
    "Departamento de Interpretacao Teatral": LINGUISTICA,
    "Departamento de Ciencias Fisiologicas": BIOLOGICAS,
    "Departamento de Servico Social": SOCIAIS_APLICADAS,
    "Departamento de Alimentacao e Nutricao em Saude Coletiva": SAUDE,
    "Departamento de Ciencias Sociais": HUMANAS,
    "Departamento de Cenografia": LINGUISTICA,
}


def test_pesquisa_da_unirio_classifica_pela_unidade():
    itens = unirio.parse_listagem(fixture_utf8("unirio_pesquisa_listagem.html"), "pesquisa", URL_PESQ)
    assert len(itens) == 8
    for item in itens:
        assert classificar_area(item) == UNIRIO_PESQUISA[item["unidade"]], item["titulo"]


@pytest.mark.parametrize("doc, esperado", [
    ({"titulo": "Robótica educacional"}, ENGENHARIAS),            # assunto (2) vence palavra de escola (1)
    ({"titulo": "Ensino de Química com experimentos", "descricao": "Para alunos da escola pública"}, EXATAS),
    ({"titulo": "Educação Física escolar"}, SAUDE),
    ({"titulo": "Horta comunitária"}, AGRARIAS),
    ({"titulo": "Clínica de leitura", "palavras_chave": ["saúde", "extensão"]}, SAUDE),
    ({"titulo": "Projeto Vida", "descricao": "Acompanhamento de pacientes hipertensos no hospital universitário"},
     SAUDE),                                                       # só a descrição tem pistas
    ({"titulo": "Gestão de resíduos sólidos"}, ENGENHARIAS),
    ({"titulo": "Direitos humanos e cidadania"}, SOCIAIS_APLICADAS),
    ({"titulo": "Oficina de violão", "descricao": "Aulas de música para a comunidade"}, LINGUISTICA),
    ({"titulo": "Semana interdisciplinar de pesquisa"}, MULTIDISCIPLINAR),
    ({"titulo": "XXI Jornada Científica CEDSA"}, MULTIDISCIPLINAR),
    ({"titulo": ""}, MULTIDISCIPLINAR),
    ({}, MULTIDISCIPLINAR),
])
def test_palavras_chave_e_fallback(doc, esperado):
    assert classificar_area(doc) == esperado


def test_area_de_estudo_do_projeto_manual_conta_quando_e_uma_grande_area():
    assert classificar_area({"area_estudo": "Ciências Humanas", "titulo": "Horta comunitária"}) == HUMANAS
    # valor antigo do formulário, fora da tabela: entra só como pista, junto do título
    assert classificar_area({"area_estudo": "Linguística e Letras", "titulo": "Sarau"}) == LINGUISTICA


# ── 4. migração ─────────────────────────────────────────────────────────────

async def test_migracao_preenche_em_lotes_e_e_idempotente(db):
    await db.projetos.insert_many([
        {"titulo": "Horta comunitária", "origem": "sigaa", "unidade": "DEPARTAMENTO DE AGRONOMIA"},
        {"titulo": "Robótica educacional", "origem": "sigaa", "unidade": "CAMPUS PORTO VELHO"},
        {"titulo": "Maré de Saúde", "origem": "unirio", "unidade": "Departamento de Interpretacao Teatral"},
        {"titulo": "Projeto da UFV", "origem": "ufv", "area_cnpq": "Ciências Exatas e da Terra"},
        {"titulo": "Projeto manual", "descricao": "Sem pista alguma"},
        {"titulo": "Com o campo nulo", "area_conhecimento": None},
        {"titulo": "Já classificado", "area_conhecimento": SAUDE},
    ])
    # lotes de 2 obrigam várias voltas do laço
    assert await garantir_area_conhecimento(db, tamanho_lote=2) == 6

    por_titulo = {d["titulo"]: d.get("area_conhecimento") async for d in db.projetos.find({})}
    assert por_titulo == {
        "Horta comunitária": AGRARIAS,
        "Robótica educacional": ENGENHARIAS,
        "Maré de Saúde": LINGUISTICA,
        "Projeto da UFV": EXATAS,
        "Projeto manual": MULTIDISCIPLINAR,
        "Com o campo nulo": MULTIDISCIPLINAR,
        "Já classificado": SAUDE,            # não é tocado
    }
    assert await garantir_area_conhecimento(db) == 0
    assert await db.projetos.count_documents({"area_conhecimento": None}) == 0
