"""
Fontes externas de projetos (coletas públicas) e seus campos no MongoDB.

Cada fonte grava na collection `projetos` com um `origem` próprio e uma
chave natural num campo exclusivo, para que a desativação/upsert de uma
fonte nunca encoste nos documentos de outra, nem nos projetos manuais.
"""

from dataclasses import dataclass

MODULOS = ("pesquisa", "extensao")
MODULO_LABEL = {"pesquisa": "Pesquisa", "extensao": "Extensão"}


@dataclass(frozen=True)
class Fonte:
    origem: str          # valor do campo `origem` (ex.: "sigaa")
    instituicao: str     # sigla exibida no front (ex.: "UNIR")
    rotulo: str          # nome da fonte para textos (ex.: "SIGAA/UNIR")
    campo_chave: str     # campo com a chave natural (único por origem)
    campo_id: str        # campo com o id do projeto na fonte


SIGAA = Fonte("sigaa", "UNIR", "SIGAA/UNIR", "chave_sigaa", "sigaa_id")
UNIRIO = Fonte("unirio", "UNIRIO", "Portais da UNIRIO", "chave_unirio", "unirio_id")
UFV = Fonte("ufv", "UFV", "Dados abertos da UFV", "chave_ufv", "ufv_id")

FONTES = {f.origem: f for f in (SIGAA, UNIRIO, UFV)}
