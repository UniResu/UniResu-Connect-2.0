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

import logging
import re
import unicodedata
from typing import Iterable, Iterator, Optional

from pymongo.errors import DuplicateKeyError

logger = logging.getLogger(__name__)

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


def candidatos_username(base: str) -> Iterator[str]:
    """`base`, `base-2`, `base-3`, ... Pura, infinita.

    O sufixo nunca estoura USERNAME_MAX: a base é encurtada para abrir
    espaço (ex.: base de 30 letras → 28 letras + "-2").
    """
    yield base
    n = 2
    while True:
        sufixo = f"-{n}"
        yield base[: USERNAME_MAX - len(sufixo)].rstrip("-") + sufixo
        n += 1


def escolher_username_livre(base: str, ocupados: Iterable[str]) -> str:
    """Primeiro candidato (ver `candidatos_username`) fora de `ocupados`. Pura."""
    ocupados = set(ocupados) | USERNAMES_RESERVADOS
    return next(c for c in candidatos_username(base) if c not in ocupados)


def _prefixo_comum(base: str) -> str:
    """Prefixo que TODOS os candidatos de `base` compartilham.

    Para bases curtas é a própria base; para bases longas, a parte que sobra
    depois do encurtamento feito para caber o sufixo (até "-999"). Sem isso a
    consulta de ocupados não enxergava `<base[:28]>-2` e devolvia o mesmo
    username para o terceiro homônimo com nome comprido.
    """
    return base[: USERNAME_MAX - 4].rstrip("-") if len(base) > USERNAME_MAX - 4 else base


async def username_disponivel(db, username: str) -> bool:
    """True se nenhum usuário usa este username (e ele não é reservado)."""
    if not username_valido(username) or username in USERNAMES_RESERVADOS:
        return False
    return await db.usuarios.find_one({"username": username}, {"_id": 1}) is None


async def gerar_username_unico(db, nome: Optional[str], evitar: Iterable[str] = ()) -> str:
    """Username único para um usuário novo, a partir do nome.

    Uma única consulta traz todos os usernames que começam com o prefixo
    comum dos candidatos; a escolha do sufixo é feita em memória. O índice
    único `uniq_username` é a garantia final contra corridas entre a consulta
    e o insert: quem pegar DuplicateKeyError chama de novo passando o username
    rejeitado em `evitar`.
    """
    base = gerar_username_base(nome)
    cursor = db.usuarios.find(
        {"username": {"$regex": f"^{re.escape(_prefixo_comum(base))}"}},
        {"username": 1},
    )
    ocupados = [doc["username"] for doc in await cursor.to_list(length=None) if doc.get("username")]
    return escolher_username_livre(base, [*ocupados, *evitar])


async def preencher_usernames(db) -> int:
    """Backfill: todo usuário sem `username` recebe um gerado do `nome`.

    Sequencial de propósito: cada atribuição já é vista pela consulta do
    próximo (dois "João Silva" viram joao-silva e joao-silva-2). Idempotente;
    devolve quantos documentos foram preenchidos. Uma colisão com o índice
    único (outro processo preencheu no mesmo instante) tenta o sufixo
    seguinte; qualquer outra falha em um documento não interrompe os demais.
    """
    # `{"username": None}` casa tanto campo ausente quanto null.
    cursor = db.usuarios.find({"username": None}, {"nome": 1})
    pendentes = await cursor.to_list(length=None)
    preenchidos = 0
    for doc in pendentes:
        rejeitados: list[str] = []
        for _ in range(5):
            username = await gerar_username_unico(db, doc.get("nome"), evitar=rejeitados)
            try:
                resultado = await db.usuarios.update_one(
                    {"_id": doc["_id"], "username": None},
                    {"$set": {"username": username}},
                )
            except DuplicateKeyError:
                rejeitados.append(username)
                continue
            except Exception as e:  # um documento ruim não derruba o backfill
                logger.error("Backfill de username falhou para %s: %s", doc["_id"], e)
                break
            preenchidos += resultado.modified_count
            break
    return preenchidos
