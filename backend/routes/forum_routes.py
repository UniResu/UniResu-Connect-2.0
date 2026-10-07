"""
Rotas do fórum — tópicos (perguntas) com reações (Like/Dislike).
Comentários/respostas foram removidos conforme nova regra de negócio.

Privacidade: nenhuma resposta desta API contém e-mail. O autor aparece como
`autor_username` + `autor_nome`, resolvidos a partir de `autor_id` com UMA
consulta em lote na collection `usuarios` (ver `anexar_autores`).

Rotas protegidas usam Depends(get_usuario_atual) para autenticação.
"""

from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, status
from typing import List, Dict, Any, Optional
from bson import ObjectId
from pymongo import ReturnDocument
from database.connection import Database
from models.forum_model import TopicoCreate, TopicoUpdate, TopicoResponse
from auth.autenticacao import get_usuario_atual

router = APIRouter()

# Rótulos de autor quando `autor_id` não aponta para um usuário existente
# (tópicos legados, só com e-mail, ou conta apagada).
AUTOR_DESCONHECIDO_USERNAME = "usuario"
AUTOR_DESCONHECIDO_NOME = "Usuário"


# ── Helpers ─────────────────────────────────────────────────────────────────

def _lista_de_ids(valor: Any) -> List[str]:
    """Docs legados guardavam `likes: 0`; hoje é lista de IDs de usuários."""
    if not isinstance(valor, list):
        return []
    return [str(v) for v in valor]


def formatar_topico(doc: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Converte _id para string 'id' e remove o que não pode sair da API."""
    if doc is None:
        return None
    doc = dict(doc)
    if "_id" in doc:
        doc["id"] = str(doc["_id"])
        del doc["_id"]
    # Privacidade: o e-mail fica no banco (checagem de autoria legada) e só lá.
    doc.pop("autor_email", None)
    doc["likes"] = _lista_de_ids(doc.get("likes"))
    doc["dislikes"] = _lista_de_ids(doc.get("dislikes"))
    doc.setdefault("autor_username", AUTOR_DESCONHECIDO_USERNAME)
    doc.setdefault("autor_nome", AUTOR_DESCONHECIDO_NOME)
    return doc


def nome_de_exibicao(usuario: Dict[str, Any]) -> str:
    return usuario.get("nome_social") or usuario.get("nome") or AUTOR_DESCONHECIDO_NOME


async def anexar_autores(db, docs: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Preenche `autor_username`/`autor_nome` em cada tópico, in place.

    Uma única `find` com `$in` sobre os `autor_id` válidos (projeção mínima:
    username, nome, nome_social). Quem não for encontrado recebe os rótulos
    de autor desconhecido — nunca o e-mail.
    """
    ids = set()
    for doc in docs:
        autor_id = doc.get("autor_id")
        if autor_id and ObjectId.is_valid(str(autor_id)):
            ids.add(ObjectId(str(autor_id)))

    autores: Dict[str, Dict[str, Any]] = {}
    if ids:
        cursor = db.usuarios.find(
            {"_id": {"$in": list(ids)}},
            {"username": 1, "nome": 1, "nome_social": 1},
        )
        for usuario in await cursor.to_list(length=len(ids)):
            autores[str(usuario["_id"])] = usuario

    for doc in docs:
        usuario = autores.get(str(doc.get("autor_id") or ""))
        if usuario:
            doc["autor_username"] = usuario.get("username") or AUTOR_DESCONHECIDO_USERNAME
            doc["autor_nome"] = nome_de_exibicao(usuario)
        else:
            doc["autor_username"] = AUTOR_DESCONHECIDO_USERNAME
            doc["autor_nome"] = AUTOR_DESCONHECIDO_NOME
    return docs


async def responder_topico(db, doc: Dict[str, Any]) -> Dict[str, Any]:
    """Resposta de um único tópico: resolve o autor e formata."""
    await anexar_autores(db, [doc])
    return formatar_topico(doc)


def extrair_id_usuario(usuario_logado: Any) -> str:
    """Obtém o ID do usuário autenticado de forma segura.

    Por que: `get_usuario_atual` (em auth/autenticacao.py) já normaliza o
    documento convertendo `_id` → `id` (string) e removendo `_id`. Documentos
    crus vindos direto do Mongo, porém, têm apenas `_id` (ObjectId). Esta
    função cobre ambos os formatos e também o caso de objeto com atributos,
    evitando KeyError/AttributeError em runtime.
    """
    if usuario_logado is None:
        return ""
    # Caso 1: dict no formato já normalizado pelo dependency de auth
    if isinstance(usuario_logado, dict):
        valor = usuario_logado.get("id") or usuario_logado.get("_id")
        return str(valor) if valor is not None else ""
    # Caso 2: objeto com atributos (modelo Pydantic, etc.)
    valor = getattr(usuario_logado, "id", None) or getattr(usuario_logado, "_id", None)
    return str(valor) if valor is not None else ""


def extrair_email_usuario(usuario_logado: Any) -> str:
    """Obtém o email do usuário autenticado, tolerando dict ou objeto.

    Usado SOMENTE na checagem de autoria de documentos legados (que só têm
    `autor_email`); nunca entra em resposta.
    """
    if usuario_logado is None:
        return ""
    if isinstance(usuario_logado, dict):
        return usuario_logado.get("email", "") or ""
    return getattr(usuario_logado, "email", "") or ""


def eh_autor(topico: Dict[str, Any], usuario_logado: Any) -> bool:
    """Autoria por `autor_id`; e-mail só como fallback de docs legados."""
    id_logado = extrair_id_usuario(usuario_logado)
    email_logado = extrair_email_usuario(usuario_logado)
    return bool(
        (id_logado and str(topico.get("autor_id", "")) == id_logado)
        or (email_logado and topico.get("autor_email") == email_logado)
    )


def _object_id(topico_id: str) -> ObjectId:
    try:
        return ObjectId(topico_id)
    except Exception:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="ID inválido.")


# ── Rotas ───────────────────────────────────────────────────────────────────

@router.get("/forum/topicos", response_model=List[TopicoResponse])
async def listar_topicos():
    """Lista todos os tópicos do fórum (rota pública)."""
    db = Database.get_db()
    try:
        cursor = db.topicos_forum.find({}).sort("data_criacao", -1)
        lista_docs = await cursor.to_list(length=100)
        await anexar_autores(db, lista_docs)
        return [formatar_topico(doc) for doc in lista_docs]
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro ao listar tópicos: {e}",
        )


@router.get("/forum/topicos/{topico_id}", response_model=TopicoResponse)
async def obter_topico(topico_id: str):
    """Devolve um tópico e conta uma visualização (rota pública).

    O `$inc` é atômico no servidor: duas aberturas simultâneas somam 2.
    """
    db = Database.get_db()
    oid = _object_id(topico_id)
    topico = await db.topicos_forum.find_one_and_update(
        {"_id": oid},
        {"$inc": {"visualizacoes": 1}},
        return_document=ReturnDocument.AFTER,
    )
    if not topico:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tópico não encontrado.")
    return await responder_topico(db, topico)


@router.post(
    "/forum/topicos",
    response_model=TopicoResponse,
    status_code=status.HTTP_201_CREATED,
)
async def criar_topico(
    topico: TopicoCreate,
    usuario_logado: dict = Depends(get_usuario_atual),
):
    """Cria um novo tópico no fórum (requer autenticação)."""
    db = Database.get_db()

    # Só `autor_id`: o autor é resolvido na leitura, e o e-mail não é gravado
    # no tópico (nada a vazar).
    novo_topico_doc = {
        "titulo": topico.titulo,
        "conteudo_original": topico.conteudo,
        "autor_id": extrair_id_usuario(usuario_logado),
        "data_criacao": datetime.now(timezone.utc),
        "visualizacoes": 0,
        # Reações: listas de IDs de usuários para garantir 1 voto por usuário
        "likes": [],
        "dislikes": [],
    }

    try:
        result = await db.topicos_forum.insert_one(novo_topico_doc)
        topico_criado = await db.topicos_forum.find_one({"_id": result.inserted_id})
        if not topico_criado:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Erro ao criar tópico.",
            )
        return await responder_topico(db, topico_criado)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro ao criar tópico: {e}",
        )


@router.patch("/forum/topicos/{topico_id}", response_model=TopicoResponse)
async def editar_topico(
    topico_id: str,
    dados: TopicoUpdate,
    usuario_logado: dict = Depends(get_usuario_atual),
):
    """Edita título e/ou conteúdo de um tópico. Apenas o autor pode editar."""
    db = Database.get_db()
    oid = _object_id(topico_id)

    topico = await db.topicos_forum.find_one({"_id": oid})
    if not topico:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tópico não encontrado.")

    if not eh_autor(topico, usuario_logado):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Apenas o autor pode editar este tópico.",
        )

    campos_para_atualizar = {}
    if dados.titulo is not None:
        campos_para_atualizar["titulo"] = dados.titulo
    if dados.conteudo is not None:
        campos_para_atualizar["conteudo_original"] = dados.conteudo

    if not campos_para_atualizar:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Nenhum campo para atualizar.")

    await db.topicos_forum.update_one({"_id": oid}, {"$set": campos_para_atualizar})

    topico_atualizado = await db.topicos_forum.find_one({"_id": oid})
    return await responder_topico(db, topico_atualizado)


@router.delete("/forum/topicos/{topico_id}", status_code=status.HTTP_204_NO_CONTENT)
async def excluir_topico(
    topico_id: str,
    usuario_logado: dict = Depends(get_usuario_atual),
):
    """Exclui um tópico. Apenas o autor pode excluir."""
    db = Database.get_db()
    oid = _object_id(topico_id)

    topico = await db.topicos_forum.find_one({"_id": oid})
    if not topico:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tópico não encontrado.")

    if not eh_autor(topico, usuario_logado):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Apenas o autor pode excluir este tópico.",
        )

    await db.topicos_forum.delete_one({"_id": oid})


@router.post("/forum/topicos/{topico_id}/reagir", response_model=TopicoResponse)
async def reagir_topico(
    topico_id: str,
    # Espera JSON: { "tipo": "like" } ou { "tipo": "dislike" }
    payload: dict,
    usuario_logado: dict = Depends(get_usuario_atual),
):
    """
    Registra ou remove uma reação (like/dislike) de um tópico.
    - Se o usuário já reagiu com o mesmo tipo → remove (toggle off).
    - Se o usuário reagiu com o tipo oposto → troca de reação.
    - Um usuário não pode dar like e dislike ao mesmo tempo.
    """
    db = Database.get_db()

    tipo = payload.get("tipo")
    if tipo not in ("like", "dislike"):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Tipo deve ser 'like' ou 'dislike'.")

    usuario_id = extrair_id_usuario(usuario_logado)
    if not usuario_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Não foi possível identificar o usuário autenticado.",
        )

    oid = _object_id(topico_id)
    topico = await db.topicos_forum.find_one({"_id": oid})
    if not topico:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tópico não encontrado.")

    likes = _lista_de_ids(topico.get("likes"))
    dislikes = _lista_de_ids(topico.get("dislikes"))

    lista_atual = likes if tipo == "like" else dislikes
    lista_oposta = dislikes if tipo == "like" else likes

    # Remove do oposto caso exista
    if usuario_id in lista_oposta:
        lista_oposta.remove(usuario_id)

    # Toggle no atual
    if usuario_id in lista_atual:
        lista_atual.remove(usuario_id)
    else:
        lista_atual.append(usuario_id)

    await db.topicos_forum.update_one(
        {"_id": oid},
        {"$set": {"likes": likes, "dislikes": dislikes}},
    )

    topico_atualizado = await db.topicos_forum.find_one({"_id": oid})
    return await responder_topico(db, topico_atualizado)
