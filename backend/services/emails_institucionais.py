"""
Validação de e-mail institucional acadêmico (registro e troca do e-mail
provisório criado pelo login via ORCID).

Regra:
  - Aceita qualquer domínio terminado em '.edu.br' ou '.edu'.
  - Aceita os domínios listados em DOMINIOS_PERMITIDOS, inclusive
    subdomínios (ex.: 'sga.pucminas.br' termina em '.pucminas.br').
"""

import re

DOMINIOS_PERMITIDOS = {
    # Federais
    "ufrj.br", "ufmg.br", "unb.br", "ufrgs.br", "ufsc.br",
    "ufpr.br", "ufpe.br", "ufba.br", "ufg.br", "ufrn.br",
    "ufv.br", "ufscar.br", "unifesp.br", "ufc.br", "ufu.br",
    "unir.br", "unirio.br",
    # Estaduais
    "usp.br", "unicamp.br", "unesp.br", "uerj.br", "udesc.br",
    "uems.br", "unemat.br", "uenp.br",
    # PUCs
    "pucminas.br", "puc-rio.br", "pucsp.br", "pucpr.br",
    "pucrs.br", "puccampinas.edu.br",
    # Privadas e institutos
    "fgv.br", "insper.edu.br", "mackenzie.br", "einstein.br",
    "fia.com.br", "senai.br", "itajuba.edu.br", "ita.br",
    "ime.eb.mil.br",
}

SUFIXO_PROVISORIO = "@orcid.placeholder"


def filtro_email(email: str, campo: str = "email") -> dict:
    """Filtro de igualdade sem distinção de maiúsculas.

    Caixas postais não distinguem maiúsculas na prática, e contas antigas
    foram gravadas com o e-mail como a pessoa digitou. Toda busca por e-mail
    digitado (login, registro, recuperação, troca de e-mail) usa isto.
    """
    return {campo: {"$regex": f"^{re.escape(email.strip())}$", "$options": "i"}}


def email_provisorio(email: str | None) -> bool:
    """E-mail criado pelo login via ORCID até a pessoa informar o institucional."""
    return bool(email) and email.lower().endswith(SUFIXO_PROVISORIO)


def email_institucional_valido(email: str) -> bool:
    dominio = email.split("@")[-1].lower().strip()
    if not dominio or "@" not in email:
        return False
    if dominio.endswith(".edu.br") or dominio == "edu.br" or dominio.endswith(".edu") or dominio == "edu":
        return True
    return any(dominio == alvo or dominio.endswith("." + alvo) for alvo in DOMINIOS_PERMITIDOS)


def validar_email_institucional(email: str) -> str:
    """Devolve o e-mail se for institucional; senão levanta ValueError (mensagem para o usuário)."""
    if not email_institucional_valido(email):
        raise ValueError("Apenas e-mails institucionais acadêmicos são permitidos.")
    return email
