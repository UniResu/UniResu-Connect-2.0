"""
Controller de candidatura com carta de intenção.

O aluno escreve uma carta de intenção, que vai no CORPO do e-mail ao
coordenador do projeto (o Lattes entra só como link no final — nunca como
anexo). O e-mail sai com reply_to no endereço do aluno, para o professor
responder direto, e o aluno recebe uma cópia de confirmação no e-mail da
CONTA logada — nunca no e-mail digitado no formulário, para que a
plataforma não possa ser usada para enviar texto livre a terceiros.

Regras importantes:
- A candidatura é gravada no banco ANTES do envio — permanece salva mesmo
  se a API do Resend falhar. Falhas de e-mail só são logadas.
- Rate limit por usuário (CANDIDATURA_LIMITE_HORA / CANDIDATURA_LIMITE_DIA)
  contado no próprio MongoDB, para valer entre todos os workers.
- Todo texto do aluno é escapado no HTML do e-mail.
"""

import html
import logging
import os
from datetime import datetime, timedelta, timezone

from fastapi import HTTPException
from bson import ObjectId
from database.connection import Database
from controllers.projeto_controller import email_contato
from models.candidatura_model import CandidaturaCreate
from services.email import EMAIL_SUPORTE, enviar_email

logger = logging.getLogger(__name__)

LIMITE_POR_HORA = int(os.getenv("CANDIDATURA_LIMITE_HORA", "5"))
LIMITE_POR_DIA = int(os.getenv("CANDIDATURA_LIMITE_DIA", "20"))


# ─────────────────────────────────────────────
#  Montagem dos e-mails (funções puras)
# ─────────────────────────────────────────────

def _assunto_seguro(texto: str, limite: int = 200) -> str:
    texto = " ".join((texto or "").split())
    return texto if len(texto) <= limite else texto[: limite - 1] + "…"


def _carta_html(carta: str) -> str:
    paragrafos = [p for p in carta.split("\n\n") if p.strip()]
    return "".join(
        '<p style="margin:0 0 12px">' + html.escape(p).replace("\n", "<br>") + "</p>"
        for p in paragrafos
    )


def montar_email_coordenador(projeto: dict, dados: CandidaturaCreate) -> dict:
    """E-mail ao coordenador: carta no corpo, Lattes como link no final."""
    titulo = projeto.get("titulo") or "Projeto Acadêmico"
    professor = projeto.get("nome_professor") or "Professor(a)"
    e = html.escape

    texto = (
        f"Prezado(a) {professor},\n\n"
        f"{dados.nome} ({dados.curso_periodo}) enviou, pela plataforma UniResu Connect, "
        f"uma carta de intenção para participar do projeto \"{titulo}\".\n\n"
        "──────── Carta de intenção ────────\n\n"
        f"{dados.carta}\n\n"
        "───────────────────────────────────\n\n"
        f"E-mail do(a) estudante: {dados.email}\n"
        "Para responder, basta usar a opção \"Responder\" do seu e-mail.\n"
    )
    corpo_html = (
        f"<p>Prezado(a) {e(professor)},</p>"
        f"<p><strong>{e(dados.nome)}</strong> ({e(dados.curso_periodo)}) enviou, pela plataforma "
        f"<strong>UniResu Connect</strong>, uma carta de intenção para participar do projeto "
        f"<strong>{e(titulo)}</strong>.</p>"
        '<h3 style="margin:24px 0 8px">Carta de intenção</h3>'
        '<div style="border-left:3px solid #7c3aed;padding:4px 0 4px 16px;margin:0 0 24px">'
        f"{_carta_html(dados.carta)}</div>"
        f'<p>E-mail do(a) estudante: <a href="mailto:{e(dados.email)}">{e(dados.email)}</a><br>'
        'Para responder, basta usar a opção "Responder" do seu e-mail.</p>'
    )
    if dados.lattes_url:
        texto += f"\nCurrículo Lattes: {dados.lattes_url}\n"
        corpo_html += (
            f'<p>Currículo Lattes: <a href="{e(dados.lattes_url, quote=True)}">'
            f"{e(dados.lattes_url)}</a></p>"
        )

    return {
        "to": [email_contato(projeto)],
        "reply_to": dados.email,
        "subject": _assunto_seguro(f"Carta de intenção — {titulo} — {dados.nome}"),
        "text": texto,
        "html": corpo_html,
    }


def montar_email_confirmacao(projeto: dict, dados: CandidaturaCreate, email_conta: str) -> dict:
    """Cópia de confirmação para o e-mail da conta do aluno (sem expor o do coordenador)."""
    titulo = projeto.get("titulo") or "Projeto Acadêmico"
    professor = projeto.get("nome_professor") or "o(a) coordenador(a)"
    e = html.escape
    texto = (
        f"Olá, {dados.nome}!\n\n"
        f"Sua carta de intenção para o projeto \"{titulo}\" foi enviada a {professor}. "
        "Quando houver resposta, ela chegará direto neste e-mail.\n\n"
        "Cópia da sua carta:\n\n"
        f"{dados.carta}\n\n"
        "Boa sorte!\nEquipe UniResu Connect"
    )
    corpo_html = (
        f"<p>Olá, {e(dados.nome)}!</p>"
        f"<p>Sua carta de intenção para o projeto <strong>{e(titulo)}</strong> foi enviada a "
        f"{e(professor)}. Quando houver resposta, ela chegará direto neste e-mail.</p>"
        '<h3 style="margin:24px 0 8px">Cópia da sua carta</h3>'
        '<div style="border-left:3px solid #7c3aed;padding:4px 0 4px 16px">'
        f"{_carta_html(dados.carta)}</div>"
        "<p>Boa sorte!<br><strong>Equipe UniResu Connect</strong></p>"
    )
    return {
        "to": [email_conta],
        "reply_to": EMAIL_SUPORTE,
        "subject": _assunto_seguro(f"Sua carta de intenção foi enviada — {titulo}"),
        "text": texto,
        "html": corpo_html,
    }


# ─────────────────────────────────────────────
#  Fluxo de candidatura
# ─────────────────────────────────────────────

async def _verificar_rate_limit(db, usuario_id) -> None:
    agora = datetime.now(timezone.utc)
    for janela, limite, texto in (
        (timedelta(hours=1), LIMITE_POR_HORA, "na última hora"),
        (timedelta(days=1), LIMITE_POR_DIA, "nas últimas 24 horas"),
    ):
        total = await db.candidaturas.count_documents(
            {"usuario_id": usuario_id, "data_candidatura": {"$gte": agora - janela}}
        )
        if total >= limite:
            raise HTTPException(
                status_code=429,
                detail=f"Você atingiu o limite de {limite} candidaturas {texto}. Tente novamente mais tarde.",
            )


async def enviar_candidatura(projeto_id: str, dados: CandidaturaCreate, usuario_atual: dict):
    if not usuario_atual:
        raise HTTPException(status_code=401, detail="Usuário não autenticado.")
    try:
        obj_id = ObjectId(projeto_id)
    except Exception:
        raise HTTPException(status_code=400, detail="ID de projeto inválido")

    db = Database.get_db()
    projeto = await db.projetos.find_one({"_id": obj_id})

    if not projeto or projeto.get("ativo") is False:
        raise HTTPException(status_code=404, detail="Projeto não encontrado")

    destino = email_contato(projeto)
    if not destino:
        raise HTTPException(
            status_code=400,
            detail="Este projeto ainda não tem contato cadastrado para receber candidaturas.",
        )

    # Identificador do aluno — prioriza o id já formatado pelo middleware
    # de autenticação, com fallback para o _id bruto do documento do Mongo.
    usuario_id = usuario_atual.get("id") or usuario_atual.get("_id")

    # Bloqueia candidatura duplicada ao mesmo projeto pelo mesmo aluno.
    # Verifica tanto por usuario_id quanto por email para cobrir usuários
    # legados sem id vinculado.
    candidatura_existente = await db.candidaturas.find_one({
        "projeto_id": obj_id,
        "$or": [{"usuario_id": usuario_id}, {"email_aluno": dados.email}],
    })
    if candidatura_existente:
        raise HTTPException(status_code=409, detail="Você já se candidatou a este projeto.")

    await _verificar_rate_limit(db, usuario_id)

    agora = datetime.now(timezone.utc)

    # 1) Persiste ANTES do envio — a candidatura fica salva mesmo se o
    #    Resend falhar.
    candidatura_doc = {
        "projeto_id": obj_id,
        "titulo_projeto": projeto.get("titulo", "Projeto Acadêmico"),
        "nome_professor": projeto.get("nome_professor", "Professor(a)"),
        "email_professor_destino": destino,
        "origem_projeto": projeto.get("origem", "manual"),
        "usuario_id": usuario_id,
        "email_conta": usuario_atual.get("email"),
        "nome_aluno": dados.nome,
        "curso_periodo": dados.curso_periodo,
        "email_aluno": dados.email,
        "lattes_url": dados.lattes_url,
        "carta_intencao": dados.carta,
        "status": "pendente",
        "mensagem": None,
        "data_candidatura": agora,
        "criada_em": agora,
        "email_enviado": False,
        "email_provider_id": None,
        "confirmacao_enviada": False,
    }
    candidatura_id = (await db.candidaturas.insert_one(candidatura_doc)).inserted_id

    # 2) E-mail ao coordenador + cópia ao aluno. Nunca propagam exceção.
    email_enviado, provider_id = await enviar_email(montar_email_coordenador(projeto, dados))
    confirmacao_enviada = False
    email_conta = usuario_atual.get("email")
    if email_enviado and email_conta:
        confirmacao_enviada, _ = await enviar_email(montar_email_confirmacao(projeto, dados, email_conta))

    # 3) Registra o resultado do envio (best-effort).
    try:
        await db.candidaturas.update_one(
            {"_id": candidatura_id},
            {"$set": {
                "email_enviado": email_enviado,
                "email_provider_id": provider_id,
                "confirmacao_enviada": confirmacao_enviada,
            }},
        )
    except Exception as e:
        logger.warning("Não foi possível atualizar status de envio da candidatura %s: %s", candidatura_id, e)

    return {
        "status": "success",
        "message": "Candidatura enviada com sucesso!",
        "candidatura_id": str(candidatura_id),
        "email_enviado": email_enviado,
        "confirmacao_enviada": confirmacao_enviada,
    }


async def listar_candidaturas_do_aluno(usuario_atual: dict) -> list[dict]:
    """
    Retorna todas as candidaturas enviadas pelo aluno logado.

    Cada item inclui dados desnormalizados do projeto (título e nome do
    professor). Quando esses campos não estão gravados na candidatura
    (registros antigos), faz-se um join pontual com a coleção `projetos`.
    """
    if not usuario_atual:
        raise HTTPException(status_code=401, detail="Usuário não autenticado.")

    db = Database.get_db()

    usuario_id = usuario_atual.get("id") or usuario_atual.get("_id")
    email_aluno = usuario_atual.get("email")

    # Filtro amplo: registros antigos podem ter só email_aluno; registros
    # novos têm usuario_id. Cobrimos ambos com $or.
    filtros = []
    if usuario_id:
        filtros.append({"usuario_id": usuario_id})
    if email_aluno:
        filtros.append({"email_aluno": email_aluno})

    if not filtros:
        return []

    query = filtros[0] if len(filtros) == 1 else {"$or": filtros}

    cursor = db.candidaturas.find(query).sort("data_candidatura", -1)
    docs = await cursor.to_list(length=500)

    # Cache de projetos para evitar N consultas em listas grandes.
    cache_projetos: dict[str, dict] = {}

    resultado: list[dict] = []
    for doc in docs:
        projeto_id = doc.get("projeto_id")
        titulo = doc.get("titulo_projeto")
        nome_prof = doc.get("nome_professor")

        # Hidrata título/nome do professor a partir da coleção projetos
        # se a candidatura não os tem salvos (registros legados).
        if (not titulo or not nome_prof) and isinstance(projeto_id, ObjectId):
            key = str(projeto_id)
            projeto = cache_projetos.get(key)
            if projeto is None:
                projeto = await db.projetos.find_one(
                    {"_id": projeto_id},
                    {"titulo": 1, "nome_professor": 1},
                )
                cache_projetos[key] = projeto or {}
            if projeto:
                titulo = titulo or projeto.get("titulo")
                nome_prof = nome_prof or projeto.get("nome_professor")

        data_candidatura = (
            doc.get("data_candidatura")
            or doc.get("criada_em")
            or datetime.now(timezone.utc)
        )

        resultado.append({
            "id": str(doc["_id"]),
            "id_projeto": str(projeto_id) if projeto_id else "",
            "id_aluno": str(doc.get("usuario_id")) if doc.get("usuario_id") else None,
            "email_aluno": doc.get("email_aluno", ""),
            "data_candidatura": data_candidatura,
            "status": doc.get("status", "pendente"),
            "mensagem": doc.get("mensagem"),
            "titulo_projeto": titulo or "Projeto Acadêmico",
            "nome_professor": nome_prof or "Professor(a)",
        })

    return resultado
