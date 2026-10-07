"""
Username público dos usuários.

Por que: o fórum (e qualquer tela pública) não pode expor e-mail. Cada
usuário ganha um `username` derivado do NOME — nunca do e-mail — em
minúsculas, com 3 a 30 caracteres de [a-z0-9._-], único na collection
`usuarios` (índice `uniq_username`, criado em database/indexes.py).

Gerado no registro (usuario_controller), no primeiro login via ORCID
(orcid_controller) e, para contas antigas, pelo backfill `preencher_usernames`
chamado em `migrar_dados` no startup da API.
"""

import re
import unicodedata
from typing import Iterable, Optional

USERNAME_MIN = 3
USERNAME_MAX = 30
USERNAME_PADRAO = "usuario"
USERNAME_REGEX = re.compile(r"^[a-z0-9._-]{3,30}$")

# Nomes que nunca são atribuídos automaticamente: `usuario` é o rótulo de
# autor não identificado no fórum e `uniresu` é o usuário de sistema do seed.
USERNAMES_RESERVADOS = frozenset({
    "usuario", "uniresu", "admin", "administrador", "sistema", "suporte", "forum",
})

_NAO_PERMITIDO = re.compile(r"[^a-z0-9]+")
_SUFIXO_NUMERICO = re.compile(r"-(\d+)$")


def gerar_username_base(nome: Optional[str]) -> str:
    """Slug do nome: "Matheus Gabriel" → "matheus-gabriel". Função pura.

    Remove acentos, baixa a caixa, troca qualquer sequência de caracteres
    fora de [a-z0-9] por um único "-" e corta em USERNAME_MAX. Nome vazio
    ou curto demais vira USERNAME_PADRAO (a unicidade fica por conta do
    sufixo em `gerar_username_unico`).
    """
    texto = unicodedata.normalize("NFKD", nome or "")
    texto = "".join(c for c in texto if not unicodedata.combining(c)).lower()
    slug = _NAO_PERMITIDO.sub("-", texto).strip("-")
    slug = slug[:USERNAME_MAX].rstrip("-")
    if len(slug) < USERNAME_MIN:
        return USERNAME_PADRAO
    return slug


def username_valido(username: Optional[str]) -> bool:
    return bool(username) and USERNAME_REGEX.fullmatch(username) is not None


def escolher_username_livre(base: str, ocupados: Iterable[str]) -> str:
    """Primeiro username livre entre `base`, `base-2`, `base-3`, ... Pura.

    O sufixo nunca estoura USERNAME_MAX: a base é encurtada para abrir
    espaço (ex.: base de 30 letras → 28 letras + "-2").
    """
    ocupados = set(ocupados) | USERNAMES_RESERVADOS
    if base not in ocupados:
        return base
    n = 2
    while True:
        sufixo = f"-{n}"
        candidato = base[: USERNAME_MAX - len(sufixo)].rstrip("-") + sufixo
        if candidato not in ocupados:
            return candidato
        n += 1


async def username_disponivel(db, username: str) -> bool:
    """True se nenhum usuário usa este username (e ele não é reservado)."""
    if not username_valido(username) or username in USERNAMES_RESERVADOS:
        return False
    return await db.usuarios.find_one({"username": username}, {"_id": 1}) is None


async def gerar_username_unico(db, nome: Optional[str]) -> str:
    """Username único para um usuário novo, a partir do nome.

    Uma única consulta traz todos os usernames que começam com a base
    (`base` e `base-N`); a escolha do sufixo é feita em memória. O índice
    único é a garantia final contra corridas entre a consulta e o insert.
    """
    base = gerar_username_base(nome)
    cursor = db.usuarios.find(
        {"username": {"$regex": f"^{re.escape(base)}(-\\d+)?$"}},
        {"username": 1},
    )
    ocupados = [doc["username"] for doc in await cursor.to_list(length=None) if doc.get("username")]
    return escolher_username_livre(base, ocupados)


async def preencher_usernames(db) -> int:
    """Backfill: todo usuário sem `username` recebe um gerado do `nome`.

    Sequencial de propósito: cada atribuição já é vista pela consulta do
    próximo (dois "João Silva" viram joao-silva e joao-silva-2). Idempotente;
    devolve quantos documentos foram preenchidos.
    """
    # `{"username": None}` casa tanto campo ausente quanto null.
    cursor = db.usuarios.find({"username": None}, {"nome": 1})
    pendentes = await cursor.to_list(length=None)
    preenchidos = 0
    for doc in pendentes:
        username = await gerar_username_unico(db, doc.get("nome"))
        resultado = await db.usuarios.update_one(
            {"_id": doc["_id"], "username": None},
            {"$set": {"username": username}},
        )
        preenchidos += resultado.modified_count
    return preenchidos
