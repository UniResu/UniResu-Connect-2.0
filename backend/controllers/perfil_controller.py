"""
Controller de perfil — lógica de CRUD e formatação de perfis de usuário.

Suporta perfis polimórficos (aluno, professor, pesquisador) na
mesma coleção 'usuarios' do MongoDB (Single Collection Pattern).
"""

from typing import Dict, Any, Optional
from datetime import datetime, timezone
from bson import ObjectId
from fastapi import HTTPException, status
from database.connection import Database
from models.usuario_model import PerfilUpdate


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
        "nome": doc.get("nome", ""),
        "nome_social": doc.get("nome_social"),
        "avatar_url": doc.get("avatar_url"),
        "bio": doc.get("bio"),
        "papel": doc.get("papel"),
        "instituicao": doc.get("instituicao"),
        "curso": doc.get("curso"),
        "interesses": doc.get("interesses", []),
        "habilidades": doc.get("habilidades", []),
        "dados_aluno": doc.get("dados_aluno"),
        "dados_professor": doc.get("dados_professor"),
        "dados_pesquisador": doc.get("dados_pesquisador"),
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

    # Construir query de update apenas com campos não-None
    update_fields: Dict[str, Any] = {}

    dados_dict = dados.model_dump(exclude_none=True)

    # Campos simples (sobrescrevem direto)
    campos_simples = [
        "nome", "nome_social", "bio", "avatar_url",
        "instituicao", "curso", "departamento",
        "interesses", "habilidades",
    ]
    for campo in campos_simples:
        if campo in dados_dict:
            update_fields[campo] = dados_dict[campo]

    # Campos complexos (dados por papel) — merge com existente
    for campo_papel in ["dados_aluno", "dados_professor", "dados_pesquisador"]:
        if campo_papel in dados_dict:
            # Usar dot notation para merge parcial
            for key, value in dados_dict[campo_papel].items():
                update_fields[f"{campo_papel}.{key}"] = value

    if not update_fields:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Nenhum campo válido para atualizar.",
        )

    update_fields["atualizado_em"] = datetime.now(timezone.utc)

    try:
        result = await db.usuarios.update_one(
            {"_id": ObjectId(user_id)},
            {"$set": update_fields},
        )
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="ID de usuário inválido.",
        )

    if result.matched_count == 0:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Usuário não encontrado.",
        )

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
