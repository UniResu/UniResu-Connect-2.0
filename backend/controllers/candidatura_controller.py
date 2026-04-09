"""
Controller de candidatura. Valida o projeto, monta e dispara um e-mail
via SMTP padrão para o professor anexando o currículo.

O envio de e-mail é isolado: qualquer falha SMTP (credenciais inválidas,
bloqueio, timeout) é apenas registrada em log e NÃO interrompe a
candidatura — o aluno sempre recebe a confirmação de sucesso.
"""

import os
import smtplib
import asyncio
import logging
from email.message import EmailMessage
from fastapi import HTTPException
from bson import ObjectId
from database.connection import Database

logger = logging.getLogger(__name__)

async def enviar_candidatura(
    projeto_id: str,
    email_aluno: str,
    curriculo_bytes: bytes,
    curriculo_filename: str,
    curriculo_content_type: str,
    usuario_atual: dict
):
    if not usuario_atual:
        raise HTTPException(status_code=401, detail="Usuário não autenticado.")
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

    # Dispara o e-mail de forma totalmente isolada. Qualquer falha é
    # capturada aqui dentro — nunca propaga para o cliente.
    email_enviado = await _tentar_enviar_email(
        email_professor=email_professor,
        email_aluno=email_aluno,
        titulo_projeto=titulo_projeto,
        nome_professor=nome_professor,
        curriculo_bytes=curriculo_bytes,
        curriculo_filename=curriculo_filename,
        curriculo_content_type=curriculo_content_type,
    )

    return {
        "status": "success",
        "message": "Candidatura enviada com sucesso!",
        "email_enviado": email_enviado,
    }


async def _tentar_enviar_email(
    email_professor: str,
    email_aluno: str,
    titulo_projeto: str,
    nome_professor: str,
    curriculo_bytes: bytes,
    curriculo_filename: str,
    curriculo_content_type: str,
) -> bool:
    """
    Tenta enviar o e-mail de notificação ao professor. Nunca levanta
    exceção: em caso de erro apenas registra no log e devolve False.
    """
    try:
        email_remetente = os.getenv("EMAIL_REMETENTE")
        email_senha = os.getenv("EMAIL_SENHA_APP")

        if not email_remetente or not email_senha:
            logger.warning(
                "Credenciais de e-mail ausentes (EMAIL_REMETENTE/EMAIL_SENHA_APP). "
                "Candidatura confirmada sem envio de e-mail."
            )
            return False

        msg = EmailMessage()
        msg['Subject'] = f"Nova Candidatura: {titulo_projeto}"
        msg['From'] = email_remetente
        msg['To'] = email_professor
        msg.set_content(
            f"Olá, {nome_professor}.\n\n"
            f"Você recebeu uma nova candidatura para o projeto '{titulo_projeto}'.\n"
            f"E-mail de contato do candidato: {email_aluno}\n\n"
            f"O currículo do candidato foi anexado a esta mensagem.\n\n"
            f"Atenciosamente,\nPlataforma UniResu Connect"
        )

        try:
            maintype, subtype = curriculo_content_type.split("/", 1)
        except ValueError:
            maintype, subtype = "application", "octet-stream"

        msg.add_attachment(
            curriculo_bytes,
            maintype=maintype,
            subtype=subtype,
            filename=curriculo_filename,
        )

        await asyncio.to_thread(_enviar_smtp, msg, email_remetente, email_senha)
        logger.info("E-mail de candidatura enviado para %s", email_professor)
        return True

    except Exception as e:
        # Falha de SMTP, autenticação, rede, etc. Apenas registra e segue.
        logger.error(
            "Falha ao enviar e-mail de candidatura (candidatura confirmada mesmo assim): %s",
            e,
            exc_info=True,
        )
        return False


def _enviar_smtp(msg: EmailMessage, remetente: str, senha: str):
    with smtplib.SMTP_SSL("smtp.gmail.com", 465, timeout=15) as server:
        server.login(remetente, senha)
        server.send_message(msg)
