"""
Financiamento dos projetos, para o filtro "Projetos financiados".

Os SIGAAs publicam quem financia cada projeto de forma diferente por módulo:

- Pesquisa: a consulta pública filtra por "Agência Financiadora" (a página do
  projeto não mostra o campo). Cada nome de agência é classificado aqui.
- Extensão: o detalhe da ação traz "Nº Bolsas Concedidas" e "Fonte de
  Financiamento" (FINANCIAMENTO INTERNO, FINANCIAMENTO EXTERNO, AÇÃO
  AUTO-FINANCIADA...).

`classificar_financiador` transforma um desses textos em etiquetas:
"capes", "cnpq", "fap" (mais "fap:<SIGLA>" com a fundação estadual) e
"instituicao" (a própria universidade). Nomes que não se encaixam (FINEP,
ministérios, empresas, fundações de apoio) ficam sem etiqueta.

Nenhum dado de bolsista entra aqui: só o nome de quem financia e o número de
bolsas que a fonte publica.
"""

import re
from typing import Iterable, Optional

from services.sigaa.parser import normalizar

BOLSA = "bolsa"  # opção do filtro: vem de `bolsas_alunos > 0`, não de etiqueta
CAPES = "capes"
CNPQ = "cnpq"
FAP = "fap"
INSTITUICAO = "instituicao"

# Ordem fixa das opções do filtro.
CATEGORIAS = (BOLSA, CAPES, CNPQ, FAP, INSTITUICAO)
PREFIXO_FAP = FAP + ":"

# Fundação estadual de amparo à pesquisa de cada estado. A chave é o nome do
# estado normalizado; os nomes compostos vêm antes dos que estão contidos
# neles (MATO GROSSO DO SUL antes de MATO GROSSO).
_FAPS_POR_ESTADO = (
    ("RIO GRANDE DO NORTE", "FAPERN"),
    ("RIO GRANDE DO SUL", "FAPERGS"),
    ("MATO GROSSO DO SUL", "FUNDECT"),
    ("MATO GROSSO", "FAPEMAT"),
    ("RIO DE JANEIRO", "FAPERJ"),
    ("SAO PAULO", "FAPESP"),
    ("MINAS GERAIS", "FAPEMIG"),
    ("ESPIRITO SANTO", "FAPES"),
    ("DISTRITO FEDERAL", "FAPDF"),
    ("SANTA CATARINA", "FAPESC"),
    ("PARANA", "Fundação Araucária"),
    ("PARAIBA", "FAPESQ"),
    ("PERNAMBUCO", "FACEPE"),
    ("ALAGOAS", "FAPEAL"),
    ("SERGIPE", "FAPITEC"),
    ("BAHIA", "FAPESB"),
    ("CEARA", "FUNCAP"),
    ("CEARENSE", "FUNCAP"),
    ("PIAUI", "FAPEPI"),
    ("MARANHAO", "FAPEMA"),
    ("TOCANTINS", "FAPT"),
    ("GOIAS", "FAPEG"),
    ("RONDONIA", "FAPERO"),
    ("ACRE", "FAPAC"),
    ("AMAZONAS", "FAPEAM"),
    ("RORAIMA", "FAPERR"),
    ("AMAPA", "FAPEAP"),
    # "do Pará": "para" sozinho é preposição.
    ("DO PARA", "FAPESPA"),
    ("PARAENSE", "FAPESPA"),
    ("AMAZONIA DE AMPARO", "FAPESPA"),
)

# Siglas das FAPs como aparecem nos nomes das agências.
_SIGLAS_FAP = {
    "FAPERN": "FAPERN", "FAPERGS": "FAPERGS", "FUNDECT": "FUNDECT", "FAPEMAT": "FAPEMAT",
    "FAPERJ": "FAPERJ", "FAPESP": "FAPESP", "FAPEMIG": "FAPEMIG", "FAPES": "FAPES",
    "FAPDF": "FAPDF", "FAP-DF": "FAPDF", "FAPESC": "FAPESC", "ARAUCARIA": "Fundação Araucária",
    "FAPESQ": "FAPESQ", "FACEPE": "FACEPE", "FAPEAL": "FAPEAL", "FAPITEC": "FAPITEC",
    "FAPESB": "FAPESB", "FUNCAP": "FUNCAP", "FAPEPI": "FAPEPI", "FAPEMA": "FAPEMA",
    "FAPT": "FAPT", "FAPEG": "FAPEG", "FAPERO": "FAPERO", "FAPAC": "FAPAC",
    "FAPEAM": "FAPEAM", "FAPERR": "FAPERR", "FAPEAP": "FAPEAP", "FAPESPA": "FAPESPA",
}
_RE_SIGLA_FAP = re.compile(r"\b(" + "|".join(re.escape(s) for s in sorted(_SIGLAS_FAP, key=len, reverse=True)) + r")\b")

_RE_CNPQ = re.compile(r"\bCNPQ\b|CONSELHO NACIONAL DE DESENVOLVIMENTO CIENTIFICO")
_RE_CAPES = re.compile(r"\bCAPES\b|APERFEICOAMENTO DE PESSOAL DE NIVEL SUPERIOR")

# Nome por extenso de uma FAP: "Fundação de Amparo à Pesquisa do Estado de X",
# "Fundação de Apoio à Pesquisa do Distrito Federal", "Fundação Cearense de
# Apoio ao Desenvolvimento Científico". Sem estado no nome, não dá para saber
# qual é (e "Fundação de Apoio à Pesquisa e à Extensão" é fundação de apoio de
# universidade, não FAP).
_RE_AMPARO = re.compile(r"\bAMPARO\b")
_RE_APOIO_CIENCIA = re.compile(r"\bAPOIO\b.*\b(PESQUISA|CIENTIFIC\w*|CIENCIA)\b")

# Recursos da própria instituição sem o nome dela: pró-reitorias e editais internos.
_RE_INTERNO = re.compile(
    r"\bPRO-? ?REITORIA\b|\bPROPESQ\b|\bPROPESP\b|\bPROPESPI\b|\bPRPPG\b|\bPROPPG\b|\bPROPPI\b|\bPROPG\b"
    r"|\bPRPG\b|\bPROPI\b|\bRECURSOS? PROPRIOS?\b|\bFINANCIAMENTO INTERNO\b|\bEDITAL INTERNO\b"
)
# Menção a outra instituição (uma pró-reitoria de outra universidade não é recurso próprio).
_RE_OUTRA_INSTITUICAO = re.compile(r"\bUNIVERSIDADE\b|\bINSTITUTO FEDERAL\b|\b(?:UF|IF|UE)[A-Z]{1,6}\b")


def _faps(texto: str) -> set[str]:
    siglas = {_SIGLAS_FAP[m.group(1)] for m in _RE_SIGLA_FAP.finditer(texto)}
    # "Extensão" no nome é de fundação de apoio de universidade (FAPESE, da UFS:
    # "Fundação de Apoio à Pesquisa e Extensão de Sergipe"), nunca de FAP.
    if "EXTENSAO" in texto:
        return siglas
    if _RE_AMPARO.search(texto) or _RE_APOIO_CIENCIA.search(texto):
        for estado, sigla in _FAPS_POR_ESTADO:
            if re.search(r"\b" + estado + r"\b", texto):
                siglas.add(sigla)
                break
    return siglas


def _da_instituicao(texto: str, sigla: Optional[str], nome: Optional[str]) -> bool:
    if sigla and re.search(r"\b" + re.escape(normalizar(sigla)) + r"\b", texto):
        return True
    if nome and normalizar(nome) in texto:
        return True
    return bool(_RE_INTERNO.search(texto)) and not _RE_OUTRA_INSTITUICAO.search(texto)


def classificar_financiador(texto: Optional[str], sigla: Optional[str] = None,
                            nome: Optional[str] = None) -> list[str]:
    """Etiquetas de financiamento de um nome de agência ou fonte, em ordem
    estável. `sigla` e `nome` são os da instituição dona do projeto, para
    reconhecer recurso próprio ("UFRN", "Pró-Reitoria de Pesquisa da UFRN",
    "Fundação Universidade Federal de Rondônia").

    >>> classificar_financiador("CNPq + UFRN", "UFRN")
    ['cnpq', 'instituicao']
    >>> classificar_financiador("Fundação de Amparo à Pesquisa do Estado de São Paulo")
    ['fap', 'fap:FAPESP']
    """
    t = normalizar(texto)
    if not t:
        return []
    etiquetas: set[str] = set()
    if _RE_CAPES.search(t):
        etiquetas.add(CAPES)
    if _RE_CNPQ.search(t):
        etiquetas.add(CNPQ)
    faps = _faps(t)
    if faps:
        etiquetas.add(FAP)
        etiquetas.update(PREFIXO_FAP + s for s in faps)
    if _da_instituicao(t, sigla, nome):
        etiquetas.add(INSTITUICAO)
    return sorted(etiquetas)


def juntar(*listas: Optional[Iterable[str]]) -> list[str]:
    """União de listas de etiquetas, em ordem estável."""
    return sorted({e for lista in listas if lista for e in lista})
