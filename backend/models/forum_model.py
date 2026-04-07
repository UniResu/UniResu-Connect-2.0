from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime

class RespostaCreate(BaseModel):
    """Modelo para o que o usuário envia ao responder."""
    conteudo: str

class RespostaInDB(BaseModel):
    """Modelo de como a resposta é salva no banco."""
    id: str
    conteudo: str
    autor_email: str
    data_postagem: datetime = Field(default_factory=datetime.now)
    
    class Config:
        populate_by_name = True
        from_attributes = True

class TopicoCreate(BaseModel):
    """Modelo para o que o usuário envia ao criar um tópico."""
    titulo: str
    conteudo: str 

class TopicoResponse(BaseModel):
    """Modelo para o que a API retorna ao listar tópicos."""
    id: str
    titulo: str
    conteudo_original: Optional[str] = None
    descricao: Optional[str] = None
    autor_email: str
    data_criacao: Optional[datetime] = Field(default_factory=datetime.now)
    visualizacoes: int = 0
    respostas: List[RespostaInDB] = [] 
    
    class Config:
        populate_by_name = True
        from_attributes = True