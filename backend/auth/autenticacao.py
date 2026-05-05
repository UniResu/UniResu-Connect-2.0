"""
Módulo de autenticação JWT.

Responsável por criação e validação de tokens JWT.
Centraliza toda a lógica de autenticação para evitar duplicação.
"""

import os
from datetime import datetime, timedelta, timezone
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from dotenv import load_dotenv
from database.connection import Database

load_dotenv()

SECRET_KEY = os.getenv("SECRET_KEY")
ALGORITHM = os.getenv("ALGORITHM", "HS256")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "30"))

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/usuarios/login")


def create_access_token(data: dict, expires_delta: timedelta | None = None) -> str:
    """Cria um token JWT com os dados fornecidos.

    Args:
        data: Payload do token (deve conter 'sub' com o email do usuário).
        expires_delta: Tempo de expiração customizado. Se None, usa o padrão.

    Returns:
        Token JWT codificado.
    """
    if not SECRET_KEY:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="SECRET_KEY não configurada no ambiente.",
        )

    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (
        expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    to_encode.update({"exp": expire})

    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


async def get_usuario_atual(token: str = Depends(oauth2_scheme)) -> dict:
    """Decodifica o token JWT e retorna os dados do usuário.

    Dependency do FastAPI que protege rotas autenticadas.

    Returns:
        Dicionário com dados do usuário (sem senha).

    Raises:
        HTTPException 401: Se o token for inválido ou o usuário não existir.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Não foi possível validar as credenciais.",
        headers={"WWW-Authenticate": "Bearer"},
    )

    if not SECRET_KEY:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="SECRET_KEY não configurada no ambiente.",
        )

    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email: str = payload.get("sub")
        if email is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception

    db = Database.get_db()
    usuario = await db.usuarios.find_one({"email": email})

    if usuario is None:
        raise credentials_exception

    # Bloquear acesso de contas com e-mail não verificado
    if not usuario.get("email_verificado", True):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="E-mail não verificado. Verifique sua caixa de entrada para ativar a conta.",
        )

    # Formata resposta (sem dados sensíveis)
    usuario["id"] = str(usuario["_id"])
    del usuario["_id"]
    usuario.pop("senha_hash", None)

    return usuario