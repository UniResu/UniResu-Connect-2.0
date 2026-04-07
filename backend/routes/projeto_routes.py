"""
Rotas de projetos — busca pública + CRUD protegido para professores/pesquisadores.
"""

from fastapi import APIRouter, Query, Depends, HTTPException, status
from typing import List, Optional
from controllers.projeto_controller import (
    buscar_projetos_controller,
    criar_projeto_controller,
    listar_meus_projetos,
    editar_projeto_controller,
    deletar_projeto_controller,
)
from models.projeto_model import ProjetoResponse, ProjetoCreate
from auth.autenticacao import get_usuario_atual

router = APIRouter()

PAPEIS_PERMITIDOS = ("professor", "pesquisador")


def verificar_papel(usuario: dict):
    """Garante que o usuário é professor ou pesquisador."""
    if usuario.get("papel") not in PAPEIS_PERMITIDOS:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Apenas professores e pesquisadores podem gerenciar projetos.",
        )


# ── Busca pública ──

@router.get("/projetos/buscar", response_model=List[ProjetoResponse])
async def buscar_projetos_route(
    q: Optional[str] = None,
    local: Optional[str] = None,
    area: Optional[str] = None,
    remoto: bool = False,
    tipos: Optional[str] = Query(None),
    last_id: Optional[str] = Query(None, description="ID do último item (paginação por cursor)"),
    page_size: int = Query(20, ge=1, le=50, description="Itens por página"),
):
    """Busca projetos acadêmicos com filtros e paginação."""
    return await buscar_projetos_controller(
        q=q,
        local=local,
        area=area,
        remoto=remoto,
        tipos=tipos,
        last_id=last_id,
        page_size=page_size,
    )


# ── CRUD protegido ──

@router.get("/projetos/meus", response_model=List[ProjetoResponse])
async def meus_projetos(usuario: dict = Depends(get_usuario_atual)):
    """Lista os projetos do professor/pesquisador logado."""
    verificar_papel(usuario)
    return await listar_meus_projetos(usuario)


@router.post("/projetos", response_model=ProjetoResponse, status_code=status.HTTP_201_CREATED)
async def criar_projeto(dados: ProjetoCreate, usuario: dict = Depends(get_usuario_atual)):
    """Cria um novo projeto acadêmico."""
    verificar_papel(usuario)
    return await criar_projeto_controller(dados.model_dump(), usuario)


@router.put("/projetos/{projeto_id}", response_model=ProjetoResponse)
async def editar_projeto(projeto_id: str, dados: ProjetoCreate, usuario: dict = Depends(get_usuario_atual)):
    """Edita um projeto existente (somente o autor)."""
    verificar_papel(usuario)
    try:
        resultado = await editar_projeto_controller(projeto_id, dados.model_dump(), usuario)
    except PermissionError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))

    if resultado is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Projeto não encontrado.")
    return resultado


@router.delete("/projetos/{projeto_id}")
async def deletar_projeto(projeto_id: str, usuario: dict = Depends(get_usuario_atual)):
    """Exclui um projeto (somente o autor)."""
    verificar_papel(usuario)
    try:
        deletado = await deletar_projeto_controller(projeto_id, usuario)
    except PermissionError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))

    if not deletado:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Projeto não encontrado.")
    return {"detail": "Projeto excluído com sucesso."}