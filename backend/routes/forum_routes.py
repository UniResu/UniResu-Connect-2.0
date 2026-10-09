"""
Rotas do fórum: tópicos (perguntas) com reações (Like/Dislike) e respostas.

Respostas têm um único nível: respondem ao tópico, nunca a outra resposta.
Ficam na collection `respostas_forum` ({topico_id, autor_id, conteudo,
data_criacao, editado_em?}) e o tópico guarda o contador `total_respostas`,
atualizado com `$inc` ao criar e ao excluir uma resposta.

Privacidade: nenhuma resposta desta API contém e-mail. O autor aparece como
`autor_username` + `autor_nome`, resolvidos a partir de `autor_id` com UMA
consulta em lote na collection `usuarios` (ver `anexar_autores`).

Rotas protegidas usam Depends(get_usuario_com_perfil_completo) para autenticação.
"""

from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, Query, status
from typing import List, Dict, Any, Optional
from bson import ObjectId
from pymongo import ReturnDocument
from database.connection import Database
from models.forum_model import (
    RespostaCreate,
    RespostaResponse,
    RespostasPagina,
    RespostaUpdate,
    TopicoCreate,
    TopicoDetalhe,
    TopicoResponse,
    TopicoUpdate,
)
from auth.autenticacao import get_usuario_com_perfil_completo

router = APIRouter()

# Rótulos de autor quando `autor_id` não aponta para um usuário existente
# (tópicos legados, só com e-mail, ou conta apagada).
AUTOR_DESCONHECIDO_USERNAME = "usuario"
AUTOR_DESCONHECIDO_NOME = "Usuário"

# Respostas devolvidas junto com o tópico (a thread aberta em /forum mostra
# até 10) e tamanho máximo de uma página de respostas (/forum/[id] carrega 50).
RESPOSTAS_NA_THREAD = 10
RESPOSTAS_POR_PAGINA_MAX = 50


# ── Helpers ─────────────────────────────────────────────────────────────────

def _lista_de_ids(valor: Any) -> List[str]:
    """Docs legados guardavam `likes: 0`; hoje é lista de IDs de usuários."""
    if not isinstance(valor, list):
        return []
    return [str(v) for v in valor]


def formatar_topico(doc: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Converte _id para string 'id' e remove o que não pode sair da API."""
    if doc is None:
        return None
    doc = dict(doc)
    if "_id" in doc:
        doc["id"] = str(doc["_id"])
        del doc["_id"]
    # Privacidade: o e-mail fica no banco (checagem de autoria legada) e só lá.
    doc.pop("autor_email", None)
    doc["likes"] = _lista_de_ids(doc.get("likes"))
    doc["dislikes"] = _lista_de_ids(doc.get("dislikes"))
    doc.setdefault("autor_username", AUTOR_DESCONHECIDO_USERNAME)
    doc.setdefault("autor_nome", AUTOR_DESCONHECIDO_NOME)
    # Tópicos criados antes das respostas não têm o contador.
    doc["total_respostas"] = max(int(doc.get("total_respostas") or 0), 0)
    return doc


def formatar_resposta(doc: Dict[str, Any]) -> Dict[str, Any]:
    """Mesma ideia de `formatar_topico`: `_id` vira `id` e e-mail nunca sai."""
    doc = dict(doc)
    if "_id" in doc:
        doc["id"] = str(doc.pop("_id"))
    doc.pop("autor_email", None)
    doc.setdefault("autor_username", AUTOR_DESCONHECIDO_USERNAME)
    doc.setdefault("autor_nome", AUTOR_DESCONHECIDO_NOME)
    return doc


def nome_de_exibicao(usuario: Dict[str, Any]) -> str:
    return usuario.get("nome_social") or usuario.get("nome") or AUTOR_DESCONHECIDO_NOME


async def anexar_autores(db, docs: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Preenche `autor_username`/`autor_nome` em cada tópico ou resposta, in place.

    Uma única `find` com `$in` sobre os `autor_id` válidos (projeção mínima:
    username, nome, nome_social). Quem não for encontrado recebe os rótulos
    de autor desconhecido — nunca o e-mail.
    """
    ids = set()
    for doc in docs:
        autor_id = doc.get("autor_id")
        if autor_id and ObjectId.is_valid(str(autor_id)):
            ids.add(ObjectId(str(autor_id)))

    autores: Dict[str, Dict[str, Any]] = {}
    if ids:
        cursor = db.usuarios.find(
            {"_id": {"$in": list(ids)}},
            {"username": 1, "nome": 1, "nome_social": 1},
        )
        for usuario in await cursor.to_list(length=len(ids)):
            autores[str(usuario["_id"])] = usuario

    for doc in docs:
        usuario = autores.get(str(doc.get("autor_id") or ""))
        if usuario:
            doc["autor_username"] = usuario.get("username") or AUTOR_DESCONHECIDO_USERNAME
            doc["autor_nome"] = nome_de_exibicao(usuario)
        else:
            doc["autor_username"] = AUTOR_DESCONHECIDO_USERNAME
            doc["autor_nome"] = AUTOR_DESCONHECIDO_NOME
    return docs


async def responder_topico(db, doc: Dict[str, Any]) -> Dict[str, Any]:
    """Resposta de um único tópico: resolve o autor e formata."""
    await anexar_autores(db, [doc])
    return formatar_topico(doc)


async def responder_resposta(db, doc: Dict[str, Any]) -> Dict[str, Any]:
    """Uma única resposta do fórum: resolve o autor e formata."""
    await anexar_autores(db, [doc])
    return formatar_resposta(doc)


async def buscar_respostas(db, topico_id: str, limite: int, pular: int = 0) -> List[Dict[str, Any]]:
    """Respostas de um tópico, da mais antiga para a mais nova.

    O `_id` desempata respostas gravadas no mesmo milissegundo, para que a
    paginação com `pular` não repita nem perca nenhuma.
    """
    if limite <= 0:
        return []
    cursor = (
        db.respostas_forum.find({"topico_id": topico_id})
        .sort([("data_criacao", 1), ("_id", 1)])
        .skip(pular)
        .limit(limite)
    )
    return await cursor.to_list(length=limite)

def extrair_id_usuario(usuario_logado: Any) -> str:
    """Obtém o ID do usuário autenticado de forma segura.

    Por que: `get_usuario_atual` (em auth/autenticacao.py) já normaliza o
    documento convertendo `_id` → `id` (string) e removendo `_id`. Documentos
    crus vindos direto do Mongo, porém, têm apenas `_id` (ObjectId). Esta
    função cobre ambos os formatos e também o caso de objeto com atributos,
    evitando KeyError/AttributeError em runtime.
    """
    if usuario_logado is None:
        return ""
    # Caso 1: dict no formato já normalizado pelo dependency de auth
    if isinstance(usuario_logado, dict):
        valor = usuario_logado.get("id") or usuario_logado.get("_id")
        return str(valor) if valor is not None else ""
    # Caso 2: objeto com atributos (modelo Pydantic, etc.)
    valor = getattr(usuario_logado, "id", None) or getattr(usuario_logado, "_id", None)
    return str(valor) if valor is not None else ""


def extrair_email_usuario(usuario_logado: Any) -> str:
    """Obtém o email do usuário autenticado, tolerando dict ou objeto.

    Usado SOMENTE na checagem de autoria de documentos legados (que só têm
    `autor_email`); nunca entra em resposta.
    """
    if usuario_logado is None:
        return ""
    if isinstance(usuario_logado, dict):
        return usuario_logado.get("email", "") or ""
    return getattr(usuario_logado, "email", "") or ""


def eh_autor(doc: Dict[str, Any], usuario_logado: Any) -> bool:
    """Autoria (de tópico ou resposta) por `autor_id`; e-mail só como fallback
    de tópicos legados (respostas nunca gravam e-mail)."""
    id_logado = extrair_id_usuario(usuario_logado)
    email_logado = extrair_email_usuario(usuario_logado)
    return bool(
        (id_logado and str(doc.get("autor_id", "")) == id_logado)
        or (email_logado and doc.get("autor_email") == email_logado)
    )


def _object_id(topico_id: str) -> ObjectId:
    try:
        return ObjectId(topico_id)
    except Exception:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="ID inválido.")


async def _exigir_topico(db, oid: ObjectId) -> None:
    if not await db.topicos_forum.find_one({"_id": oid}, {"_id": 1}):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tópico não encontrado.")


async def _resposta_do_autor(db, resposta_id: str, usuario_logado: Any, acao: str) -> Dict[str, Any]:
    """Carrega a resposta e confere a autoria (404 se não existe, 403 se é de outra pessoa)."""
    resposta = await db.respostas_forum.find_one({"_id": _object_id(resposta_id)})
    if not resposta:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Resposta não encontrada.")
    if not eh_autor(resposta, usuario_logado):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Apenas o autor pode {acao} esta resposta.",
        )
    return resposta


# ── Rotas ───────────────────────────────────────────────────────────────────

@router.get("/forum/topicos", response_model=List[TopicoResponse])
async def listar_topicos(limite: int = Query(100, ge=1, le=100)):
    """Lista os tópicos do fórum, do mais recente ao mais antigo (rota
    pública). `limite` serve à página inicial, que mostra só os três últimos."""
    db = Database.get_db()
    try:
        cursor = db.topicos_forum.find({}).sort("data_criacao", -1).limit(limite)
        lista_docs = await cursor.to_list(length=limite)
        await anexar_autores(db, lista_docs)
        return [formatar_topico(doc) for doc in lista_docs]
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro ao listar tópicos: {e}",
        )


@router.get("/forum/topicos/{topico_id}", response_model=TopicoDetalhe)
async def obter_topico(
    topico_id: str,
    limite_respostas: int = Query(RESPOSTAS_NA_THREAD, ge=0, le=RESPOSTAS_POR_PAGINA_MAX),
):
    """Devolve um tópico com as primeiras respostas e conta uma visualização
    (rota pública).

    O `$inc` é atômico no servidor: duas aberturas simultâneas somam 2. Os
    autores do tópico e das respostas saem da mesma consulta em lote.
    """
    db = Database.get_db()
    oid = _object_id(topico_id)
    topico = await db.topicos_forum.find_one_and_update(
        {"_id": oid},
        {"$inc": {"visualizacoes": 1}},
        return_document=ReturnDocument.AFTER,
    )
    if not topico:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tópico não encontrado.")
    respostas = await buscar_respostas(db, str(oid), limite_respostas)
    await anexar_autores(db, [topico, *respostas])
    detalhe = formatar_topico(topico)
    detalhe["respostas"] = [formatar_resposta(r) for r in respostas]
    return detalhe


@router.post(
    "/forum/topicos",
    response_model=TopicoResponse,
    status_code=status.HTTP_201_CREATED,
)
async def criar_topico(
    topico: TopicoCreate,
    usuario_logado: dict = Depends(get_usuario_com_perfil_completo),
):
    """Cria um novo tópico no fórum (requer autenticação)."""
    db = Database.get_db()

    # Só `autor_id`: o autor é resolvido na leitura, e o e-mail não é gravado
    # no tópico (nada a vazar).
    novo_topico_doc = {
        "titulo": topico.titulo,
        "conteudo_original": topico.conteudo,
        "autor_id": extrair_id_usuario(usuario_logado),
        "data_criacao": datetime.now(timezone.utc),
        "visualizacoes": 0,
        # Reações: listas de IDs de usuários para garantir 1 voto por usuário
        "likes": [],
        "dislikes": [],
        "total_respostas": 0,
    }

    try:
        result = await db.topicos_forum.insert_one(novo_topico_doc)
        topico_criado = await db.topicos_forum.find_one({"_id": result.inserted_id})
        if not topico_criado:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Erro ao criar tópico.",
            )
        return await responder_topico(db, topico_criado)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro ao criar tópico: {e}",
        )


@router.patch("/forum/topicos/{topico_id}", response_model=TopicoResponse)
async def editar_topico(
    topico_id: str,
    dados: TopicoUpdate,
    usuario_logado: dict = Depends(get_usuario_com_perfil_completo),
):
    """Edita título e/ou conteúdo de um tópico. Apenas o autor pode editar."""
    db = Database.get_db()
    oid = _object_id(topico_id)

    topico = await db.topicos_forum.find_one({"_id": oid})
    if not topico:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tópico não encontrado.")

    if not eh_autor(topico, usuario_logado):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Apenas o autor pode editar este tópico.",
        )

    campos_para_atualizar = {}
    if dados.titulo is not None:
        campos_para_atualizar["titulo"] = dados.titulo
    if dados.conteudo is not None:
        campos_para_atualizar["conteudo_original"] = dados.conteudo

    if not campos_para_atualizar:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Nenhum campo para atualizar.")

    await db.topicos_forum.update_one({"_id": oid}, {"$set": campos_para_atualizar})

    topico_atualizado = await db.topicos_forum.find_one({"_id": oid})
    return await responder_topico(db, topico_atualizado)


@router.delete("/forum/topicos/{topico_id}", status_code=status.HTTP_204_NO_CONTENT)
async def excluir_topico(
    topico_id: str,
    usuario_logado: dict = Depends(get_usuario_com_perfil_completo),
):
    """Exclui um tópico e as respostas dele. Apenas o autor pode excluir."""
    db = Database.get_db()
    oid = _object_id(topico_id)

    topico = await db.topicos_forum.find_one({"_id": oid})
    if not topico:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tópico não encontrado.")

    if not eh_autor(topico, usuario_logado):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Apenas o autor pode excluir este tópico.",
        )

    await db.topicos_forum.delete_one({"_id": oid})
    await db.respostas_forum.delete_many({"topico_id": str(oid)})


@router.post("/forum/topicos/{topico_id}/reagir", response_model=TopicoResponse)
async def reagir_topico(
    topico_id: str,
    # Espera JSON: { "tipo": "like" } ou { "tipo": "dislike" }
    payload: dict,
    usuario_logado: dict = Depends(get_usuario_com_perfil_completo),
):
    """
    Registra ou remove uma reação (like/dislike) de um tópico.
    - Se o usuário já reagiu com o mesmo tipo → remove (toggle off).
    - Se o usuário reagiu com o tipo oposto → troca de reação.
    - Um usuário não pode dar like e dislike ao mesmo tempo.
    """
    db = Database.get_db()

    tipo = payload.get("tipo")
    if tipo not in ("like", "dislike"):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Tipo deve ser 'like' ou 'dislike'.")

    usuario_id = extrair_id_usuario(usuario_logado)
    if not usuario_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Não foi possível identificar o usuário autenticado.",
        )

    oid = _object_id(topico_id)
    topico = await db.topicos_forum.find_one({"_id": oid})
    if not topico:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tópico não encontrado.")

    campo = "likes" if tipo == "like" else "dislikes"
    oposto = "dislikes" if tipo == "like" else "likes"

    # Docs legados guardavam `likes: 0`: viram listas antes dos operadores de
    # array (um `$set` só nos campos que ainda não são lista).
    legados = {c: [] for c in ("likes", "dislikes") if not isinstance(topico.get(c), list)}
    if legados:
        await db.topicos_forum.update_one({"_id": oid}, {"$set": legados})

    # Operadores atômicos no servidor: votos simultâneos de pessoas diferentes
    # não se sobrescrevem (o read-modify-write anterior perdia votos).
    # 1) já tinha este voto → remove (toggle off); 2) senão → adiciona e tira o oposto.
    removido = await db.topicos_forum.update_one(
        {"_id": oid, campo: usuario_id}, {"$pull": {campo: usuario_id}},
    )
    if removido.modified_count == 0:
        await db.topicos_forum.update_one(
            {"_id": oid}, {"$addToSet": {campo: usuario_id}, "$pull": {oposto: usuario_id}},
        )

    topico_atualizado = await db.topicos_forum.find_one({"_id": oid})
    return await responder_topico(db, topico_atualizado)


# ── Respostas ───────────────────────────────────────────────────────────────

@router.get("/forum/topicos/{topico_id}/respostas", response_model=RespostasPagina)
async def listar_respostas(
    topico_id: str,
    limite: int = Query(RESPOSTAS_NA_THREAD, ge=1, le=RESPOSTAS_POR_PAGINA_MAX),
    pular: int = Query(0, ge=0),
):
    """Uma página de respostas de um tópico, da mais antiga para a mais nova,
    com o total do tópico (rota pública)."""
    db = Database.get_db()
    oid = _object_id(topico_id)
    await _exigir_topico(db, oid)

    total = await db.respostas_forum.count_documents({"topico_id": str(oid)})
    respostas = await buscar_respostas(db, str(oid), limite, pular)
    await anexar_autores(db, respostas)
    return {"total": total, "respostas": [formatar_resposta(r) for r in respostas]}


@router.post(
    "/forum/topicos/{topico_id}/respostas",
    response_model=RespostaResponse,
    status_code=status.HTTP_201_CREATED,
)
async def criar_resposta(
    topico_id: str,
    dados: RespostaCreate,
    usuario_logado: dict = Depends(get_usuario_com_perfil_completo),
):
    """Responde a um tópico (requer perfil completo). O conteúdo chega sem os
    espaços das pontas e com 1 a 5.000 caracteres (validado no modelo)."""
    db = Database.get_db()
    oid = _object_id(topico_id)

    autor_id = extrair_id_usuario(usuario_logado)
    if not autor_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Não foi possível identificar o usuário autenticado.",
        )

    await _exigir_topico(db, oid)

    # Só `autor_id`, como nos tópicos: o e-mail não é gravado na resposta.
    nova = {
        "topico_id": str(oid),
        "autor_id": autor_id,
        "conteudo": dados.conteudo,
        "data_criacao": datetime.now(timezone.utc),
    }
    resultado = await db.respostas_forum.insert_one(nova)
    nova["_id"] = resultado.inserted_id

    contado = await db.topicos_forum.update_one({"_id": oid}, {"$inc": {"total_respostas": 1}})
    if contado.matched_count == 0:
        # O tópico foi excluído entre a checagem e o insert: a resposta não fica órfã.
        await db.respostas_forum.delete_one({"_id": resultado.inserted_id})
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tópico não encontrado.")

    return await responder_resposta(db, nova)


@router.patch("/forum/respostas/{resposta_id}", response_model=RespostaResponse)
async def editar_resposta(
    resposta_id: str,
    dados: RespostaUpdate,
    usuario_logado: dict = Depends(get_usuario_com_perfil_completo),
):
    """Substitui o texto de uma resposta. Apenas o autor pode editar."""
    db = Database.get_db()
    resposta = await _resposta_do_autor(db, resposta_id, usuario_logado, "editar")

    atualizada = await db.respostas_forum.find_one_and_update(
        {"_id": resposta["_id"]},
        {"$set": {"conteudo": dados.conteudo, "editado_em": datetime.now(timezone.utc)}},
        return_document=ReturnDocument.AFTER,
    )
    if not atualizada:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Resposta não encontrada.")
    return await responder_resposta(db, atualizada)


@router.delete("/forum/respostas/{resposta_id}", status_code=status.HTTP_204_NO_CONTENT)
async def excluir_resposta(
    resposta_id: str,
    usuario_logado: dict = Depends(get_usuario_com_perfil_completo),
):
    """Exclui uma resposta e desconta do tópico. Apenas o autor pode excluir."""
    db = Database.get_db()
    resposta = await _resposta_do_autor(db, resposta_id, usuario_logado, "excluir")

    removida = await db.respostas_forum.delete_one({"_id": resposta["_id"]})
    # Só quem de fato removeu desconta: dois DELETEs simultâneos tiram 1, não 2.
    topico_id = str(resposta.get("topico_id") or "")
    if removida.deleted_count and ObjectId.is_valid(topico_id):
        await db.topicos_forum.update_one(
            {"_id": ObjectId(topico_id), "total_respostas": {"$gt": 0}},
            {"$inc": {"total_respostas": -1}},
        )
