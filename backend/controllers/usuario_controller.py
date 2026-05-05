"""
Controller de usuários — lógica de negócio para registro e login.

Centraliza hash de senha, verificação e operações de CRUD de usuários.
Usa Motor (async) para todas as operações com o banco.
"""

from typing import Dict, Any
from datetime import datetime, timezone, timedelta
import os
import secrets
import asyncio
import logging

import resend
from fastapi import HTTPException, status
from passlib.context import CryptContext
from database.connection import Database
from models.usuario_model import UsuarioCreate

logger = logging.getLogger(__name__)

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Envio de e-mail agora é feito via API do Resend (domínio uniresu.org
# verificado). EMAIL_REMETENTE é o "from" exibido; EMAIL_SUPORTE recebe
# as respostas dos usuários via reply_to.
EMAIL_REMETENTE = os.getenv("EMAIL_REMETENTE", "UniResu <contato@uniresu.org>")
EMAIL_SUPORTE = os.getenv("EMAIL_SUPORTE", "uniresuconnect@gmail.com")

# A chave da API do Resend já é configurada em candidatura_controller no
# momento da importação; repetimos aqui para garantir que este módulo
# funcione mesmo se for carregado primeiro.
resend.api_key = os.getenv("RESEND_API_KEY")


def hash_password(password: str) -> str:
    """Gera o hash bcrypt de uma senha."""
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verifica se a senha em texto puro corresponde ao hash salvo."""
    return pwd_context.verify(plain_password, hashed_password)


def formatar_usuario(doc: Dict[str, Any]) -> Dict[str, Any]:
    """Converte _id do MongoDB para string 'id' e remove dados sensíveis."""
    if doc is None:
        return None
    if "_id" in doc:
        doc["id"] = str(doc["_id"])
        del doc["_id"]
    doc.pop("senha_hash", None)
    # Remover tokens ORCID internos
    if "orcid" in doc and doc["orcid"]:
        doc["orcid"].pop("access_token", None)
        doc["orcid"].pop("refresh_token", None)
        doc["orcid"].pop("token_expires_at", None)
    return doc


async def registrar_usuario_controller(user: UsuarioCreate) -> Dict[str, Any]:
    """Registra um novo usuário no banco de dados.

    A conta é criada com email_verificado=False. Um token de verificação
    é gerado e enviado por e-mail. O usuário só poderá fazer login após
    confirmar o e-mail.

    Args:
        user: Dados do novo usuário.

    Returns:
        Dicionário com os dados do usuário criado (sem senha).
    """
    db = Database.get_db()

    # Verificar unicidade do email
    usuario_existente = await db.usuarios.find_one({"email": user.email})
    if usuario_existente:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Este email já está cadastrado.",
        )

    # Gerar token de verificação de e-mail
    token_verificacao = secrets.token_urlsafe(48)
    token_verificacao_expira = datetime.now(timezone.utc) + timedelta(hours=24)

    # Construir documento do usuário
    novo_usuario_doc: Dict[str, Any] = {
        "email": user.email,
        "nome": user.nome,
        "papel": user.papel.value,
        "instituicao": user.instituicao,
        "curso": user.curso,
        "interesses": [],
        "habilidades": [],
        "criado_em": datetime.now(timezone.utc),
        "atualizado_em": datetime.now(timezone.utc),
        "ativo": True,
        "email_verificado": False,
        "token_verificacao_email": token_verificacao,
        "token_verificacao_expira": token_verificacao_expira,
    }

    # Hash da senha (opcional — se usando ORCID como método principal)
    if user.senha:
        novo_usuario_doc["senha_hash"] = hash_password(user.senha)

    # Inicializar sub-documento por papel
    if user.papel.value == "aluno":
        novo_usuario_doc["dados_aluno"] = {
            "nivel": "graduacao",
            "semestre": 1,
        }
    elif user.papel.value == "professor":
        novo_usuario_doc["dados_professor"] = {
            "linhas_pesquisa": [],
        }
    elif user.papel.value == "pesquisador":
        novo_usuario_doc["dados_pesquisador"] = {
            "linhas_pesquisa": [],
        }

    try:
        result = await db.usuarios.insert_one(novo_usuario_doc)
        usuario_criado = await db.usuarios.find_one({"_id": result.inserted_id})

        if usuario_criado is None:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Erro ao criar o usuário.",
            )

        # Disparar e-mail de verificação (não bloqueia o response)
        await _enviar_email_verificacao(user.email, user.nome, token_verificacao)

        return formatar_usuario(usuario_criado)

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro interno do servidor: {e}",
        )


async def login_usuario_controller(email: str, senha: str) -> Dict[str, Any]:
    """Valida as credenciais de login por email+senha.

    Bloqueia login se o e-mail não estiver verificado.

    Args:
        email: Email do usuário.
        senha: Senha em texto puro.

    Returns:
        Dicionário com os dados do usuário (sem senha).
    """
    db = Database.get_db()

    usuario = await db.usuarios.find_one({"email": email})
    if usuario is None or not verify_password(senha, usuario.get("senha_hash", "")):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Email ou senha inválidos.",
        )

    # Bloquear login de contas com e-mail não verificado
    if not usuario.get("email_verificado", True):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="E-mail não verificado. Verifique sua caixa de entrada para ativar a conta.",
        )

    # Atualizar último login
    await db.usuarios.update_one(
        {"_id": usuario["_id"]},
        {"$set": {"ultimo_login": datetime.now(timezone.utc)}},
    )

    return formatar_usuario(usuario)

# ═══════════════════════════════════════════
#  Recuperação de Senha
# ═══════════════════════════════════════════

async def solicitar_recuperacao_senha_controller(email: str) -> None:
    db = Database.get_db()
    usuario = await db.usuarios.find_one({"email": email})

    # Retorno silencioso p/ não vazar informações (enumeração de bad actors)
    if not usuario or "senha_hash" not in usuario:
        return

    token = secrets.token_urlsafe(48)
    expiracao = datetime.now(timezone.utc) + timedelta(hours=1)

    await db.usuarios.update_one(
        {"_id": usuario["_id"]},
        {"$set": {
            "reset_token": token,
            "reset_token_expira": expiracao
        }}
    )

    if not resend.api_key:
        logger.warning(
            "RESEND_API_KEY ausente — e-mail de recuperação de senha NÃO enviado."
        )
        return

    base_url = os.getenv("NEXT_PUBLIC_SITE_URL", "https://uniresu.org")
    link = f"{base_url}/resetar-senha?token={token}"

    nome = usuario.get("nome", "Usuário")
    corpo_texto = (
        f"Olá, {nome}.\n\n"
        f"Recebemos uma solicitação para redefinir a senha da sua conta "
        f"na plataforma UniResu Connect.\n"
        f"Para cadastrar uma nova senha, acesse o link abaixo (válido por 1 hora):\n\n"
        f"{link}\n\n"
        f"Se você não solicitou esta recuperação, simplesmente ignore este e-mail.\n\n"
        f"Atenciosamente,\n"
        f"Equipe UniResu Connect"
    )
    corpo_html = (
        f"<p>Olá, {nome}.</p>"
        f"<p>Recebemos uma solicitação para redefinir a senha da sua conta "
        f"na plataforma <strong>UniResu Connect</strong>.</p>"
        f"<p>Para cadastrar uma nova senha, acesse o link abaixo "
        f"(válido por 1 hora):</p>"
        f"<p><a href=\"{link}\">{link}</a></p>"
        f"<p>Se você não solicitou esta recuperação, simplesmente ignore "
        f"este e-mail.</p>"
        f"<p>Atenciosamente,<br><strong>Equipe UniResu Connect</strong></p>"
    )

    params: "resend.Emails.SendParams" = {
        "from": EMAIL_REMETENTE,
        "to": [email],
        "reply_to": EMAIL_SUPORTE,
        "subject": "Recuperação de Senha - UniResu Connect",
        "text": corpo_texto,
        "html": corpo_html,
    }

    try:
        # SDK do Resend é síncrono; rodamos em thread para não bloquear o loop.
        await asyncio.to_thread(resend.Emails.send, params)
    except Exception as e:
        logger.error(
            "Falha ao enviar e-mail de recuperação de senha via Resend: %s",
            e,
            exc_info=True,
        )

# ═══════════════════════════════════════════
#  Verificação de E-mail
# ═══════════════════════════════════════════

async def _enviar_email_verificacao(email: str, nome: str, token: str) -> None:
    """Envia o e-mail de confirmação com link de verificação."""
    if not resend.api_key:
        logger.warning(
            "RESEND_API_KEY ausente — e-mail de verificação NÃO enviado."
        )
        return

    base_url = os.getenv("NEXT_PUBLIC_SITE_URL", "https://uniresu.org")
    link = f"{base_url}/verificar-email?token={token}"

    corpo_texto = (
        f"Olá, {nome}.\n\n"
        f"Bem-vindo(a) à UniResu Connect!\n\n"
        f"Para ativar sua conta, confirme seu e-mail clicando no link abaixo "
        f"(válido por 24 horas):\n\n"
        f"{link}\n\n"
        f"Se você não se cadastrou na plataforma, ignore este e-mail.\n\n"
        f"Atenciosamente,\n"
        f"Equipe UniResu Connect"
    )
    corpo_html = (
        f"<p>Olá, <strong>{nome}</strong>.</p>"
        f"<p>Bem-vindo(a) à <strong>UniResu Connect</strong>!</p>"
        f"<p>Para ativar sua conta, confirme seu e-mail clicando no link abaixo "
        f"(válido por 24 horas):</p>"
        f'<p><a href="{link}" style="display:inline-block;padding:12px 24px;'
        f"background-color:#7c3aed;color:#ffffff;text-decoration:none;"
        f'border-radius:6px;font-weight:bold;">Confirmar meu e-mail</a></p>'
        f"<p style=\"color:#666;font-size:12px;\">Ou copie e cole este link no navegador:<br>"
        f"{link}</p>"
        f"<p>Se você não se cadastrou na plataforma, ignore este e-mail.</p>"
        f"<p>Atenciosamente,<br><strong>Equipe UniResu Connect</strong></p>"
    )

    params: "resend.Emails.SendParams" = {
        "from": EMAIL_REMETENTE,
        "to": [email],
        "reply_to": EMAIL_SUPORTE,
        "subject": "Confirme seu e-mail - UniResu Connect",
        "text": corpo_texto,
        "html": corpo_html,
    }

    try:
        await asyncio.to_thread(resend.Emails.send, params)
        logger.info("E-mail de verificação enviado para %s", email)
    except Exception as e:
        logger.error(
            "Falha ao enviar e-mail de verificação via Resend: %s",
            e,
            exc_info=True,
        )


async def verificar_email_controller(token: str) -> bool:
    """Valida o token de verificação e ativa a conta do usuário.

    Args:
        token: Token recebido via link no e-mail.

    Returns:
        True se a verificação foi bem-sucedida.

    Raises:
        HTTPException 400: Se o token for inválido ou expirado.
    """
    db = Database.get_db()
    agora = datetime.now(timezone.utc)

    usuario = await db.usuarios.find_one({
        "token_verificacao_email": token,
        "token_verificacao_expira": {"$gt": agora},
    })

    if not usuario:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="O link de confirmação é inválido ou expirou.",
        )

    # Ativar a conta e limpar tokens de verificação
    await db.usuarios.update_one(
        {"_id": usuario["_id"]},
        {
            "$set": {
                "email_verificado": True,
                "atualizado_em": agora,
            },
            "$unset": {
                "token_verificacao_email": "",
                "token_verificacao_expira": "",
            },
        },
    )

    return True


async def reenviar_verificacao_controller(email: str) -> None:
    """Reenvia o e-mail de verificação com um novo token.

    Útil caso o token original tenha expirado ou o e-mail não chegou.
    """
    db = Database.get_db()
    usuario = await db.usuarios.find_one({"email": email})

    if not usuario:
        return  # Retorno silencioso (segurança)

    if usuario.get("email_verificado", True):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Este e-mail já foi verificado.",
        )

    # Gerar novo token
    novo_token = secrets.token_urlsafe(48)
    nova_expiracao = datetime.now(timezone.utc) + timedelta(hours=24)

    await db.usuarios.update_one(
        {"_id": usuario["_id"]},
        {"$set": {
            "token_verificacao_email": novo_token,
            "token_verificacao_expira": nova_expiracao,
        }},
    )

    await _enviar_email_verificacao(email, usuario.get("nome", "Usuário"), novo_token)


async def resetar_senha_controller(token: str, nova_senha: str) -> bool:
    db = Database.get_db()
    agora = datetime.now(timezone.utc)
    
    usuario = await db.usuarios.find_one({
        "reset_token": token,
        "reset_token_expira": {"$gt": agora}
    })
    
    if not usuario:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="O link de recuperação é inválido ou expirou."
        )
        
    nova_senha_hash = hash_password(nova_senha)
    
    await db.usuarios.update_one(
        {"_id": usuario["_id"]},
        {
            "$set": {"senha_hash": nova_senha_hash, "atualizado_em": agora},
            "$unset": {"reset_token": "", "reset_token_expira": ""}
        }
    )
    
    return True