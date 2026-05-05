"""
Rotas de autenticação — ORCID OAuth2 e sessão.

Endpoints:
    GET  /api/auth/orcid/authorize    → Gera URL de autorização ORCID
    POST /api/auth/orcid/callback     → Processa callback OAuth
    GET  /api/auth/me                 → Retorna usuário da sessão atual
    POST /api/auth/sincronizar-orcid  → Re-importa dados do ORCID
"""

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from models.usuario_model import (
    UsuarioResponse,
    LoginResponse,
    LoginRequest,
    RecuperarSenhaRequest,
    ResetarSenhaRequest,
    ReenviarVerificacaoRequest,
)
from controllers.orcid_controller import (
    gerar_url_autorizacao,
    processar_callback_orcid,
    sincronizar_perfil_orcid,
)
from controllers.usuario_controller import (
    login_usuario_controller,
    solicitar_recuperacao_senha_controller,
    resetar_senha_controller,
    verificar_email_controller,
    reenviar_verificacao_controller,
)
from auth.autenticacao import create_access_token, get_usuario_atual

router = APIRouter()


# ── Schemas ──

class OrcidAuthorizeResponse(BaseModel):
    authorize_url: str
    state: str


class OrcidCallbackRequest(BaseModel):
    code: str
    state: str


# ── Rotas ORCID ──


@router.get("/auth/orcid/authorize", response_model=OrcidAuthorizeResponse)
async def orcid_authorize():
    """Retorna a URL para redirecionar o usuário ao login ORCID."""
    return await gerar_url_autorizacao()


@router.post("/auth/orcid/callback", response_model=LoginResponse)
async def orcid_callback(payload: OrcidCallbackRequest):
    """Processa o callback do ORCID após o usuário autorizar.

    Cria ou atualiza o usuário no banco de dados e retorna
    um token JWT para uso no frontend.
    """
    usuario = await processar_callback_orcid(payload.code, payload.state)

    # Gerar JWT interno
    access_token = create_access_token(
        data={"sub": usuario["email"], "papel": usuario.get("papel", "pesquisador")}
    )

    return {
        "access_token": access_token,
        "token_type": "bearer",
        "usuario": usuario,
    }


# ── Rotas de Sessão ──


@router.post("/auth/login", response_model=LoginResponse)
async def login_email_senha(login: LoginRequest):
    """Login alternativo com email + senha.

    Usado por alunos que não possuem ORCID.
    """
    usuario = await login_usuario_controller(login.email, login.senha)

    access_token = create_access_token(
        data={"sub": usuario["email"], "papel": usuario.get("papel", "aluno")}
    )

    return {
        "access_token": access_token,
        "token_type": "bearer",
        "usuario": usuario,
    }


@router.get("/auth/me", response_model=UsuarioResponse)
async def obter_usuario_atual(
    usuario_logado: dict = Depends(get_usuario_atual),
):
    """Retorna os dados do usuário autenticado (via token JWT).

    Usado pelo frontend para verificar se existe sessão ativa.
    """
    return usuario_logado


@router.post("/auth/sincronizar-orcid", response_model=UsuarioResponse)
async def sincronizar_orcid(
    usuario_logado: dict = Depends(get_usuario_atual),
):
    """Re-importa dados do ORCID (publicações, educação, afiliação).

    Requer autenticação. O usuário deve ter um ORCID vinculado.
    """
    return await sincronizar_perfil_orcid(usuario_logado["id"])


# ── Rotas de Verificação de E-mail ──

@router.get("/auth/verificar-email")
async def verificar_email(token: str = Query(..., min_length=1)):
    """Verifica o token recebido no e-mail e ativa a conta do usuário."""
    await verificar_email_controller(token)
    return {"message": "E-mail verificado com sucesso! Você já pode fazer login."}


@router.post("/auth/reenviar-verificacao")
async def reenviar_verificacao(req: ReenviarVerificacaoRequest):
    """Reenvia o e-mail de verificação com um novo token."""
    await reenviar_verificacao_controller(req.email)
    return {"message": "Se o e-mail estiver cadastrado e pendente, um novo link será enviado."}


# ── Rotas de Recuperação de Senha ──

@router.post("/auth/recuperar-senha")
async def recuperar_senha(req: RecuperarSenhaRequest):
    """Dispara o envio de e-mail com token temporário de recuperação."""
    await solicitar_recuperacao_senha_controller(req.email)
    return {"message": "Se o e-mail estiver cadastrado, um link de recuperação será enviado."}

@router.post("/auth/resetar-senha")
async def resetar_senha(req: ResetarSenhaRequest):
    """Verifica o token recebido no e-mail e aplica a nova senha informada."""
    await resetar_senha_controller(req.token, req.nova_senha)
    return {"message": "Sua senha foi redefinida com sucesso. Faça login novamente."}
