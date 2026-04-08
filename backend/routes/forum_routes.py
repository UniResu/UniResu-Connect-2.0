"""
Rotas do fórum — tópicos com reações (Like/Dislike).
Comentários/respostas foram removidos conforme nova regra de negócio.

Rotas protegidas usam Depends(get_usuario_atual) para autenticação.
"""

from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, status
from typing import List, Dict, Any
from bson import ObjectId
from database.connection import Database
from models.forum_model import TopicoCreate, TopicoUpdate, TopicoResponse
from auth.autenticacao import get_usuario_atual

router = APIRouter()


# ── Helpers ─────────────────────────────────────────────────────────────────

def formatar_topico(doc: Dict[str, Any]) -> Dict[str, Any]:
    """Converte _id para string 'id'."""
    if doc is None:
        return None
    doc = dict(doc)
    if "_id" in doc:
        doc["id"] = str(doc["_id"])
        del doc["_id"]
    return doc


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
    """Obtém o email do usuário autenticado, tolerando dict ou objeto."""
    if usuario_logado is None:
        return ""
    if isinstance(usuario_logado, dict):
        return usuario_logado.get("email", "") or ""
    return getattr(usuario_logado, "email", "") or ""


# ── Rotas ───────────────────────────────────────────────────────────────────

@router.get("/forum/topicos", response_model=List[TopicoResponse])
async def listar_topicos():
    """Lista todos os tópicos do fórum (rota pública)."""
    db = Database.get_db()
    try:
        cursor = db.topicos_forum.find({}).sort("data_criacao", -1)
        lista_docs = await cursor.to_list(length=100)
        return [formatar_topico(doc) for doc in lista_docs]
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro ao listar tópicos: {e}",
        )


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

    novo_topico_doc = {
        "titulo": topico.titulo,
        "conteudo_original": topico.conteudo,
        "autor_email": extrair_email_usuario(usuario_logado),
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
        return formatar_topico(topico_criado)
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

    try:
        topico = await db.topicos_forum.find_one({"_id": ObjectId(topico_id)})
    except Exception:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="ID inválido.")

    if not topico:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tópico não encontrado.")

    # Verificação de autoria — usa autor_email como fallback para documentos legados
    id_logado = extrair_id_usuario(usuario_logado)
    email_logado = extrair_email_usuario(usuario_logado)
    eh_autor = (
        (id_logado and str(topico.get("autor_id", "")) == id_logado)
        or (email_logado and topico.get("autor_email") == email_logado)
    )
    if not eh_autor:
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

    await db.topicos_forum.update_one(
        {"_id": ObjectId(topico_id)},
        {"$set": campos_para_atualizar},
    )

    topico_atualizado = await db.topicos_forum.find_one({"_id": ObjectId(topico_id)})
    return formatar_topico(topico_atualizado)


@router.delete("/forum/topicos/{topico_id}", status_code=status.HTTP_204_NO_CONTENT)
async def excluir_topico(
    topico_id: str,
    usuario_logado: dict = Depends(get_usuario_atual),
):
    """Exclui um tópico. Apenas o autor pode excluir."""
    db = Database.get_db()

    try:
        topico = await db.topicos_forum.find_one({"_id": ObjectId(topico_id)})
    except Exception:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="ID inválido.")

    if not topico:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tópico não encontrado.")

    id_logado = extrair_id_usuario(usuario_logado)
    email_logado = extrair_email_usuario(usuario_logado)
    eh_autor = (
        (id_logado and str(topico.get("autor_id", "")) == id_logado)
        or (email_logado and topico.get("autor_email") == email_logado)
    )
    if not eh_autor:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Apenas o autor pode excluir este tópico.",
        )

    await db.topicos_forum.delete_one({"_id": ObjectId(topico_id)})


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

    try:
        topico = await db.topicos_forum.find_one({"_id": ObjectId(topico_id)})
    except Exception:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="ID inválido.")

    if not topico:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tópico não encontrado.")

    likes = list(topico.get("likes", []))
    dislikes = list(topico.get("dislikes", []))

    oposto = "dislikes" if tipo == "like" else "likes"
    atual = "likes" if tipo == "like" else "dislikes"
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
        {"_id": ObjectId(topico_id)},
        {"$set": {"likes": lista_atual if tipo == "like" else lista_oposta,
                  "dislikes": lista_oposta if tipo == "like" else lista_atual}},
    )

    topico_atualizado = await db.topicos_forum.find_one({"_id": ObjectId(topico_id)})
    return formatar_topico(topico_atualizado)