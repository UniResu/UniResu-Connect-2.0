import os
from pathlib import Path

import pytest
from httpx import ASGITransport, AsyncClient
from mongomock_motor import AsyncMongoMockClient

# Variáveis mínimas para importar o app sem .env real.
os.environ.setdefault("SECRET_KEY", "test-secret")
os.environ.pop("RESEND_API_KEY", None)

from auth.autenticacao import get_usuario_atual  # noqa: E402
from database.connection import Database  # noqa: E402
from main import app  # noqa: E402

FIXTURES = Path(__file__).parent / "fixtures"

ALUNO = {"id": "aluno-1", "email": "aluno@exemplo.com", "papel": "aluno", "nome": "Aluno Teste"}


def ler_fixture(nome: str) -> str:
    # O SIGAA serve ISO-8859-1; as fixtures foram salvas no mesmo encoding.
    return (FIXTURES / nome).read_bytes().decode("iso-8859-1")


@pytest.fixture
def db():
    """Banco MongoDB em memória, injetado no singleton Database."""
    banco = AsyncMongoMockClient()["uniresu_test"]
    anterior = Database.db
    Database.db = banco
    yield banco
    Database.db = anterior


@pytest.fixture
async def api(db):
    """Cliente HTTP do app (sem lifespan: não conecta no Mongo real)."""
    app.dependency_overrides[get_usuario_atual] = lambda: dict(ALUNO)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        yield client
    app.dependency_overrides.clear()
