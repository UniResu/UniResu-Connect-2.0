"""
Rotas de usuários — registro e listagem pública de perfis.

Login foi movido para auth_routes.py para centralizar autenticação.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from typing import List
from models.usuario_model import UsuarioCreate, UsuarioResponse, PerfilPublicoResponse
from controllers.usuario_controller import registrar_usuario_controller
from controllers.perfil_controller import formatar_perfil_publico
from auth.autenticacao import get_usuario_atual
from database.connection import Database

router = APIRouter()


@router.get("/usuarios", response_model=List[PerfilPublicoResponse])
async def get_usuarios(_usuario: dict = Depends(get_usuario_atual)):
    """Lista perfis públicos dos usuários (requer login).

    Devolve só o que é público (sem e-mail, tokens ou senha): a listagem
    antiga expunha o e-mail de todo mundo para qualquer visitante.
    """
    db = Database.get_db()

    try:
        cursor = db.usuarios.find({"ativo": {"$ne": False}, "sistema": {"$ne": True}})
        lista_docs = await cursor.to_list(length=100)
        return [formatar_perfil_publico(doc) for doc in lista_docs]
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
