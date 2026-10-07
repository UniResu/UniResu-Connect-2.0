from typing import List

from fastapi import APIRouter, Depends

from controllers.candidatura_controller import (
    enviar_candidatura,
    listar_candidaturas_do_aluno,
)
from models.candidatura_model import CandidaturaCreate, CandidaturaResponse
from auth.autenticacao import get_usuario_atual, get_usuario_com_perfil_completo

router = APIRouter()


@router.post("/projetos/{id}/candidatar")
async def candidatar_projeto(
    id: str,
    dados: CandidaturaCreate,
    usuario_atual: dict = Depends(get_usuario_com_perfil_completo),
):
    """
    Recebe a candidatura com carta de intenção (JSON), persiste no MongoDB
    e envia a carta no corpo do e-mail ao coordenador do projeto, com
    reply-to no e-mail do aluno e cópia de confirmação para o aluno.
    Bloqueia candidaturas duplicadas e aplica rate limit por usuário.
    """
    return await enviar_candidatura(projeto_id=id, dados=dados, usuario_atual=usuario_atual)


@router.get("/candidaturas/me", response_model=List[CandidaturaResponse])
async def listar_minhas_candidaturas(
    usuario_atual: dict = Depends(get_usuario_atual),
):
    """
    Lista todas as candidaturas enviadas pelo aluno autenticado.

    Cada item traz os dados desnormalizados do projeto (título e professor)
    para que o frontend renderize a página de candidaturas sem precisar
    fazer chamadas adicionais por projeto.
    """
    return await listar_candidaturas_do_aluno(usuario_atual)
