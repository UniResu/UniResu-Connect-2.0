"""
Modelos Pydantic para Usuário / Perfil.

Suporta polimorfismo por papel (vínculo institucional): aluno (discente),
professor (docente), pesquisador(a), tecnico (técnico-administrativo) e
egresso. Integração com dados do ORCID.
"""

from pydantic import BaseModel, EmailStr, Field, field_validator, model_validator
from typing import Optional, List
from datetime import datetime
from enum import Enum

from services.emails_institucionais import validar_email_institucional


# ═══════════════════════════════════════════
#  Enums
# ═══════════════════════════════════════════

class PapelUsuario(str, Enum):
    """Vínculo institucional. Os três primeiros valores existem desde a
    primeira versão e continuam com o nome interno antigo (a interface mostra
    "Discente", "Docente", "Pesquisador(a)")."""
    ALUNO = "aluno"
    PROFESSOR = "professor"
    PESQUISADOR = "pesquisador"
    TECNICO = "tecnico"
    EGRESSO = "egresso"


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


class DadosTecnico(BaseModel):
    """Campos exclusivos de técnicos(as)-administrativos(as)."""
    setor: Optional[str] = None              # laboratório, secretaria, biblioteca...
    cargo: Optional[str] = None


class DadosEgresso(BaseModel):
    """Campos exclusivos de egressos(as)."""
    ano_conclusao: Optional[int] = Field(None, ge=1900, le=2100)
    atuacao: Optional[str] = None            # onde atua hoje (empresa, pós em outra IES...)


# Sub-documento de cada vínculo (nome do campo no banco).
DADOS_POR_PAPEL = {
    PapelUsuario.ALUNO: "dados_aluno",
    PapelUsuario.PROFESSOR: "dados_professor",
    PapelUsuario.PESQUISADOR: "dados_pesquisador",
    PapelUsuario.TECNICO: "dados_tecnico",
    PapelUsuario.EGRESSO: "dados_egresso",
}


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
    """Schema para criação de usuário (registro).

    A pessoa escolhe o vínculo (`papel`) e pode já preencher o sub-documento
    correspondente; os dois aceites são obrigatórios.
    """
    email: EmailStr
    senha: Optional[str] = Field(None, min_length=6)   # Opcional se login via ORCID
    nome: str = Field(min_length=2, max_length=200)
    papel: PapelUsuario
    instituicao: Optional[str] = Field(None, max_length=200)
    curso: Optional[str] = Field(None, max_length=200)
    departamento: Optional[str] = Field(None, max_length=200)
    aceite_regras: bool = Field(..., description="Li e aceito as regras da plataforma")
    aceite_dados: bool = Field(..., description="Aceito o compartilhamento dos dados do perfil")
    dados_aluno: Optional[DadosAluno] = None
    dados_professor: Optional[DadosProfessor] = None
    dados_pesquisador: Optional[DadosPesquisador] = None
    dados_tecnico: Optional[DadosTecnico] = None
    dados_egresso: Optional[DadosEgresso] = None

    @field_validator('email')
    @classmethod
    def email_deve_ser_institucional(cls, email: str) -> str:
        """Whitelist de domínios acadêmicos (ver services.emails_institucionais)."""
        return validar_email_institucional(email)

    @field_validator('aceite_regras', 'aceite_dados')
    @classmethod
    def aceites_obrigatorios(cls, valor: bool) -> bool:
        if not valor:
            raise ValueError('É preciso aceitar as regras da plataforma e o compartilhamento de dados.')
        return valor


class PerfilUpdate(BaseModel):
    """Schema para atualização parcial do perfil (PATCH)."""
    nome: Optional[str] = Field(None, min_length=2, max_length=200)
    nome_social: Optional[str] = None
    bio: Optional[str] = Field(None, max_length=2000)
    avatar_url: Optional[str] = None
    papel: Optional[PapelUsuario] = None     # vínculo pode ser escolhido/alterado pela pessoa
    email: Optional[EmailStr] = None         # só aceito enquanto for o provisório do ORCID
    instituicao: Optional[str] = Field(None, max_length=200)
    curso: Optional[str] = Field(None, max_length=200)
    departamento: Optional[str] = Field(None, max_length=200)
    interesses: Optional[List[str]] = None
    habilidades: Optional[List[str]] = None
    aceite_regras: Optional[bool] = None
    aceite_dados: Optional[bool] = None
    perfil_completo: Optional[bool] = None   # marcado ao concluir /perfil/completar
    dados_aluno: Optional[DadosAluno] = None
    dados_professor: Optional[DadosProfessor] = None
    dados_pesquisador: Optional[DadosPesquisador] = None
    dados_tecnico: Optional[DadosTecnico] = None
    dados_egresso: Optional[DadosEgresso] = None


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


class ReenviarVerificacaoRequest(BaseModel):
    """Schema para reenviar e-mail de verificação."""
    email: EmailStr


# ═══════════════════════════════════════════
#  Schemas de saída (response)
# ═══════════════════════════════════════════

class UsuarioResponse(BaseModel):
    """Resposta completa do usuário logado (sem dados sensíveis)."""
    id: str
    email: EmailStr
    # E-mail institucional informado por uma conta do ORCID e ainda não
    # confirmado pelo link enviado; substitui `email` na confirmação.
    email_pendente: Optional[EmailStr] = None
    # True quando esse e-mail já pertence a uma conta por senha: ao confirmar,
    # o ORCID é vinculado a ela e esta conta provisória é desativada.
    email_pendente_vincula: bool = False
    aceite_regras: bool = False
    aceite_dados: bool = False
    username: Optional[str] = None           # identificador público (fórum); gerado do nome
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
    dados_tecnico: Optional[DadosTecnico] = None
    dados_egresso: Optional[DadosEgresso] = None
    orcid: Optional[OrcidData] = None
    # False só para contas criadas pelo ORCID que ainda não escolheram o
    # vínculo nem informaram o e-mail institucional (/perfil/completar).
    perfil_completo: bool = True
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
    username: Optional[str] = None           # identificador público (fórum); gerado do nome
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
    dados_tecnico: Optional[DadosTecnico] = None
    dados_egresso: Optional[DadosEgresso] = None
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