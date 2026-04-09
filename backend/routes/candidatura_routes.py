from typing import List

from fastapi import APIRouter, Form, File, UploadFile, HTTPException, Depends

from controllers.candidatura_controller import (
    enviar_candidatura,
    listar_candidaturas_do_aluno,
)
from models.candidatura_model import CandidaturaResponse
from auth.autenticacao import get_usuario_atual

router = APIRouter()


@router.post("/projetos/{id}/candidatar")
async def candidatar_projeto(
    id: str,
    email: str = Form(...),
    curriculo: UploadFile = File(...),
    usuario_atual: dict = Depends(get_usuario_atual)
):
    """
    Recebe os dados da candidatura (e-mail do aluno e o currículo em PDF/DOCX)
    via formulário multipart, persiste em MongoDB e envia por e-mail para o
    professor responsável. Bloqueia candidaturas duplicadas ao mesmo projeto.
    """

    if not curriculo.filename:
        raise HTTPException(status_code=400, detail="Arquivo não selecionado")

    conteudo = await curriculo.read()

    # Limita tamanho para ~5MB por precaução do Resend (limite de payload).
    if len(conteudo) > 5 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="O currículo deve ter no máximo 5MB")

    return await enviar_candidatura(
        projeto_id=id,
        email_aluno=email,
        curriculo_bytes=conteudo,
        curriculo_filename=curriculo.filename,
        curriculo_content_type=curriculo.content_type or "application/octet-stream",
        usuario_atual=usuario_atual
    )


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
