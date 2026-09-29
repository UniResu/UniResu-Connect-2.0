"""
Cadastro manual do e-mail de contato de um projeto (fallback do admin).

Usado quando o SIGAA não traz o e-mail do coordenador — ou traz um e-mail
que não deve receber candidaturas. O valor fica em `email_contato_manual`,
tem prioridade sobre o e-mail coletado e nunca é sobrescrito pelo sync.

Uso (a partir de backend/):
    python -m jobs.definir_contato --codigo PVC2148-2026 --email prof@unir.br
    python -m jobs.definir_contato --sigaa-id 4527 --email prof@unir.br
    python -m jobs.definir_contato --projeto-id 66f... --remover
"""

import argparse
import asyncio
import sys

from dotenv import load_dotenv
from bson import ObjectId
from pydantic import EmailStr, TypeAdapter, ValidationError


def montar_filtro(args) -> dict:
    if args.projeto_id:
        return {"_id": ObjectId(args.projeto_id)}
    if args.codigo:
        return {"origem": "sigaa", "codigo": args.codigo}
    return {"origem": "sigaa", "sigaa_id": args.sigaa_id}


async def definir_contato(db, filtro: dict, email) -> int:
    """Grava (ou remove, com email=None) o contato manual. Retorna nº de docs."""
    projetos = await db.projetos.find(filtro, {"titulo": 1}).to_list(10)
    if len(projetos) != 1:
        return len(projetos)
    operacao = {"$set": {"email_contato_manual": email}} if email else {"$unset": {"email_contato_manual": ""}}
    await db.projetos.update_one({"_id": projetos[0]["_id"]}, operacao)
    return 1


async def main() -> int:
    load_dotenv()
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    alvo = ap.add_mutually_exclusive_group(required=True)
    alvo.add_argument("--projeto-id", help="_id do projeto no MongoDB")
    alvo.add_argument("--codigo", help="código do projeto de pesquisa no SIGAA (ex.: PVC2148-2026)")
    alvo.add_argument("--sigaa-id", help="id da ação de extensão/projeto no SIGAA")
    acao = ap.add_mutually_exclusive_group(required=True)
    acao.add_argument("--email", help="e-mail que passa a receber as candidaturas")
    acao.add_argument("--remover", action="store_true", help="remove o contato manual")
    args = ap.parse_args()

    email = None
    if args.email:
        try:
            email = TypeAdapter(EmailStr).validate_python(args.email)
        except ValidationError:
            print(f"E-mail inválido: {args.email}", file=sys.stderr)
            return 2

    from database.connection import Database

    await Database.connect()
    try:
        n = await definir_contato(Database.get_db(), montar_filtro(args), email)
    finally:
        await Database.disconnect()

    if n != 1:
        print(f"Esperava 1 projeto, encontrei {n}. Nada foi alterado.", file=sys.stderr)
        return 1
    print("Contato removido." if args.remover else f"Contato definido: {email}")
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
