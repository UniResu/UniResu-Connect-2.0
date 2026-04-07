"""
Rotas de perfil — visualização e edição de perfis de usuário.

Endpoints:
    GET  /api/perfil           → Perfil do usuário logado
    PATCH /api/perfil          → Atualizar perfil próprio
    GET  /api/perfil/{id}      → Perfil público de outro usuário
"""

from fastapi import APIRouter, Depends
from models.usuario_model import (
    UsuarioResponse,
    PerfilPublicoResponse,
    PerfilUpdate,
)
from controllers.perfil_controller import (
    obter_perfil_controller,
    atualizar_perfil_controller,
    obter_perfil_publico_controller,
)
from auth.autenticacao import get_usuario_atual

router = APIRouter()


@router.get("/perfil", response_model=UsuarioResponse)
async def obter_meu_perfil(
    usuario_logado: dict = Depends(get_usuario_atual),
):
    """Retorna o perfil completo do usuário autenticado."""
    return await obter_perfil_controller(usuario_logado["id"])


@router.patch("/perfil", response_model=UsuarioResponse)
async def atualizar_meu_perfil(
    dados: PerfilUpdate,
    usuario_logado: dict = Depends(get_usuario_atual),
):
    """Atualiza parcialmente o perfil do usuário autenticado.

    Apenas os campos enviados serão atualizados (PATCH semântico).
    Campos de papel (dados_aluno, dados_professor, dados_pesquisador)
    são mesclados com os dados existentes, não substituídos.
    """
    return await atualizar_perfil_controller(usuario_logado["id"], dados)


@router.get("/perfil/{identificador}", response_model=PerfilPublicoResponse)
async def obter_perfil_publico(identificador: str):
    """Retorna o perfil público de um usuário.

    O identificador pode ser:
    - ORCID ID (ex: 0000-0002-1234-5678)
    - ID do usuário (ObjectId)

    Esta rota é pública (não requer autenticação).
    """
    return await obter_perfil_publico_controller(identificador)
