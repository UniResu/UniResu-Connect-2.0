"""
Modelos Pydantic para candidaturas de alunos a projetos.

A coleção `candidaturas` é criada no MongoDB automaticamente na primeira
inserção (comportamento padrão do Motor/PyMongo), não há bootstrap manual.
"""

from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel


class CandidaturaStatus(str, Enum):
    """Estados possíveis de uma candidatura."""
    PENDENTE = "pendente"
    APROVADO = "aprovado"
    RECUSADO = "recusado"


class CandidaturaResponse(BaseModel):
    """
    Representa uma candidatura pronta para o frontend.

    Além dos campos próprios da candidatura, inclui dados desnormalizados
    do projeto associado (título e nome do professor) para evitar que o
    frontend precise fazer uma segunda chamada.
    """
    id: str
    id_projeto: str
    id_aluno: Optional[str] = None
    email_aluno: str
    data_candidatura: datetime
    status: CandidaturaStatus = CandidaturaStatus.PENDENTE
    mensagem: Optional[str] = None

    # Dados do projeto associado (populados via join na leitura).
    titulo_projeto: Optional[str] = None
    nome_professor: Optional[str] = None

    class Config:
        from_attributes = True
        use_enum_values = True
