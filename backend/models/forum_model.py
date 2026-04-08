from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime


class TopicoCreate(BaseModel):
    """Modelo para o que o usuário envia ao criar um tópico."""
    titulo: str
    conteudo: str


class TopicoUpdate(BaseModel):
    """Modelo para edição parcial de um tópico (PATCH)."""
    titulo: Optional[str] = None
    conteudo: Optional[str] = None


class TopicoResponse(BaseModel):
    """Modelo para o que a API retorna ao listar/detalhar tópicos."""
    id: str
    titulo: str
    conteudo_original: Optional[str] = None
    descricao: Optional[str] = None          # campo legado — mantido para compatibilidade
    autor_email: str
    autor_id: Optional[str] = None           # adicionado na v2.1
    data_criacao: Optional[datetime] = Field(default_factory=datetime.now)
    visualizacoes: int = 0
    likes: List[str] = []                    # lista de IDs de usuários
    dislikes: List[str] = []                 # lista de IDs de usuários

    class Config:
        populate_by_name = True
        from_attributes = True