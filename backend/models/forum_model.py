from pydantic import BaseModel, ConfigDict, Field
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
    """Modelo para o que a API retorna ao listar/detalhar tópicos.

    Privacidade: o e-mail do autor NUNCA sai daqui. O autor é identificado
    pelo `autor_username` (e `autor_nome` para exibição), resolvidos a partir
    de `autor_id` em routes/forum_routes.py.
    """
    model_config = ConfigDict(populate_by_name=True, from_attributes=True)

    id: str
    titulo: str
    conteudo_original: Optional[str] = None
    descricao: Optional[str] = None          # campo legado — mantido para compatibilidade
    autor_id: Optional[str] = None           # adicionado na v2.1
    autor_username: Optional[str] = None     # "usuario" quando o autor não é identificado
    autor_nome: Optional[str] = None         # nome_social ou nome; "Usuário" quando não identificado
    data_criacao: Optional[datetime] = Field(default_factory=datetime.now)
    visualizacoes: int = 0
    likes: List[str] = []                    # lista de IDs de usuários
    dislikes: List[str] = []                 # lista de IDs de usuários
