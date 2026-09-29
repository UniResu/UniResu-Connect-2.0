"""
Envio de e-mail transacional via API do Resend.

`enviar_email` nunca levanta exceção: devolve (enviado, provider_id) e
registra falhas em log. Quem chama decide o que fazer com o resultado.
"""

import asyncio
import logging
import os
from typing import Optional

import resend

logger = logging.getLogger(__name__)

# Remetente oficial (domínio uniresu.org verificado no Resend).
EMAIL_REMETENTE = os.getenv("EMAIL_REMETENTE", "UniResu <contato@uniresu.org>")

# Caixa institucional da equipe (respostas a e-mails do sistema e alertas).
EMAIL_SUPORTE = os.getenv("EMAIL_SUPORTE", "uniresuconnect@gmail.com")


async def enviar_email(params: dict) -> tuple[bool, Optional[str]]:
    """Envia `params` (formato resend.Emails.SendParams, sem o `from`)."""
    api_key = os.getenv("RESEND_API_KEY")
    if not api_key:
        logger.warning("RESEND_API_KEY ausente — e-mail '%s' NÃO foi enviado.", params.get("subject"))
        return False, None
    try:
        resend.api_key = api_key
        payload = {"from": EMAIL_REMETENTE, **params}
        # O SDK do Resend é síncrono; roda em thread para não bloquear o loop.
        resposta = await asyncio.to_thread(resend.Emails.send, payload)
        provider_id = resposta.get("id") if isinstance(resposta, dict) else None
        logger.info("E-mail '%s' enviado via Resend (id=%s)", params.get("subject"), provider_id)
        return True, provider_id
    except Exception as e:
        logger.error("Falha ao enviar e-mail via Resend: %s", e, exc_info=True)
        return False, None
