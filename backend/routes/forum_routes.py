"""
Rotas do fórum — tópicos e respostas.

Rotas protegidas usam Depends(get_usuario_atual) para autenticação.
"""

from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, status
from typing import List, Dict, Any
from bson import ObjectId
from database.connection import Database
from models.forum_model import TopicoCreate, TopicoResponse, RespostaCreate
from auth.autenticacao import get_usuario_atual

router = APIRouter()


def formatar_topico(doc: Dict[str, Any]) -> Dict[str, Any]:
    """Converte _id para string 'id'."""
    if doc is None:
        return None
    if "_id" in doc:
        doc["id"] = str(doc["_id"])
        del doc["_id"]
    # Formatar _id das respostas também
    if "respostas" in doc:
        for resposta in doc["respostas"]:
            if "_id" in resposta:
                resposta["_id"] = str(resposta["_id"])
    return doc


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
        "autor_email": usuario_logado["email"],
        "data_criacao": datetime.now(timezone.utc),
        "visualizacoes": 0,
        "respostas": [],
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


@router.post("/forum/topicos/{topico_id}/responder", response_model=TopicoResponse)
async def adicionar_resposta(
    topico_id: str,
    resposta: RespostaCreate,
    usuario_logado: dict = Depends(get_usuario_atual),
):
    """Adiciona uma resposta a um tópico existente (requer autenticação)."""
    db = Database.get_db()

    nova_resposta_doc = {
        "_id": ObjectId(),
        "conteudo": resposta.conteudo,
        "autor_email": usuario_logado["email"],
        "data_postagem": datetime.now(timezone.utc),
    }

    try:
        update_result = await db.topicos_forum.update_one(
            {"_id": ObjectId(topico_id)},
            {"$push": {"respostas": nova_resposta_doc}},
        )

        if update_result.matched_count == 0:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Tópico não encontrado.",
            )

        topico_atualizado = await db.topicos_forum.find_one(
            {"_id": ObjectId(topico_id)}
        )
        return formatar_topico(topico_atualizado)

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro ao adicionar resposta: {e}",
        )