"""
Modelos Pydantic para Usuário / Perfil.

Suporta polimorfismo por papel: aluno, professor, pesquisador.
Integração com dados do ORCID.
"""

from pydantic import BaseModel, EmailStr, Field, field_validator, model_validator
from typing import Optional, List
from datetime import datetime
from enum import Enum


# ═══════════════════════════════════════════
#  Enums
# ═══════════════════════════════════════════

class PapelUsuario(str, Enum):
    ALUNO = "aluno"
    PROFESSOR = "professor"
    PESQUISADOR = "pesquisador"


class NivelAcademico(str, Enum):
    GRADUACAO = "graduacao"
    MESTRADO = "mestrado"
    DOUTORADO = "doutorado"


# ═══════════════════════════════════════════
#  Sub-schemas por papel (polimorfismo)
# ═══════════════════════════════════════════

class DadosAluno(BaseModel):
    """Campos exclusivos de alunos."""
    nivel: NivelAcademico = NivelAcademico.GRADUACAO
    semestre: int = Field(ge=1, le=100, default=1)
    orientador: Optional[str] = None
    linha_pesquisa: Optional[str] = None


class DadosProfessor(BaseModel):
    """Campos exclusivos de professores."""
    titulo: Optional[str] = None             # Dr., Me., PhD
    cargo: Optional[str] = None              # Professor Associado, Titular, etc.
    linhas_pesquisa: List[str] = []
    laboratorio: Optional[str] = None


class DadosPesquisador(BaseModel):
    """Campos exclusivos de pesquisadores."""
    titulo: Optional[str] = None
    vinculo: Optional[str] = None            # Pós-Doc, Colaborador, Visitante
    linhas_pesquisa: List[str] = []
    grupo_pesquisa: Optional[str] = None


# ═══════════════════════════════════════════
#  ORCID — dados importados
# ═══════════════════════════════════════════

class OrcidPublicacao(BaseModel):
    """Publicação importada do ORCID."""
    titulo: str
    doi: Optional[str] = None
    ano: Optional[int] = None
    tipo: Optional[str] = None               # journal-article, conference-paper


class OrcidEducacao(BaseModel):
    """Formação acadêmica importada do ORCID."""
    instituicao: str
    grau: Optional[str] = None
    area: Optional[str] = None
    inicio: Optional[int] = None
    fim: Optional[int] = None


class OrcidData(BaseModel):
    """Dados do ORCID armazenados no perfil do usuário."""
    orcid_id: str
    nome_orcid: Optional[str] = None
    afiliacao_orcid: Optional[str] = None
    perfil_sincronizado_em: Optional[datetime] = None
    publicacoes: List[OrcidPublicacao] = []
    educacao: List[OrcidEducacao] = []


# ═══════════════════════════════════════════
#  Schemas de entrada (create / update)
# ═══════════════════════════════════════════

class UsuarioCreate(BaseModel):
    """Schema para criação de usuário (registro)."""
    email: EmailStr
    senha: Optional[str] = None              # Opcional se login via ORCID
    nome: str = Field(min_length=2, max_length=200)
    papel: PapelUsuario
    instituicao: Optional[str] = None
    curso: Optional[str] = None

    @field_validator('email')
    @classmethod
    def email_deve_ser_institucional(cls, email: str) -> str:
        dominios_proibidos = {"gmail.com", "hotmail.com", "yahoo.com", "outlook.com", "protonmail.com"}
        dominio = email.split('@')[-1].lower()
        if dominio in dominios_proibidos:
            raise ValueError('Apenas e-mails institucionais são permitidos')
        return email


class PerfilUpdate(BaseModel):
    """Schema para atualização parcial do perfil (PATCH)."""
    nome: Optional[str] = Field(None, min_length=2, max_length=200)
    nome_social: Optional[str] = None
    bio: Optional[str] = Field(None, max_length=2000)
    avatar_url: Optional[str] = None
    instituicao: Optional[str] = None
    curso: Optional[str] = None
    departamento: Optional[str] = None
    interesses: Optional[List[str]] = None
    habilidades: Optional[List[str]] = None
    dados_aluno: Optional[DadosAluno] = None
    dados_professor: Optional[DadosProfessor] = None
    dados_pesquisador: Optional[DadosPesquisador] = None


class LoginRequest(BaseModel):
    """Schema para login com email+senha."""
    email: EmailStr
    senha: str

class RecuperarSenhaRequest(BaseModel):
    """Schema para solicitar recuperação de senha."""
    email: EmailStr

class ResetarSenhaRequest(BaseModel):
    """Schema para redefinir a senha com o token recebido."""
    token: str
    nova_senha: str = Field(min_length=6)


# ═══════════════════════════════════════════
#  Schemas de saída (response)
# ═══════════════════════════════════════════

class UsuarioResponse(BaseModel):
    """Resposta completa do usuário logado (sem dados sensíveis)."""
    id: str
    email: EmailStr
    nome: str
    nome_social: Optional[str] = None
    avatar_url: Optional[str] = None
    bio: Optional[str] = None
    papel: PapelUsuario
    instituicao: Optional[str] = None
    curso: Optional[str] = None
    departamento: Optional[str] = None
    interesses: List[str] = []
    habilidades: List[str] = []
    dados_aluno: Optional[DadosAluno] = None
    dados_professor: Optional[DadosProfessor] = None
    dados_pesquisador: Optional[DadosPesquisador] = None
    orcid: Optional[OrcidData] = None
    criado_em: Optional[datetime] = None

    @model_validator(mode='before')
    @classmethod
    def compatibilidade_banco_legado(cls, data):
        if isinstance(data, dict):
            if 'papel' not in data and 'vinculo' in data:
                data['papel'] = data['vinculo']
            elif 'papel' not in data:
                data['papel'] = "aluno"
        return data

    class Config:
        from_attributes = True


class PerfilPublicoResponse(BaseModel):
    """Perfil visível para outros usuários (sem emails, tokens, etc.)."""
    id: str
    nome: str
    nome_social: Optional[str] = None
    avatar_url: Optional[str] = None
    bio: Optional[str] = None
    papel: PapelUsuario
    instituicao: Optional[str] = None
    curso: Optional[str] = None
    interesses: List[str] = []
    habilidades: List[str] = []
    dados_aluno: Optional[DadosAluno] = None
    dados_professor: Optional[DadosProfessor] = None
    dados_pesquisador: Optional[DadosPesquisador] = None
    orcid_id: Optional[str] = None
    publicacoes: List[OrcidPublicacao] = []

    @model_validator(mode='before')
    @classmethod
    def compatibilidade_banco_legado(cls, data):
        if isinstance(data, dict):
            if 'papel' not in data and 'vinculo' in data:
                data['papel'] = data['vinculo']
            elif 'papel' not in data:
                data['papel'] = "aluno"
        return data

    class Config:
        from_attributes = True


class LoginResponse(BaseModel):
    """Resposta do login com token JWT."""
    access_token: str
    token_type: str = "bearer"
    usuario: UsuarioResponse