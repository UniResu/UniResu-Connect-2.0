from pydantic import BaseModel, ConfigDict, Field, field_validator
from typing import List, Optional
from datetime import datetime

# Limite de uma resposta, contado depois de tirar os espaços das pontas.
RESPOSTA_MAX_CARACTERES = 5000


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
    total_respostas: int = 0                 # contador ($inc); tópicos antigos sem o campo contam 0
    primeira_do_autor: bool = False          # primeira pergunta de quem escreveu (selo "Primeiro contato")


# ── Respostas (um único nível: respondem ao tópico, nunca a outra resposta) ──

class RespostaCreate(BaseModel):
    """Corpo de POST /forum/topicos/{id}/respostas e de PATCH /forum/respostas/{id}."""
    conteudo: str

    @field_validator("conteudo")
    @classmethod
    def conteudo_valido(cls, valor: str) -> str:
        valor = valor.strip()
        if not valor:
            raise ValueError("Escreva o texto da resposta.")
        if len(valor) > RESPOSTA_MAX_CARACTERES:
            raise ValueError("A resposta pode ter no máximo 5.000 caracteres.")
        return valor


class RespostaUpdate(RespostaCreate):
    """Edição de uma resposta: o texto inteiro é substituído."""


class RespostaResponse(BaseModel):
    """Uma resposta como a API devolve. Mesma regra de privacidade dos tópicos:
    o autor sai como `autor_username`/`autor_nome`, nunca como e-mail."""
    model_config = ConfigDict(populate_by_name=True, from_attributes=True)

    id: str
    topico_id: str
    conteudo: str
    autor_id: Optional[str] = None
    autor_username: Optional[str] = None
    autor_nome: Optional[str] = None
    data_criacao: Optional[datetime] = None
    editado_em: Optional[datetime] = None


class RespostasPagina(BaseModel):
    """Uma página de respostas (da mais antiga para a mais nova) e o total do tópico."""
    total: int
    respostas: List[RespostaResponse]


class TopicoDetalhe(TopicoResponse):
    """GET de um tópico: o tópico e as primeiras respostas, para a thread
    abrir com uma requisição só."""
    respostas: List[RespostaResponse] = []
