"""
Fontes externas de projetos (coletas públicas) e seus campos no MongoDB.

Cada fonte grava na collection `projetos` com um `origem` próprio e uma
chave natural num campo exclusivo, para que a desativação/upsert de uma
fonte nunca encoste nos documentos de outra, nem nos projetos manuais.

`origem` identifica a plataforma de onde os dados vieram ("sigaa", "unirio",
"ufv", "puccamp"); `instituicao` é a universidade. Várias instituições compartilham a
plataforma SIGAA, então toda escrita filtra pelos dois campos.
"""

from dataclasses import dataclass

from services.sigaa.instituicoes import INSTITUICOES_SIGAA

MODULOS = ("pesquisa", "extensao")
MODULO_LABEL = {"pesquisa": "Pesquisa", "extensao": "Extensão"}


@dataclass(frozen=True)
class Fonte:
    origem: str          # valor do campo `origem` (ex.: "sigaa")
    instituicao: str     # sigla exibida no front (ex.: "UNIR")
    rotulo: str          # nome da fonte para textos (ex.: "SIGAA/UNIR")
    campo_chave: str     # campo com a chave natural (único por origem)
    campo_id: str        # campo com o id do projeto na fonte
    # Prefixo da chave natural, para instituições que dividem a mesma origem
    # (a chave da UNIR ficou sem prefixo por ser anterior a isso).
    prefixo_chave: str = ""


def fonte_sigaa(sigla: str) -> Fonte:
    """Fonte de uma instituição que usa o SIGAA: mesma origem e mesmos campos
    da UNIR, mudando sigla, rótulo e o prefixo da chave."""
    sigla = sigla.strip().upper()
    if sigla not in INSTITUICOES_SIGAA:
        raise ValueError(f"Instituição SIGAA desconhecida: {sigla!r}")
    return Fonte("sigaa", sigla, f"SIGAA/{sigla}", "chave_sigaa", "sigaa_id",
                 prefixo_chave="" if sigla == "UNIR" else sigla.lower() + "|")


SIGAA = fonte_sigaa("UNIR")
UNIRIO = Fonte("unirio", "UNIRIO", "Portais da UNIRIO", "chave_unirio", "unirio_id")
UFV = Fonte("ufv", "UFV", "Dados abertos da UFV", "chave_ufv", "ufv_id")
PUCCAMP = Fonte("puccamp", "PUC-Campinas", "Portal da PUC-Campinas", "chave_puccamp", "puccamp_id")

# Uma fonte por plataforma (a do SIGAA representa a UNIR, a primeira coletada).
FONTES = {f.origem: f for f in (SIGAA, UNIRIO, UFV, PUCCAMP)}

# Uma fonte por instituição, para rótulos e filtros do front.
INSTITUICOES: dict[str, Fonte] = {sigla: fonte_sigaa(sigla) for sigla in INSTITUICOES_SIGAA}
INSTITUICOES.update({f.instituicao: f for f in (UNIRIO, UFV, PUCCAMP)})
