"""
Modelos Pydantic para candidaturas de alunos a projetos.

A coleção `candidaturas` é criada no MongoDB automaticamente na primeira
inserção (comportamento padrão do Motor/PyMongo), não há bootstrap manual.
"""

import re
from datetime import datetime
from enum import Enum
from typing import Optional
from urllib.parse import urlparse

from pydantic import BaseModel, EmailStr, Field, field_validator

CARTA_MIN_CARACTERES = 300
CARTA_MAX_CARACTERES = 5000
HOSTS_LATTES = {"lattes.cnpq.br", "buscatextual.cnpq.br"}

# Caracteres de controle (exceto \n e \t) — removidos de todo texto livre.
_RE_CONTROLE = re.compile(r"[\x00-\x08\x0b-\x1f\x7f]")


def _linha_unica(valor: str) -> str:
    """Texto de uma linha: sem quebras (evita header injection no assunto)."""
    valor = _RE_CONTROLE.sub("", valor.replace("\r", " ").replace("\n", " ").replace("\t", " "))
    return re.sub(r"\s+", " ", valor).strip()


class CandidaturaCreate(BaseModel):
    """Formulário de candidatura com carta de intenção."""
    nome: str = Field(..., min_length=3, max_length=120)
    curso_periodo: str = Field(..., min_length=2, max_length=120)
    email: EmailStr
    lattes_url: Optional[str] = Field(None, max_length=300)
    carta: str = Field(..., min_length=CARTA_MIN_CARACTERES, max_length=CARTA_MAX_CARACTERES)

    @field_validator("nome", "curso_periodo", mode="before")
    @classmethod
    def _limpar_linha(cls, v):
        return _linha_unica(v) if isinstance(v, str) else v

    @field_validator("carta", mode="before")
    @classmethod
    def _limpar_carta(cls, v):
        if not isinstance(v, str):
            return v
        v = _RE_CONTROLE.sub("", v.replace("\r\n", "\n").replace("\r", "\n"))
        v = re.sub(r"[ \t]+\n", "\n", v)          # espaços no fim da linha
        v = re.sub(r"\n{3,}", "\n\n", v)          # no máx. uma linha em branco
        return v.strip()

    @field_validator("lattes_url", mode="before")
    @classmethod
    def _validar_lattes(cls, v):
        if v is None or (isinstance(v, str) and not v.strip()):
            return None
        v = v.strip()
        url = urlparse(v)
        if url.scheme not in ("http", "https") or (url.hostname or "").lower() not in HOSTS_LATTES:
            raise ValueError("Informe um link do Currículo Lattes (lattes.cnpq.br).")
        return v


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
