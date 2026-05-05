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
        """Valida por whitelist de domínios acadêmicos (aceita subdomínios).

        Regra:
          - Aceita qualquer domínio terminado em '.edu.br' ou '.edu'.
          - Aceita domínios listados em `dominios_permitidos`, inclusive
            quaisquer subdomínios (ex.: 'sga.pucminas.br' → OK porque
            termina em '.pucminas.br').
        """
        dominio = email.split('@')[-1].lower().strip()
        if not dominio:
            raise ValueError('E-mail inválido.')

        # Regra geral: qualquer instituição acadêmica (.edu.br / .edu)
        if dominio.endswith('.edu.br') or dominio == 'edu.br' \
                or dominio.endswith('.edu') or dominio == 'edu':
            return email

        dominios_permitidos = {
            # Federais
            'ufrj.br', 'ufmg.br', 'unb.br', 'ufrgs.br', 'ufsc.br',
            'ufpr.br', 'ufpe.br', 'ufba.br', 'ufg.br', 'ufrn.br',
            'ufv.br', 'ufscar.br', 'unifesp.br', 'ufc.br', 'ufu.br',
            # Estaduais
            'usp.br', 'unicamp.br', 'unesp.br', 'uerj.br', 'udesc.br',
            'uems.br', 'unemat.br', 'uenp.br',
            # PUCs
            'pucminas.br', 'puc-rio.br', 'pucsp.br', 'pucpr.br',
            'pucrs.br', 'puccampinas.edu.br',
            # Privadas e institutos
            'fgv.br', 'insper.edu.br', 'mackenzie.br', 'einstein.br',
            'fia.com.br', 'senai.br', 'itajuba.edu.br', 'ita.br',
            'ime.eb.mil.br',
        }

        for alvo in dominios_permitidos:
            if dominio == alvo or dominio.endswith('.' + alvo):
                return email

        raise ValueError('Apenas e-mails institucionais acadêmicos são permitidos.')


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