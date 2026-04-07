"""
Controller de candidatura. Valida o projeto, monta e dispara um e-mail 
via SMTP padrão para o professor anexando o currículo.
"""

import os
import smtplib
import asyncio
from email.message import EmailMessage
from fastapi import HTTPException
from bson import ObjectId
from database.connection import Database

async def enviar_candidatura(
    projeto_id: str, 
    email_aluno: str, 
    curriculo_bytes: bytes, 
    curriculo_filename: str, 
    curriculo_content_type: str
):
    try:
        obj_id = ObjectId(projeto_id)
    except Exception:
        raise HTTPException(status_code=400, detail="ID de projeto inválido")

    db = Database.get_db()
    projeto = await db.projetos.find_one({"_id": obj_id})

    if not projeto:
        raise HTTPException(status_code=404, detail="Projeto não encontrado")

    email_professor = projeto.get("email_professor")
    if not email_professor:
        raise HTTPException(status_code=400, detail="Este projeto não possui um contato de professor configurado.")

    titulo_projeto = projeto.get("titulo", "Projeto Acadêmico")
    nome_professor = projeto.get("nome_professor", "Professor(a)")

    email_remetente = os.getenv("EMAIL_REMETENTE")
    email_senha = os.getenv("EMAIL_SENHA_APP")

    if not email_remetente or not email_senha:
        print("⚠️ Email não configurado no .env")
        raise HTTPException(status_code=500, detail="Configuração de email ausente no servidor")

    # Criar mensagem
    msg = EmailMessage()
    msg['Subject'] = f"Nova Candidatura: {titulo_projeto}"
    msg['From'] = email_remetente
    msg['To'] = email_professor
    
    corpo = (
        f"Olá, {nome_professor}.\n\n"
        f"Você recebeu uma nova candidatura para o projeto '{titulo_projeto}'.\n"
        f"E-mail de contato do candidato: {email_aluno}\n\n"
        f"O currículo do candidato foi anexado a esta mensagem.\n\n"
        f"Atenciosamente,\nPlataforma UniResu Connect"
    )
    msg.set_content(corpo)

    # Anexar arquivo
    try:
        maintype, subtype = curriculo_content_type.split("/", 1)
    except ValueError:
        maintype, subtype = "application", "octet-stream"

    msg.add_attachment(
        curriculo_bytes,
        maintype=maintype,
        subtype=subtype,
        filename=curriculo_filename
    )

    # Disparo assíncrono envelopado
    try:
        await asyncio.to_thread(_enviar_smtp, msg, email_remetente, email_senha)
    except Exception as e:
        print(f"❌ Erro ao enviar email SMTP: {e}")
        raise HTTPException(status_code=500, detail="Falha ao tentar enviar o email. O servidor SMTP pode estar indisponível.")

    return {"status": "success", "message": "Candidatura enviada com sucesso!"}

def _enviar_smtp(msg: EmailMessage, remetente: str, senha: str):
    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
        server.login(remetente, senha)
        server.send_message(msg)
