"""
Ponto de entrada da API UniResu Connect.

Usa o lifespan context manager (padrão moderno do FastAPI) para gerenciar
inicialização e encerramento da conexão com o banco de dados.
"""

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

# Origens permitidas pelo CORS.
# Lista explícita — inclui dev local, o domínio oficial de produção
# (uniresu.org e www.uniresu.org) e a URL legada do Render.
origins = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "https://uniresu.org",
    "https://www.uniresu.org",
    "https://uniresu-frontend.onrender.com",  # URL legada do Render
]


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

# IMPORTANTE: o middleware de CORS deve ser registrado ANTES da inclusão
# de qualquer router, para que se aplique a todas as rotas abaixo.
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
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