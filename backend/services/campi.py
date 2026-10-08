"""
Campus de cada projeto, deduzido do que a fonte publica sobre a unidade.

As fontes não têm um campo "campus": o SIGAA embute a cidade no nome do
centro ("CENTRO DE CIÊNCIAS DA SAÚDE - NATAL - 15.00"), a UNIR usa siglas de
campus no fim do nome da unidade ("COORDENADORIA DO CURSO DE DIREITO - CAC"),
os institutos federais prefixam a unidade com "C-" e a cidade, e a UNIRIO e
a UFV têm quase tudo na sede. O resultado fica em `campus` e alimenta o
filtro de campi da busca.
"""

import re
from typing import Optional

from services.sigaa.parser import normalizar

# UNIR: siglas de campus que aparecem no fim do nome da unidade.
CAMPI_UNIR = {
    "ARI": "Ariquemes",
    "CAC": "Cacoal",
    "GM": "Guajará-Mirim",
    "JIP": "Ji-Paraná",
    "PM": "Presidente Médici",
    "RM": "Rolim de Moura",
    "VHA": "Vilhena",
    "PVH": "Porto Velho",
}
# Unidades da UNIR em Porto Velho (núcleos e departamentos sem sigla de campus).
SEDE_UNIR = "Porto Velho"

# Sede de instituições concentradas em uma cidade (quando a unidade não diz outra coisa).
SEDES = {
    "PUC-CAMPINAS": "Campinas",
    "UNIRIO": "Rio de Janeiro",
    "UFV": "Viçosa",
    "UNIR": SEDE_UNIR,
}

# UFV: siglas de departamento dos campi fora de Viçosa.
PREFIXOS_UFV = {"CAF": "Florestal", "CRP": "Rio Paranaíba"}

# "... - NATAL - 15.00", "CAMPUS ARIQUEMES - ARIQUEMES - 11.35", "CERES - CAICÓ - 18.04"
_RE_CIDADE_CODIGO = re.compile(r" - ([A-ZÀ-Ü][A-ZÀ-Ü' ]+?) - [\d.]+$")
# IFAL e outros institutos: "C-MARAGOGI", "CAMPUS MACEIÓ".
_RE_C_CIDADE = re.compile(r"^(?:C-|CAMPUS )([A-ZÀ-Ü][A-ZÀ-Ü' -]+)$")
# Sigla de campus da UNIR no fim do nome, com ou sem código depois.
_RE_SIGLA_UNIR = re.compile(r" - (ARI|CAC|GM|JIP|PM|RM|VHA|PVH)(?: - .*)?$")


def _titulo(cidade: str) -> str:
    """"PRESIDENTE MÉDICI" -> "Presidente Médici", preservando conectivos minúsculos."""
    pequenas = {"de", "da", "do", "das", "dos", "e"}
    palavras = []
    for i, p in enumerate(cidade.strip().lower().split()):
        palavras.append(p if (p in pequenas and i > 0) else p.capitalize())
    return " ".join(palavras)


def extrair_campus(doc: dict) -> Optional[str]:
    """Campus do projeto a partir de `instituicao`, `unidade` e, na UFV, da
    sigla do departamento. Devolve None quando não há como saber."""
    instituicao = (doc.get("instituicao") or "").strip().upper()
    unidade = (doc.get("unidade") or "").strip()
    # Maiúsculas com acentos preservados: a cidade extraída mantém a grafia.
    unidade_maiusc = " ".join(unidade.upper().split())

    if instituicao == "UNIR":
        m = _RE_SIGLA_UNIR.search(unidade_maiusc)
        if m:
            return CAMPI_UNIR[m.group(1)]
        m = _RE_CIDADE_CODIGO.search(unidade_maiusc)
        if m:
            return _titulo(m.group(1))
        unidade_norm = normalizar(unidade)
        for sigla, cidade in CAMPI_UNIR.items():
            if normalizar(cidade) in unidade_norm:
                return cidade
        return SEDE_UNIR if unidade else None

    if instituicao == "UFV":
        sigla = (doc.get("departamento_sigla") or unidade or "").strip().upper()
        for prefixo, cidade in PREFIXOS_UFV.items():
            if sigla.startswith(prefixo):
                return cidade
        return SEDES["UFV"]

    if instituicao in SEDES:
        return SEDES[instituicao]

    m = _RE_CIDADE_CODIGO.search(unidade_maiusc)
    if m:
        return _titulo(m.group(1))
    m = _RE_C_CIDADE.match(unidade_maiusc)
    if m:
        return _titulo(m.group(1))
    return None


async def garantir_campus(db, tamanho_lote: int = 500) -> int:
    """Preenche `campus` nos projetos coletados que ainda não têm o campo, em
    lotes. Documentos sem campus dedutível recebem null, para não serem
    reprocessados a cada startup. Idempotente. Devolve quantos documentos
    mudaram."""
    filtro = {"origem": {"$exists": True}, "campus": {"$exists": False}}
    projecao = {"instituicao": 1, "unidade": 1, "departamento_sigla": 1}
    total = 0
    while True:
        lote = await db.projetos.find(filtro, projecao).limit(tamanho_lote).to_list(tamanho_lote)
        if not lote:
            return total
        por_campus: dict[Optional[str], list] = {}
        for doc in lote:
            por_campus.setdefault(extrair_campus(doc), []).append(doc["_id"])
        modificados = 0
        for campus, ids in por_campus.items():
            resultado = await db.projetos.update_many({"_id": {"$in": ids}}, {"$set": {"campus": campus}})
            modificados += resultado.modified_count
        total += modificados
        if modificados == 0:
            return total
