"""
Controller de candidatura.

Persiste a candidatura no banco e dispara um e-mail de notificação via
API do Resend (substitui o antigo envio SMTP via smtplib).

Regras importantes:
- O envio do e-mail é totalmente isolado: qualquer falha (rede, chave
  inválida, limite do Resend) é registrada em log e NÃO interrompe a
  candidatura. O aluno sempre recebe confirmação de sucesso.
- A candidatura é gravada no banco ANTES da chamada ao Resend — portanto
  permanece salva mesmo se a API falhar.
- Produção: domínio uniresu.org verificado no Resend. O remetente usa
  contato@uniresu.org e o reply_to aponta para a caixa institucional no
  Gmail, permitindo que respostas dos professores cheguem à equipe.
"""

import os
import base64
import asyncio
import logging
from datetime import datetime, timezone

import resend
from fastapi import HTTPException
from bson import ObjectId
from database.connection import Database

logger = logging.getLogger(__name__)

# Remetente oficial (domínio uniresu.org verificado no Resend).
# Lido de EMAIL_REMETENTE; fallback cobre ambientes sem env configurado.
EMAIL_REMETENTE = os.getenv("EMAIL_REMETENTE", "UniResu <contato@uniresu.org>")

# Caixa institucional de suporte que recebe as respostas (reply_to) quando
# o destinatário clica em "Responder" no cliente de e-mail.
EMAIL_SUPORTE = os.getenv("EMAIL_SUPORTE", "uniresuconnect@gmail.com")

# Configura a API key do Resend uma única vez, na importação do módulo.
resend.api_key = os.getenv("RESEND_API_KEY")


async def enviar_candidatura(
    projeto_id: str,
    email_aluno: str,
    curriculo_bytes: bytes,
    curriculo_filename: str,
    curriculo_content_type: str,
    usuario_atual: dict,
):
    if not usuario_atual:
        raise HTTPException(status_code=401, detail="Usuário não autenticado.")
    try:
        obj_id = ObjectId(projeto_id)
    except Exception:
        raise HTTPException(status_code=400, detail="ID de projeto inválido")

    db = Database.get_db()
    projeto = await db.projetos.find_one({"_id": obj_id})

    if not projeto:
        raise HTTPException(status_code=404, detail="Projeto não encontrado")

    email_professor = projeto.get("email_professor")
    if not email_professor:
        raise HTTPException(
            status_code=400,
            detail="Este projeto não possui um contato de professor configurado.",
        )

    titulo_projeto = projeto.get("titulo", "Projeto Acadêmico")
    nome_professor = projeto.get("nome_professor", "Professor(a)")

    # Identificador do aluno — prioriza o id já formatado pelo middleware
    # de autenticação, com fallback para o _id bruto do documento do Mongo.
    usuario_id = usuario_atual.get("id") or usuario_atual.get("_id")

    # Bloqueia candidatura duplicada ao mesmo projeto pelo mesmo aluno.
    # Verifica tanto por usuario_id quanto por email para cobrir usuários
    # legados sem id vinculado.
    filtro_duplicado = {
        "projeto_id": obj_id,
        "$or": [
            {"usuario_id": usuario_id},
            {"email_aluno": email_aluno},
        ],
    }
    candidatura_existente = await db.candidaturas.find_one(filtro_duplicado)
    if candidatura_existente:
        raise HTTPException(
            status_code=409,
            detail="Você já se candidatou a este projeto.",
        )

    # 1) Persiste a candidatura no banco ANTES do disparo de e-mail,
    #    para que a candidatura fique salva mesmo se a API do Resend falhar.
    candidatura_doc = {
        "projeto_id": obj_id,
        "titulo_projeto": titulo_projeto,
        "nome_professor": nome_professor,
        "email_professor_destino": email_professor,
        "email_aluno": email_aluno,
        "usuario_id": usuario_id,
        "curriculo_filename": curriculo_filename,
        "curriculo_content_type": curriculo_content_type,
        "status": "pendente",
        "mensagem": None,
        "data_candidatura": datetime.now(timezone.utc),
        "criada_em": datetime.now(timezone.utc),
        "email_enviado": False,
        "email_provider_id": None,
    }
    insert_result = await db.candidaturas.insert_one(candidatura_doc)
    candidatura_id = insert_result.inserted_id

    # 2) Tenta disparar o e-mail via Resend. Nunca propaga exceção.
    email_enviado, provider_id = await _tentar_enviar_email_resend(
        email_professor=email_professor,
        email_aluno=email_aluno,
        titulo_projeto=titulo_projeto,
        nome_professor=nome_professor,
        curriculo_bytes=curriculo_bytes,
        curriculo_filename=curriculo_filename,
        curriculo_content_type=curriculo_content_type,
    )

    # 3) Atualiza o registro com o resultado do envio (best-effort).
    if email_enviado:
        try:
            await db.candidaturas.update_one(
                {"_id": candidatura_id},
                {"$set": {"email_enviado": True, "email_provider_id": provider_id}},
            )
        except Exception as e:
            logger.warning("Não foi possível atualizar status de envio da candidatura %s: %s", candidatura_id, e)

    return {
        "status": "success",
        "message": "Candidatura enviada com sucesso!",
        "candidatura_id": str(candidatura_id),
        "email_enviado": email_enviado,
    }


async def _tentar_enviar_email_resend(
    email_professor: str,
    email_aluno: str,
    titulo_projeto: str,
    nome_professor: str,
    curriculo_bytes: bytes,
    curriculo_filename: str,
    curriculo_content_type: str,
):
    """
    Dispara o e-mail de candidatura via API do Resend.

    Retorna uma tupla (enviado: bool, provider_id: Optional[str]).
    Nunca levanta exceção — falhas são apenas logadas.
    """
    try:
        if not resend.api_key:
            logger.warning(
                "RESEND_API_KEY ausente. Candidatura persistida no banco, "
                "mas e-mail NÃO foi disparado."
            )
            return False, None

        corpo_texto = (
            f"Prezado(a) {nome_professor},\n\n"
            f"Você recebeu uma nova candidatura para o projeto "
            f"\"{titulo_projeto}\" através da plataforma UniResu Connect.\n\n"
            f"Dados do candidato:\n"
            f"- E-mail para contato: {email_aluno}\n\n"
            f"O currículo do candidato segue em anexo a este e-mail.\n\n"
            f"Para responder diretamente ao candidato, utilize o endereço "
            f"informado acima.\n\n"
            f"Atenciosamente,\n"
            f"Equipe UniResu Connect"
        )

        corpo_html = (
            f"<p>Prezado(a) {nome_professor},</p>"
            f"<p>Você recebeu uma nova candidatura para o projeto "
            f"<strong>{titulo_projeto}</strong> através da plataforma "
            f"<strong>UniResu Connect</strong>.</p>"
            f"<p><strong>Dados do candidato:</strong><br>"
            f"E-mail para contato: <a href=\"mailto:{email_aluno}\">{email_aluno}</a></p>"
            f"<p>O currículo do candidato segue em anexo a este e-mail.</p>"
            f"<p>Para responder diretamente ao candidato, utilize o endereço "
            f"informado acima.</p>"
            f"<p>Atenciosamente,<br><strong>Equipe UniResu Connect</strong></p>"
        )

        params: "resend.Emails.SendParams" = {
            "from": EMAIL_REMETENTE,
            "to": [email_professor],
            "reply_to": EMAIL_SUPORTE,
            "subject": f"Nova Candidatura Recebida: {titulo_projeto}",
            "text": corpo_texto,
            "html": corpo_html,
            "attachments": [
                {
                    "filename": curriculo_filename,
                    "content": base64.b64encode(curriculo_bytes).decode("ascii"),
                    "content_type": curriculo_content_type or "application/octet-stream",
                }
            ],
        }

        # O SDK do Resend é síncrono (requests); rodamos em thread para
        # não bloquear o event loop do FastAPI.
        resposta = await asyncio.to_thread(resend.Emails.send, params)

        provider_id = None
        if isinstance(resposta, dict):
            provider_id = resposta.get("id")

        logger.info(
            "E-mail de candidatura enviado via Resend (id=%s) para %s",
            provider_id,
            email_professor,
        )
        return True, provider_id

    except Exception as e:
        logger.error(
            "Falha ao enviar e-mail via Resend (candidatura confirmada mesmo assim): %s",
            e,
            exc_info=True,
        )
        return False, None


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
