"""
Controller de perfil — lógica de CRUD e formatação de perfis de usuário.

Suporta perfis polimórficos (aluno, professor, pesquisador) na
mesma coleção 'usuarios' do MongoDB (Single Collection Pattern).
"""

from typing import Dict, Any
from datetime import datetime, timedelta, timezone
import secrets
from bson import ObjectId
from fastapi import HTTPException, status
from database.connection import Database
from controllers.usuario_controller import _enviar_email_verificacao
from models.usuario_model import DADOS_POR_PAPEL, PerfilUpdate
from services.emails_institucionais import email_provisorio, filtro_email, validar_email_institucional


def formatar_perfil(doc: Dict[str, Any]) -> Dict[str, Any]:
    """Converte _id do MongoDB e remove dados sensíveis para resposta."""
    if doc is None:
        return None
    if "_id" in doc:
        doc["id"] = str(doc["_id"])
        del doc["_id"]
    doc.pop("senha_hash", None)
    # Não expor tokens ORCID internos
    if "orcid" in doc and doc["orcid"]:
        doc["orcid"].pop("access_token", None)
        doc["orcid"].pop("refresh_token", None)
        doc["orcid"].pop("token_expires_at", None)
        doc["orcid"].pop("scopes", None)
    return doc


def formatar_perfil_publico(doc: Dict[str, Any]) -> Dict[str, Any]:
    """Formata perfil para visualização pública (sem dados sensíveis)."""
    if doc is None:
        return None
    formatado = {
        "id": str(doc["_id"]) if "_id" in doc else doc.get("id"),
        "username": doc.get("username"),
        "nome": doc.get("nome", ""),
        "nome_social": doc.get("nome_social"),
        "avatar_url": doc.get("avatar_url"),
        "bio": doc.get("bio"),
        # contas anteriores ao campo `papel` guardavam `vinculo`
        "papel": doc.get("papel") or doc.get("vinculo") or "aluno",
        "instituicao": doc.get("instituicao"),
        "curso": doc.get("curso"),
        "interesses": doc.get("interesses", []),
        "habilidades": doc.get("habilidades", []),
        "dados_aluno": doc.get("dados_aluno"),
        "dados_professor": doc.get("dados_professor"),
        "dados_pesquisador": doc.get("dados_pesquisador"),
        "dados_tecnico": doc.get("dados_tecnico"),
        "dados_egresso": doc.get("dados_egresso"),
        "departamento": doc.get("departamento"),
        "orcid_id": doc.get("orcid", {}).get("orcid_id") if doc.get("orcid") else None,
        "publicacoes": doc.get("orcid", {}).get("publicacoes", []) if doc.get("orcid") else [],
    }
    return formatado


async def obter_perfil_controller(user_id: str) -> Dict[str, Any]:
    """Obtém o perfil completo de um usuário pelo ID.

    Args:
        user_id: ID do usuário (string do ObjectId).

    Returns:
        Dicionário com perfil completo (sem dados sensíveis).

    Raises:
        HTTPException 404: Se o usuário não for encontrado.
    """
    db = Database.get_db()

    try:
        usuario = await db.usuarios.find_one({"_id": ObjectId(user_id)})
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="ID de usuário inválido.",
        )

    if usuario is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Usuário não encontrado.",
        )

    return formatar_perfil(usuario)


async def atualizar_perfil_controller(
    user_id: str, dados: PerfilUpdate
) -> Dict[str, Any]:
    """Atualiza parcialmente o perfil de um usuário (PATCH).

    Apenas campos enviados (não-None) são atualizados.
    Dados específicos de papel (dados_aluno, etc.) são mesclados,
    não substituídos, para evitar perda de informações.

    Args:
        user_id: ID do usuário.
        dados: Campos a atualizar.

    Returns:
        Perfil atualizado.
    """
    db = Database.get_db()

    try:
        oid = ObjectId(user_id)
    except Exception:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="ID de usuário inválido.")
    atual = await db.usuarios.find_one({"_id": oid})
    if atual is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Usuário não encontrado.")

    # Construir query de update apenas com campos não-None
    update_fields: Dict[str, Any] = {}
    agora = datetime.now(timezone.utc)

    # `exclude_unset`: distingue "não enviado" (mantém) de "enviado como null"
    # (limpa o campo). Antes os null eram descartados e apagar um campo no
    # formulário não tinha efeito.
    dados_dict = dados.model_dump(exclude_unset=True)
    LIMPAVEIS = {"nome_social", "bio", "avatar_url", "instituicao", "curso", "departamento"}
    dados_dict = {
        k: v for k, v in dados_dict.items()
        if v is not None or k in LIMPAVEIS or k in DADOS_POR_PAPEL.values()
    }

    # Campos simples (sobrescrevem direto; null limpa os limpáveis)
    campos_simples = ["nome", *LIMPAVEIS, "interesses", "habilidades"]
    for campo in campos_simples:
        if campo in dados_dict:
            update_fields[campo] = dados_dict[campo]

    # Vínculo institucional (tipo de perfil): pode ser escolhido/alterado pela
    # própria pessoa — o login via ORCID não sabe se ela é discente, docente ou
    # pesquisador(a). Garante o sub-documento do novo tipo.
    papel = dados_dict.get("papel")
    if papel:
        papel = papel.value if hasattr(papel, "value") else str(papel)
        update_fields["papel"] = papel
        campo_dados = DADOS_POR_PAPEL.get(papel)
        if campo_dados and not atual.get(campo_dados):
            # Sub-documento ainda não existe: gravar inteiro (o merge por
            # dot notation abaixo falharia se o valor atual fosse null).
            update_fields[campo_dados] = dados_dict.pop(campo_dados, None) or {}

    # E-mail: só pode ser definido aqui enquanto for o provisório do ORCID.
    # Fica em `email_pendente` até a pessoa confirmar pelo link enviado (mesmo
    # fluxo de verificação do registro); enquanto isso a conta continua
    # funcionando pelo login do ORCID, com o e-mail provisório.
    enviar_verificacao = None
    if "email" in dados_dict:
        novo_email = str(dados_dict["email"]).strip().lower()
        if not email_provisorio(atual.get("email")):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                                detail="O e-mail da conta não pode ser alterado por aqui.")
        try:
            validar_email_institucional(novo_email)
        except ValueError as e:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
        em_uso = await db.usuarios.find_one(
            {"$or": [filtro_email(novo_email), filtro_email(novo_email, "email_pendente")], "_id": {"$ne": oid}})
        vincula = False
        if em_uso is not None:
            # Quem já tinha conta por e-mail/senha e entrou pelo ORCID: ao
            # confirmar o link, o ORCID é vinculado à conta existente (ver
            # verificar_email_controller). Qualquer outro caso é conflito.
            dona_sem_orcid = not (em_uso.get("orcid") or {}).get("orcid_id") and not em_uso.get("email_pendente")
            if not (dona_sem_orcid and (atual.get("orcid") or {}).get("orcid_id")):
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Este email já está cadastrado.")
            vincula = True
        token = secrets.token_urlsafe(48)
        update_fields["email_pendente"] = novo_email
        update_fields["email_pendente_vincula"] = vincula
        update_fields["token_verificacao_email"] = token
        update_fields["token_verificacao_expira"] = agora + timedelta(hours=24)
        enviar_verificacao = (novo_email, token)

    # Aceites (regras da plataforma e compartilhamento de dados)
    if dados_dict.get("aceite_regras") or dados_dict.get("aceite_dados"):
        if dados_dict.get("aceite_regras"):
            update_fields["aceite_regras"] = True
        if dados_dict.get("aceite_dados"):
            update_fields["aceite_dados"] = True
        update_fields["aceites_em"] = agora

    # Conclusão do perfil (contas do ORCID): decidida aqui, não pelo cliente.
    # Exige vínculo escolhido, os dois aceites e o e-mail institucional
    # informado (ou já definido). Sem isso o frontend voltaria a pedir, e a
    # flag é o que libera o uso da plataforma sem aceite registrado.
    if dados_dict.get("perfil_completo"):
        depois = {**atual, **update_fields}
        faltas = []
        if not depois.get("papel"):
            faltas.append("escolher o vínculo institucional")
        if not (depois.get("aceite_regras") and depois.get("aceite_dados")):
            faltas.append("aceitar as regras e o compartilhamento de dados")
        if email_provisorio(depois.get("email")) and not depois.get("email_pendente"):
            faltas.append("informar o e-mail institucional")
        if faltas:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                                detail="Para concluir o perfil falta " + "; ".join(faltas) + ".")
        update_fields["perfil_completo"] = True

    # Campos complexos (dados por tipo de perfil) — merge com existente
    for campo_papel in DADOS_POR_PAPEL.values():
        if dados_dict.get(campo_papel) is not None:
            # Usar dot notation para merge parcial (null limpa o campo)
            for key, value in dados_dict[campo_papel].items():
                update_fields[f"{campo_papel}.{key}"] = value

    if not update_fields:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Nenhum campo válido para atualizar.",
        )

    update_fields["atualizado_em"] = agora

    await db.usuarios.update_one({"_id": oid}, {"$set": update_fields})

    if enviar_verificacao:
        novo_email, token = enviar_verificacao
        await _enviar_email_verificacao(novo_email, atual.get("nome", "Usuário"), token)

    # Retorna perfil atualizado
    return await obter_perfil_controller(user_id)


async def obter_perfil_publico_controller(
    identificador: str,
) -> Dict[str, Any]:
    """Obtém perfil público de um usuário (por ORCID ID ou user ID).

    Args:
        identificador: ORCID ID (0000-0002-...) ou ObjectId do usuário.

    Returns:
        Perfil público formatado.
    """
    db = Database.get_db()

    # Detecta se é ORCID ID (formato: 0000-0000-0000-0000)
    is_orcid = len(identificador) == 19 and identificador.count("-") == 3

    if is_orcid:
        usuario = await db.usuarios.find_one({"orcid.orcid_id": identificador})
    else:
        try:
            usuario = await db.usuarios.find_one({"_id": ObjectId(identificador)})
        except Exception:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Identificador inválido.",
            )

    if usuario is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Perfil não encontrado.",
        )

    return formatar_perfil_publico(usuario)
