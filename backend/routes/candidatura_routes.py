from fastapi import APIRouter, Form, File, UploadFile, HTTPException
from controllers.candidatura_controller import enviar_candidatura

router = APIRouter()

@router.post("/projetos/{id}/candidatar")
async def candidatar_projeto(
    id: str,
    email: str = Form(...),
    curriculo: UploadFile = File(...)
):
    """
    Recebe os dados da candidatura (e-mail do aluno e o currículo em PDF/DOCX)
    via formulário multipart e envia por e-mail para o professor responsável.
    """
    
    if not curriculo.filename:
        raise HTTPException(status_code=400, detail="Arquivo não selecionado")
        
    conteudo = await curriculo.read()
    
    # Limita tamanho para ~5MB por precaução do SMTP (Gmail aceita até 25MB)
    if len(conteudo) > 5 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="O currículo deve ter no máximo 5MB")
        
    return await enviar_candidatura(
        projeto_id=id,
        email_aluno=email,
        curriculo_bytes=conteudo,
        curriculo_filename=curriculo.filename,
        curriculo_content_type=curriculo.content_type or "application/octet-stream"
    )
