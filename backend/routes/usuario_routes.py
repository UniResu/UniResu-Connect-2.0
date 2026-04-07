"""
Rotas de usuários — registro e listagem.

Login foi movido para auth_routes.py para centralizar autenticação.
"""

from fastapi import APIRouter, HTTPException, status
from typing import List
from models.usuario_model import UsuarioCreate, UsuarioResponse
from controllers.usuario_controller import registrar_usuario_controller
from database.connection import Database

router = APIRouter()


@router.get("/usuarios", response_model=List[UsuarioResponse])
async def get_usuarios():
    """Lista todos os usuários cadastrados."""
    db = Database.get_db()

    try:
        cursor = db.usuarios.find({})
        lista_docs = await cursor.to_list(length=100)
        resultado = []
        for doc in lista_docs:
            doc["id"] = str(doc["_id"])
            del doc["_id"]
            doc.pop("senha_hash", None)
            resultado.append(doc)
        return resultado
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro ao buscar usuários: {str(e)}",
        )


@router.post(
    "/usuarios/registrar",
    response_model=UsuarioResponse,
    status_code=status.HTTP_201_CREATED,
)
async def registrar_usuario_route(user: UsuarioCreate):
    """Registra um novo usuário."""
    return await registrar_usuario_controller(user)