from pydantic import BaseModel, ConfigDict
from typing import Dict, List, Optional


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


class ProjetoPublicoResponse(BaseModel):
    """Projeto como aparece na busca pública.

    Não expõe o e-mail do professor/coordenador: o frontend só precisa
    saber se há contato (`tem_contato`) para habilitar a candidatura.
    """
    id: str

    titulo: str
    descricao: Optional[str] = None
    instituicao: Optional[str] = None
    tipo: Optional[str] = None
    dataPublicacao: Optional[str] = None

    local: Optional[str] = None
    modalidade: Optional[str] = None
    area_estudo: Optional[str] = None
    e_remoto: Optional[bool] = None
    nome_professor: Optional[str] = None
    autor_id: Optional[str] = None
    tem_contato: bool = False

    # Campos dos projetos importados de fontes externas (origem="sigaa" | "unirio").
    origem: Optional[str] = None
    modulo: Optional[str] = None       # "pesquisa" | "extensao"
    tipo_sigaa: Optional[str] = None   # nome antigo de `modulo` (docs do SIGAA)
    codigo: Optional[str] = None
    unidade: Optional[str] = None
    situacao: Optional[str] = None
    ano: Optional[str] = None
    categoria: Optional[str] = None
    link_detalhe: Optional[str] = None
    periodo_inicio: Optional[str] = None
    periodo_fim: Optional[str] = None
    # Extras dos portais da UNIRIO.
    area_tematica: Optional[str] = None
    palavras_chave: Optional[List[str]] = None

    model_config = ConfigDict(populate_by_name=True, from_attributes=True)


class ProjetoResponse(ProjetoPublicoResponse):
    """Projeto visto pelo próprio autor (inclui o e-mail de contato)."""
    email_professor: Optional[str] = None


class FonteStatus(BaseModel):
    instituicao: str
    rotulo: str
    ultima_atualizacao: Optional[str] = None


class FontesStatusResponse(BaseModel):
    """Data da última execução bem-sucedida do sync de cada fonte externa.

    `ultima_atualizacao` é a do SIGAA/UNIR (compatibilidade com o front antigo).
    """
    ultima_atualizacao: Optional[str] = None
    fontes: Dict[str, FonteStatus] = {}


# Nome antigo.
SigaaStatusResponse = FontesStatusResponse
