"""
Controller de projetos — lógica de busca e formatação.

Usa Motor (async) e paginação baseada em cursor para escalar
com grandes volumes de dados.
"""

import re
from datetime import timezone
from typing import List, Optional, Dict, Any
from bson import ObjectId
from database.connection import Database
from services.sigaa.parser import SITUACAO_EM_EXECUCAO, normalizar


def formatar_projeto(doc: Dict[str, Any]) -> Dict[str, Any]:
    """Converte _id para string e ajusta nomes de campos para o frontend."""
    if doc is None:
        return None
    if "_id" in doc:
        doc["id"] = str(doc["_id"])
        del doc["_id"]

    tipo_map = {
        "institucional_exclusivo": "Projeto Institucional (Exclusivo)",
        "voluntario_aberto": "Projeto Voluntário (Aberto)",
    }
    if "tipo_projeto" in doc:
        doc["tipo"] = tipo_map.get(doc["tipo_projeto"], doc["tipo_projeto"])

    if "data_publicacao" in doc:
        doc["dataPublicacao"] = "Publicado recentemente"

    doc["tem_contato"] = bool(email_contato(doc))

    return doc


def email_contato(projeto: Dict[str, Any]) -> Optional[str]:
    """E-mail que recebe as candidaturas. O cadastro manual do admin
    (`email_contato_manual`) tem prioridade sobre o coletado do SIGAA."""
    return projeto.get("email_contato_manual") or projeto.get("email_professor") or None


def formatar_projeto_publico(doc: Dict[str, Any]) -> Dict[str, Any]:
    """Como `formatar_projeto`, mas sem dados de contato (resposta pública)."""
    doc = formatar_projeto(doc)
    for campo in ("email_professor", "email_contato_manual", "autor_email"):
        doc.pop(campo, None)
    return doc


async def buscar_projetos_controller(
    q: Optional[str] = None,
    local: Optional[str] = None,
    area: Optional[str] = None,
    remoto: bool = False,
    tipos: Optional[str] = None,
    tipo_sigaa: Optional[str] = None,
    unidade: Optional[str] = None,
    incluir_inativos: bool = False,
    last_id: Optional[str] = None,
    page_size: int = 20,
) -> List[Dict[str, Any]]:
    """Busca projetos com filtros e paginação baseada em cursor.

    Args:
        q: Texto para busca em título, descrição e professor/coordenador.
        local: Filtro por localidade.
        area: Filtro por área de estudo.
        remoto: Filtro para projetos remotos.
        tipos: Lista de tipos separados por vírgula.
        tipo_sigaa: "pesquisa" ou "extensao" (projetos importados do SIGAA).
        unidade: Unidade/departamento (valor exato, vindo de /projetos/unidades).
        incluir_inativos: Se False (padrão), mostra só projetos ativos e em
            execução — projetos manuais, sem situação, contam como ativos.
        last_id: ID do último item da página anterior (paginação por cursor).
        page_size: Número de itens por página (máx. 50).

    Returns:
        Lista de projetos formatados (sem e-mails de contato).
    """
    db = Database.get_db()

    # Limitar page_size
    page_size = min(page_size, 50)

    query_filter: Dict[str, Any] = {}
    and_clauses = []

    if q:
        termo = re.escape(q.strip())
        and_clauses.append({
            "$or": [
                {"titulo": {"$regex": termo, "$options": "i"}},
                {"descricao": {"$regex": termo, "$options": "i"}},
                {"nome_professor": {"$regex": termo, "$options": "i"}},
            ]
        })
    if not incluir_inativos:
        query_filter["ativo"] = {"$ne": False}
        # $in com None também casa documentos sem o campo (projetos manuais).
        query_filter["situacao"] = {"$in": [SITUACAO_EM_EXECUCAO, None]}
    if tipo_sigaa:
        query_filter["tipo_sigaa"] = tipo_sigaa
    if unidade:
        query_filter["unidade"] = unidade
    if local:
        query_filter["local"] = {"$regex": local, "$options": "i"}
    if area:
        query_filter["area_estudo"] = {"$regex": area, "$options": "i"}
    if remoto:
        and_clauses.append({
            "$or": [
                {"e_remoto": True},
                {"modalidade": {"$regex": "remoto|online|distância|distancia", "$options": "i"}}
            ]
        })
    if tipos:
        lista_de_tipos = [t.strip() for t in tipos.split(",") if t.strip()]
        if lista_de_tipos:
            query_filter["tipo_projeto"] = {"$in": lista_de_tipos}

    if and_clauses:
        query_filter["$and"] = and_clauses

    # Paginação por cursor (mais eficiente que skip/limit para grandes volumes)
    if last_id:
        try:
            query_filter["_id"] = {"$gt": ObjectId(last_id)}
        except Exception:
            pass  # Ignora last_id inválido

    try:
        cursor = db.projetos.find(query_filter).sort("_id", 1).limit(page_size)
        resultados = await cursor.to_list(length=page_size)
        return [formatar_projeto_publico(doc) for doc in resultados]

    except Exception as e:
        print(f"❌ Erro na consulta ao MongoDB: {e}")
        return []


async def listar_unidades_controller(tipo_sigaa: Optional[str] = None) -> List[str]:
    """Unidades/departamentos distintos dos projetos ativos (para o filtro)."""
    db = Database.get_db()
    filtro: Dict[str, Any] = {"ativo": {"$ne": False}, "unidade": {"$nin": [None, ""]}}
    if tipo_sigaa:
        filtro["tipo_sigaa"] = tipo_sigaa
    unidades = await db.projetos.distinct("unidade", filtro)
    return sorted(unidades, key=normalizar)


async def status_sigaa_controller() -> Dict[str, Any]:
    """Data da última execução bem-sucedida do sync com o SIGAA."""
    db = Database.get_db()
    run = await db.sigaa_sync_runs.find_one(
        {"status": {"$in": ["sucesso", "sucesso_com_erros"]}},
        sort=[("finalizada_em", -1)],
    )
    if not run or not run.get("finalizada_em"):
        return {"ultima_atualizacao": None}
    finalizada = run["finalizada_em"]
    if finalizada.tzinfo is None:  # Mongo devolve datetimes "naive" em UTC
        finalizada = finalizada.replace(tzinfo=timezone.utc)
    return {"ultima_atualizacao": finalizada.isoformat()}


# ═══════════════════════════════════════════════════
#  CRUD — Criação, Edição, Exclusão de Projetos
# ═══════════════════════════════════════════════════


async def criar_projeto_controller(dados: Dict[str, Any], usuario: Dict[str, Any]) -> Dict[str, Any]:
    """Cria um novo projeto vinculado ao professor/pesquisador."""
    from datetime import datetime, timezone

    db = Database.get_db()

    projeto_doc = {
        **dados,
        "autor_id": usuario["id"],
        "autor_email": usuario.get("email"),
        "data_publicacao": datetime.now(timezone.utc).isoformat(),
        "e_remoto": dados.get("modalidade", "").lower() in ("remoto", "online", "a distância"),
    }

    resultado = await db.projetos.insert_one(projeto_doc)
    projeto_doc["_id"] = resultado.inserted_id

    return formatar_projeto(projeto_doc)


async def listar_meus_projetos(usuario: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Lista todos os projetos criados pelo professor/pesquisador logado."""
    db = Database.get_db()

    cursor = db.projetos.find({"autor_id": usuario["id"]}).sort("_id", -1)
    resultados = await cursor.to_list(length=100)

    return [formatar_projeto(doc) for doc in resultados]


async def editar_projeto_controller(
    projeto_id: str, dados: Dict[str, Any], usuario: Dict[str, Any]
) -> Dict[str, Any]:
    """Edita um projeto existente (somente o autor pode editar)."""
    db = Database.get_db()

    try:
        oid = ObjectId(projeto_id)
    except Exception:
        return None

    projeto = await db.projetos.find_one({"_id": oid})
    if not projeto:
        return None

    # Verifica autoria
    if projeto.get("autor_id") != usuario["id"]:
        raise PermissionError("Você não tem permissão para editar este projeto.")

    # Atualiza o campo e_remoto com base na modalidade
    dados["e_remoto"] = dados.get("modalidade", "").lower() in ("remoto", "online", "a distância")

    await db.projetos.update_one({"_id": oid}, {"$set": dados})

    atualizado = await db.projetos.find_one({"_id": oid})
    return formatar_projeto(atualizado)


async def deletar_projeto_controller(projeto_id: str, usuario: Dict[str, Any]) -> bool:
    """Exclui um projeto (somente o autor pode excluir)."""
    db = Database.get_db()

    try:
        oid = ObjectId(projeto_id)
    except Exception:
        return False

    projeto = await db.projetos.find_one({"_id": oid})
    if not projeto:
        return False

    if projeto.get("autor_id") != usuario["id"]:
        raise PermissionError("Você não tem permissão para excluir este projeto.")

    result = await db.projetos.delete_one({"_id": oid})
    return result.deleted_count > 0