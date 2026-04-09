"""
Ponto de entrada da API UniResu Connect.

Usa o lifespan context manager (padrão moderno do FastAPI) para gerenciar
inicialização e encerramento da conexão com o banco de dados.
"""

import os
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
from database.connection import Database
from routes.usuario_routes import router as router_usuario
from routes.projeto_routes import router as router_projeto
from routes.forum_routes import router as router_forum
from routes.auth_routes import router as router_auth
from routes.perfil_routes import router as router_perfil
from routes.candidatura_routes import router as router_candidatura

load_dotenv()

# Domínios permitidos — carregados do ambiente para flexibilidade no Render.
#
# Estratégia:
#   1. Origens de desenvolvimento local sempre permitidas (localhost/127.0.0.1).
#   2. FRONTEND_URL: variável principal usada no Render para injetar
#      dinamicamente a URL pública do front-end (ex.: https://uniresu-frontend.onrender.com).
#   3. ALLOWED_ORIGINS: lista separada por vírgula, opcional, para cenários
#      com múltiplos domínios (staging, domínio customizado, etc).
_DEFAULT_DEV_ORIGINS = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "http://localhost:5500",
    "http://127.0.0.1:5500",
]

_frontend_url = os.getenv("FRONTEND_URL", "").strip()
_extra_origins_env = os.getenv("ALLOWED_ORIGINS", "")
_extra_origins = [
    origin.strip()
    for origin in _extra_origins_env.split(",")
    if origin.strip()
]

# Monta a lista final sem duplicatas, preservando a ordem.
ALLOWED_ORIGINS = list(dict.fromkeys(
    _DEFAULT_DEV_ORIGINS
    + ([_frontend_url] if _frontend_url else [])
    + _extra_origins
))


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Gerencia o ciclo de vida da aplicação (startup/shutdown)."""
    # ── Startup ──
    await Database.connect()
    yield
    # ── Shutdown ──
    await Database.disconnect()


app = FastAPI(
    title="UniResu API",
    description="API da plataforma UniResu Connect — conectando a comunidade acadêmica.",
    version="2.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type"],
)


# ── Health Check ──
@app.get("/health", tags=["Infra"])
async def health_check():
    """Endpoint de health check para Load Balancer / Render / Kubernetes."""
    checks = {}

    try:
        db = Database.get_db()
        await db.command("ping")
        checks["mongodb"] = "healthy"
    except Exception:
        checks["mongodb"] = "unhealthy"

    all_healthy = all(v == "healthy" for v in checks.values())

    return {
        "status": "healthy" if all_healthy else "degraded",
        "checks": checks,
    }


@app.get("/", tags=["Infra"])
async def home():
    """Rota raiz — verificar se a API está online."""
    return {"status": "Servidor FastAPI rodando!", "version": "2.1.0"}


# ── Routers ──
app.include_router(router_auth, prefix="/api", tags=["Autenticação"])
app.include_router(router_perfil, prefix="/api", tags=["Perfil"])
app.include_router(router_usuario, prefix="/api", tags=["Usuários"])
app.include_router(router_projeto, prefix="/api", tags=["Projetos"])
app.include_router(router_candidatura, prefix="/api", tags=["Candidatura"])
app.include_router(router_forum, prefix="/api", tags=["Fórum"])