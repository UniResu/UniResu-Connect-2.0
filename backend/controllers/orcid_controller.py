"""
Controller de autenticação ORCID — fluxo OAuth2 Authorization Code + PKCE.

Responsável por:
1. Gerar URL de autorização para o ORCID
2. Processar o callback com code → trocar por tokens
3. Upsert do usuário com dados do ORCID
4. Sincronização de perfil com dados públicos do ORCID
"""

import os
import secrets
import hashlib
import base64
from datetime import datetime, timezone
from typing import Dict, Any, Optional
from fastapi import HTTPException, status
from dotenv import load_dotenv
import httpx
from database.connection import Database

load_dotenv()

ORCID_CLIENT_ID = os.getenv("ORCID_CLIENT_ID", "")
ORCID_CLIENT_SECRET = os.getenv("ORCID_CLIENT_SECRET", "")
ORCID_REDIRECT_URI = os.getenv("ORCID_REDIRECT_URI", "")
ORCID_BASE_URL = os.getenv("ORCID_BASE_URL", "https://orcid.org")
ORCID_API_URL = os.getenv("ORCID_API_URL", "https://pub.orcid.org/v3.0")

# Armazenamento temporário de states (em produção, usar Redis)
_pending_states: Dict[str, Dict[str, str]] = {}


def _gerar_pkce() -> tuple[str, str]:
    """Gera code_verifier e code_challenge para PKCE."""
    code_verifier = secrets.token_urlsafe(64)
    digest = hashlib.sha256(code_verifier.encode()).digest()
    code_challenge = base64.urlsafe_b64encode(digest).rstrip(b"=").decode()
    return code_verifier, code_challenge


async def gerar_url_autorizacao() -> Dict[str, str]:
    """Gera a URL de autorização do ORCID com PKCE.

    Returns:
        Dict com 'authorize_url' e 'state'.
    """
    if not ORCID_CLIENT_ID:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="ORCID_CLIENT_ID não configurado.",
        )

    state = secrets.token_urlsafe(32)
    code_verifier, code_challenge = _gerar_pkce()

    # Salvar state para validação posterior
    _pending_states[state] = {
        "code_verifier": code_verifier,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }

    params = {
        "client_id": ORCID_CLIENT_ID,
        "response_type": "code",
        "scope": "/authenticate",
        "redirect_uri": ORCID_REDIRECT_URI,
        "state": state,
        "code_challenge": code_challenge,
        "code_challenge_method": "S256",
    }

    query_string = "&".join(f"{k}={v}" for k, v in params.items())
    authorize_url = f"{ORCID_BASE_URL}/oauth/authorize?{query_string}"

    return {"authorize_url": authorize_url, "state": state}


async def processar_callback_orcid(
    code: str, state: str
) -> Dict[str, Any]:
    """Processa o callback do ORCID: troca code por token e upsert usuário.

    Args:
        code: Authorization code do ORCID.
        state: State para validação CSRF.

    Returns:
        Dados do usuário criado/atualizado.
    """
    # Validar state
    state_data = _pending_states.pop(state, None)
    if state_data is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="State inválido ou expirado.",
        )

    code_verifier = state_data["code_verifier"]

    # Trocar code por token no ORCID
    async with httpx.AsyncClient(timeout=15.0) as client:
        token_response = await client.post(
            f"{ORCID_BASE_URL}/oauth/token",
            data={
                "client_id": ORCID_CLIENT_ID,
                "client_secret": ORCID_CLIENT_SECRET,
                "grant_type": "authorization_code",
                "code": code,
                "redirect_uri": ORCID_REDIRECT_URI,
                "code_verifier": code_verifier,
            },
            headers={"Accept": "application/json"},
        )

    if token_response.status_code != 200:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Erro ao autenticar com ORCID: {token_response.text}",
        )

    token_data = token_response.json()
    orcid_id = token_data.get("orcid")
    name = token_data.get("name", "")
    access_token = token_data.get("access_token", "")

    if not orcid_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="ORCID ID não retornado na resposta.",
        )

    # Buscar dados do perfil público do ORCID
    perfil_orcid = await _buscar_perfil_orcid(orcid_id, access_token)

    # Upsert do usuário no MongoDB
    db = Database.get_db()

    orcid_data = {
        "orcid_id": orcid_id,
        "nome_orcid": name,
        "access_token": access_token,  # Em produção, criptografar
        "perfil_sincronizado_em": datetime.now(timezone.utc),
        "publicacoes": perfil_orcid.get("publicacoes", []),
        "educacao": perfil_orcid.get("educacao", []),
        "afiliacao_orcid": perfil_orcid.get("afiliacao"),
    }

    # Verificar se já existe usuário com este ORCID
    usuario_existente = await db.usuarios.find_one({"orcid.orcid_id": orcid_id})

    if usuario_existente:
        # Atualizar dados do ORCID
        await db.usuarios.update_one(
            {"_id": usuario_existente["_id"]},
            {
                "$set": {
                    "orcid": orcid_data,
                    "ultimo_login": datetime.now(timezone.utc),
                    "atualizado_em": datetime.now(timezone.utc),
                }
            },
        )
        usuario = await db.usuarios.find_one({"_id": usuario_existente["_id"]})
    else:
        # Criar novo usuário
        novo_usuario = {
            "email": f"{orcid_id}@orcid.placeholder",  # Placeholder até o usuário informar
            "nome": name or "Usuário ORCID",
            "papel": "pesquisador",  # Padrão para login via ORCID
            "orcid": orcid_data,
            "instituicao": perfil_orcid.get("afiliacao"),
            "interesses": [],
            "habilidades": [],
            "criado_em": datetime.now(timezone.utc),
            "atualizado_em": datetime.now(timezone.utc),
            "ultimo_login": datetime.now(timezone.utc),
            "ativo": True,
        }
        result = await db.usuarios.insert_one(novo_usuario)
        usuario = await db.usuarios.find_one({"_id": result.inserted_id})

    # Formatar resposta
    usuario["id"] = str(usuario["_id"])
    del usuario["_id"]
    usuario.pop("senha_hash", None)
    if "orcid" in usuario:
        usuario["orcid"].pop("access_token", None)

    return usuario


async def sincronizar_perfil_orcid(user_id: str) -> Dict[str, Any]:
    """Re-importa dados do ORCID para o perfil do usuário.

    Args:
        user_id: ID do usuário no MongoDB.

    Returns:
        Perfil atualizado com dados do ORCID.
    """
    from bson import ObjectId

    db = Database.get_db()
    usuario = await db.usuarios.find_one({"_id": ObjectId(user_id)})

    if not usuario:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Usuário não encontrado.",
        )

    orcid_data = usuario.get("orcid")
    if not orcid_data or not orcid_data.get("orcid_id"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Usuário não possui ORCID vinculado.",
        )

    orcid_id = orcid_data["orcid_id"]
    access_token = orcid_data.get("access_token", "")

    perfil_orcid = await _buscar_perfil_orcid(orcid_id, access_token)

    await db.usuarios.update_one(
        {"_id": ObjectId(user_id)},
        {
            "$set": {
                "orcid.publicacoes": perfil_orcid.get("publicacoes", []),
                "orcid.educacao": perfil_orcid.get("educacao", []),
                "orcid.afiliacao_orcid": perfil_orcid.get("afiliacao"),
                "orcid.perfil_sincronizado_em": datetime.now(timezone.utc),
                "atualizado_em": datetime.now(timezone.utc),
            }
        },
    )

    usuario_atualizado = await db.usuarios.find_one({"_id": ObjectId(user_id)})
    usuario_atualizado["id"] = str(usuario_atualizado["_id"])
    del usuario_atualizado["_id"]
    usuario_atualizado.pop("senha_hash", None)
    if "orcid" in usuario_atualizado:
        usuario_atualizado["orcid"].pop("access_token", None)

    return usuario_atualizado


async def _buscar_perfil_orcid(
    orcid_id: str, access_token: str
) -> Dict[str, Any]:
    """Busca dados do perfil público no ORCID API.

    Returns:
        Dict com 'publicacoes', 'educacao', 'afiliacao'.
    """
    resultado: Dict[str, Any] = {
        "publicacoes": [],
        "educacao": [],
        "afiliacao": None,
    }

    headers = {
        "Accept": "application/json",
        "Authorization": f"Bearer {access_token}",
    }

    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            # Buscar registro completo
            response = await client.get(
                f"{ORCID_API_URL}/{orcid_id}/record",
                headers=headers,
            )

            if response.status_code != 200:
                return resultado

            record = response.json()

            # Extrair educação
            educations = (
                record.get("activities-summary", {})
                .get("educations", {})
                .get("affiliation-group", [])
            )
            for group in educations:
                summaries = group.get("summaries", [])
                for summary in summaries:
                    edu = summary.get("education-summary", {})
                    resultado["educacao"].append({
                        "instituicao": edu.get("organization", {}).get("name", ""),
                        "grau": edu.get("role-title", ""),
                        "area": edu.get("department-name", ""),
                        "inicio": edu.get("start-date", {}).get("year", {}).get("value") if edu.get("start-date") else None,
                        "fim": edu.get("end-date", {}).get("year", {}).get("value") if edu.get("end-date") else None,
                    })

            # Extrair afiliação (emprego mais recente)
            employments = (
                record.get("activities-summary", {})
                .get("employments", {})
                .get("affiliation-group", [])
            )
            if employments:
                first_group = employments[0].get("summaries", [])
                if first_group:
                    emp = first_group[0].get("employment-summary", {})
                    resultado["afiliacao"] = emp.get("organization", {}).get("name")

            # Buscar publicações (works)
            works_response = await client.get(
                f"{ORCID_API_URL}/{orcid_id}/works",
                headers=headers,
            )

            if works_response.status_code == 200:
                works_data = works_response.json()
                work_groups = works_data.get("group", [])
                for group in work_groups[:20]:  # Limitar a 20 publicações
                    summaries = group.get("work-summary", [])
                    if summaries:
                        work = summaries[0]
                        pub = {
                            "titulo": work.get("title", {}).get("title", {}).get("value", ""),
                            "tipo": work.get("type", ""),
                            "ano": None,
                            "doi": None,
                        }
                        # Ano
                        pub_date = work.get("publication-date")
                        if pub_date and pub_date.get("year"):
                            try:
                                pub["ano"] = int(pub_date["year"]["value"])
                            except (ValueError, TypeError):
                                pass
                        # DOI
                        ext_ids = work.get("external-ids", {}).get("external-id", [])
                        for eid in ext_ids:
                            if eid.get("external-id-type") == "doi":
                                pub["doi"] = eid.get("external-id-value")
                                break

                        resultado["publicacoes"].append(pub)

    except httpx.TimeoutException:
        pass  # Retorna dados vazios se ORCID não responder
    except Exception:
        pass

    return resultado
