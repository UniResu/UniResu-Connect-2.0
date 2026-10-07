"""
Rotas de projetos — busca pública + CRUD protegido para professores/pesquisadores.
"""

from fastapi import APIRouter, Query, Depends, HTTPException, status
from typing import List, Literal, Optional
from controllers.projeto_controller import (
    buscar_projetos_controller,
    listar_unidades_controller,
    listar_instituicoes_controller,
    listar_filtros_controller,
    status_fontes_controller,
    criar_projeto_controller,
    listar_meus_projetos,
    editar_projeto_controller,
    deletar_projeto_controller,
)
from models.projeto_model import (
    ProjetoResponse,
    ProjetoCreate,
    ProjetoPublicoResponse,
    FontesStatusResponse,
    FiltrosResponse,
)
from auth.autenticacao import get_usuario_atual, get_usuario_com_perfil_completo

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

@router.get("/projetos/buscar", response_model=List[ProjetoPublicoResponse])
async def buscar_projetos_route(
    q: Optional[str] = Query(None, max_length=200),
    local: Optional[str] = None,
    area: Optional[str] = None,
    remoto: bool = False,
    tipos: Optional[str] = Query(None),
    modulo: Optional[Literal["pesquisa", "extensao"]] = Query(None, description="Pesquisa ou extensão"),
    tipo_sigaa: Optional[Literal["pesquisa", "extensao"]] = Query(None, deprecated=True,
                                                                  description="Nome antigo de `modulo`"),
    unidade: Optional[str] = Query(None, max_length=300, description="Unidade/departamento"),
    instituicao: Optional[str] = Query(None, max_length=200, description="Instituição (sigla ou nome; ex.: UNIR, UNIRIO)"),
    incluir_inativos: bool = Query(False, description="Inclui projetos inativos/finalizados"),
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
        modulo=modulo or tipo_sigaa,
        unidade=unidade,
        instituicao=instituicao,
        incluir_inativos=incluir_inativos,
        last_id=last_id,
        page_size=page_size,
    )


@router.get("/projetos/unidades", response_model=List[str])
async def listar_unidades_route(
    modulo: Optional[Literal["pesquisa", "extensao"]] = None,
    tipo_sigaa: Optional[Literal["pesquisa", "extensao"]] = Query(None, deprecated=True),
    instituicao: Optional[str] = Query(None, max_length=200),
):
    """Unidades/departamentos com projetos ativos (opções do filtro)."""
    return await listar_unidades_controller(modulo or tipo_sigaa, instituicao)


@router.get("/projetos/instituicoes", response_model=List[str])
async def listar_instituicoes_route():
    """Instituições com projetos ativos (opções do filtro)."""
    return await listar_instituicoes_controller()


@router.get("/projetos/filtros", response_model=FiltrosResponse)
async def listar_filtros_route():
    """Opções de filtro agrupadas: instituição > unidades/departamentos, com contagens."""
    return await listar_filtros_controller()


@router.get("/projetos/fontes/status", response_model=FontesStatusResponse)
@router.get("/projetos/sigaa/status", response_model=FontesStatusResponse, deprecated=True)
async def status_fontes_route(usuario: dict = Depends(get_usuario_atual)):
    """Data da última atualização dos dados de cada fonte externa (SIGAA/UNIR, UNIRIO).

    Só para professores e pesquisadores logados: quando a base foi atualizada
    é informação interna da equipe, não aparece na aba pública.
    """
    verificar_papel(usuario)
    return await status_fontes_controller()


# ── CRUD protegido ──

@router.get("/projetos/meus", response_model=List[ProjetoResponse])
async def meus_projetos(usuario: dict = Depends(get_usuario_com_perfil_completo)):
    """Lista os projetos do professor/pesquisador logado."""
    verificar_papel(usuario)
    return await listar_meus_projetos(usuario)


@router.post("/projetos", response_model=ProjetoResponse, status_code=status.HTTP_201_CREATED)
async def criar_projeto(dados: ProjetoCreate, usuario: dict = Depends(get_usuario_com_perfil_completo)):
    """Cria um novo projeto acadêmico."""
    verificar_papel(usuario)
    return await criar_projeto_controller(dados.model_dump(), usuario)


@router.put("/projetos/{projeto_id}", response_model=ProjetoResponse)
async def editar_projeto(projeto_id: str, dados: ProjetoCreate, usuario: dict = Depends(get_usuario_com_perfil_completo)):
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
async def deletar_projeto(projeto_id: str, usuario: dict = Depends(get_usuario_com_perfil_completo)):
    """Exclui um projeto (somente o autor)."""
    verificar_papel(usuario)
    try:
        deletado = await deletar_projeto_controller(projeto_id, usuario)
    except PermissionError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))

    if not deletado:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Projeto não encontrado.")
    return {"detail": "Projeto excluído com sucesso."}