from pydantic import BaseModel, Field
from typing import Optional


class ProjetoCreate(BaseModel):
    """Payload para criação/edição de projetos."""
    titulo: str
    descricao: str
    modalidade: Optional[str] = "Presencial"
    instituicao: Optional[str] = None
    local: Optional[str] = None
    area_estudo: Optional[str] = None
    tipo_projeto: Optional[str] = "voluntario_aberto"
    nome_professor: Optional[str] = None
    email_professor: Optional[str] = None


class ProjetoResponse(BaseModel):
    id: str

    titulo: str
    descricao: str
    instituicao: Optional[str] = None
    tipo: Optional[str] = None
    dataPublicacao: Optional[str] = None

    local: Optional[str] = None
    modalidade: Optional[str] = None
    area_estudo: Optional[str] = None
    e_remoto: Optional[bool] = None
    nome_professor: Optional[str] = None
    email_professor: Optional[str] = None
    autor_id: Optional[str] = None

    class Config:
        populate_by_name = True
        from_attributes = True