from pydantic import BaseModel, ConfigDict
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

    # Campos dos projetos importados do SIGAA (origem="sigaa").
    origem: Optional[str] = None
    tipo_sigaa: Optional[str] = None
    codigo: Optional[str] = None
    unidade: Optional[str] = None
    situacao: Optional[str] = None
    ano: Optional[str] = None
    categoria: Optional[str] = None
    link_detalhe: Optional[str] = None
    periodo_inicio: Optional[str] = None
    periodo_fim: Optional[str] = None

    model_config = ConfigDict(populate_by_name=True, from_attributes=True)


class ProjetoResponse(ProjetoPublicoResponse):
    """Projeto visto pelo próprio autor (inclui o e-mail de contato)."""
    email_professor: Optional[str] = None


class SigaaStatusResponse(BaseModel):
    """Data da última execução bem-sucedida do sync com o SIGAA."""
    ultima_atualizacao: Optional[str] = None
