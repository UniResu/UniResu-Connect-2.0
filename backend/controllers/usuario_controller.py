"""
Controller de usuários — lógica de negócio para registro e login.

Centraliza hash de senha, verificação e operações de CRUD de usuários.
Usa Motor (async) para todas as operações com o banco.
"""

from typing import Dict, Any
from datetime import datetime, timezone
from fastapi import HTTPException, status
from passlib.context import CryptContext
from database.connection import Database
from models.usuario_model import UsuarioCreate

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


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

    # Atualizar último login
    await db.usuarios.update_one(
        {"_id": usuario["_id"]},
        {"$set": {"ultimo_login": datetime.now(timezone.utc)}},
    )

    return formatar_usuario(usuario)