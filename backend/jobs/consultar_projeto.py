"""
Consulta projetos no banco de produção por trecho do título e imprime os
campos que decidem se eles aparecem na plataforma (ativo, situação, origem,
módulo, coordenação). Só leitura.

Uso (a partir de backend/) ou pelo workflow "Manutenção do banco"
(tarefa `consultar`, input `termo`):
    python -m jobs.consultar_projeto "tuberculose"
"""

import asyncio
import os
import re
import sys

from dotenv import load_dotenv

CAMPOS = ("titulo", "origem", "instituicao", "modulo", "situacao", "ativo", "nome_professor",
          "email_professor", "unidade", "tipo", "tipo_sigaa", "categoria", "ano", "sigaa_id",
          "unirio_id", "ufv_id", "detalhe_ok", "link_detalhe", "remoto", "data_criacao",
          "atualizado_em", "desativado_em")


async def consultar(db, termo: str, limite: int = 20, instituicao: str = "", modulo: str = "") -> list[dict]:
    filtro: dict = {"titulo": {"$regex": re.escape(termo), "$options": "i"}} if termo else {}
    if instituicao:
        filtro["instituicao"] = instituicao
    if modulo:
        filtro["modulo"] = modulo
    return await db.projetos.find(filtro).limit(limite).to_list(length=limite)


def imprimir(docs: list[dict], termo: str) -> None:
    print(f"{len(docs)} projeto(s) com '{termo}' no título:")
    for doc in docs:
        print(f"\n_id={doc.get('_id')}")
        for campo in CAMPOS:
            if campo in doc:
                print(f"  {campo}: {doc[campo]!r}")
        extras = doc.get("extras")
        if extras:
            print(f"  extras: {extras!r}")


async def main(argv: list[str]) -> int:
    termo = (argv[0] if argv else "").strip()
    # Filtros opcionais por ambiente (o workflow repassa os inputs).
    instituicao = os.getenv("CONSULTA_INSTITUICAO", "").strip()
    modulo = os.getenv("CONSULTA_MODULO", "").strip()
    if not termo and not instituicao:
        print("Informe um trecho do título ou uma instituição.", file=sys.stderr)
        return 2
    load_dotenv()
    from database.connection import Database

    await Database.connect()
    try:
        docs = await consultar(Database.get_db(), termo, instituicao=instituicao, modulo=modulo)
    finally:
        await Database.disconnect()
    imprimir(docs, termo or f"{instituicao} {modulo}".strip())
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main(sys.argv[1:])))
