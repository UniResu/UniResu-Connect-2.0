"""
Módulo de conexão com MongoDB usando Motor (driver assíncrono).

Utiliza uma classe Database como singleton para gerenciar a conexão,
eliminando variáveis globais mutáveis e possibilitando escala horizontal.
"""

import os
from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv

load_dotenv()

MONGO_URI = os.getenv("MONGO_URI")
MONGO_DB_NAME = os.getenv("MONGO_DB_NAME", "UniResuDB")


class Database:
    """Gerenciador de conexão MongoDB assíncrono (Motor).

    Uso com o lifespan do FastAPI:
        - Database.connect() no startup
        - Database.disconnect() no shutdown
        - Database.get_db() para obter referência do banco
    """

    client: AsyncIOMotorClient = None
    db = None

    @classmethod
    async def connect(cls):
        """Conecta ao MongoDB Atlas via Motor (assíncrono)."""
        if not MONGO_URI:
            raise RuntimeError(
                "❌ ERRO: Variável MONGO_URI não encontrada. "
                "Verifique se seu arquivo .env está configurado corretamente."
            )

        cls.client = AsyncIOMotorClient(
            MONGO_URI,
            maxPoolSize=50,
            minPoolSize=10,
            serverSelectionTimeoutMS=5000,
            connectTimeoutMS=10000,
        )

        # Verifica conectividade
        await cls.client.admin.command("ping")
        cls.db = cls.client[MONGO_DB_NAME]
        print(f"[OK] Conectado ao MongoDB Atlas (Banco: {cls.db.name}) - Driver: Motor (async)")

    @classmethod
    async def disconnect(cls):
        """Fecha a conexão com o MongoDB."""
        if cls.client:
            cls.client.close()
            cls.client = None
            cls.db = None
            print("[CLOSED] Conexao com MongoDB fechada.")

    @classmethod
    def get_db(cls):
        """Retorna referência ao banco de dados.

        Returns:
            AsyncIOMotorDatabase: Referência ao banco MongoDB.

        Raises:
            RuntimeError: Se o banco não estiver conectado.
        """
        if cls.db is None:
            raise RuntimeError(
                "Database não conectado. Certifique-se de que Database.connect() "
                "foi chamado no lifespan do FastAPI."
            )
        return cls.db


# Função de conveniência para retrocompatibilidade
def get_db():
    """Atalho para Database.get_db(). Retrocompatível com código existente."""
    return Database.get_db()