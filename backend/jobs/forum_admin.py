"""
Moderação do fórum pela equipe, sem acesso direto ao Atlas.

    python -m jobs.forum_admin listar
    python -m jobs.forum_admin remover <id do tópico> [--confirmar]

`listar` mostra cada tópico com data, autor (@username e nome) e número de
respostas. `remover` apaga o tópico e as respostas dele, como faz a rota de
exclusão do autor; sem `--confirmar` só mostra o que seria apagado. Os
tópicos do seed (`seed: "forum_v1"`) voltam no próximo startup da API se
continuarem em jobs/seed_forum.py.
"""

import asyncio
import sys
from typing import Any, Dict, List

from bson import ObjectId
from dotenv import load_dotenv


async def listar(db) -> List[Dict[str, Any]]:
    topicos = await db.topicos_forum.find({}).sort("data_criacao", 1).to_list(length=None)
    ids_autores = {t.get("autor_id") for t in topicos if t.get("autor_id")}
    oids = [ObjectId(i) for i in ids_autores if ObjectId.is_valid(i)]
    autores = {
        str(u["_id"]): u
        for u in await db.usuarios.find({"_id": {"$in": oids}}, {"username": 1, "nome": 1}).to_list(length=None)
    }
    linhas = []
    for t in topicos:
        autor = autores.get(t.get("autor_id") or "", {})
        linhas.append({
            "id": str(t["_id"]),
            "data": t.get("data_criacao"),
            "username": autor.get("username"),
            "nome": autor.get("nome"),
            "titulo": t.get("titulo"),
            "respostas": await db.respostas_forum.count_documents({"topico_id": str(t["_id"])}),
            "seed": t.get("seed_chave"),
        })
    return linhas


async def remover(db, topico_id: str, confirmar: bool) -> Dict[str, Any]:
    if not ObjectId.is_valid(topico_id):
        raise ValueError(f"id inválido: {topico_id!r}")
    oid = ObjectId(topico_id)
    topico = await db.topicos_forum.find_one({"_id": oid})
    if not topico:
        raise LookupError(f"tópico {topico_id} não encontrado")
    respostas = await db.respostas_forum.count_documents({"topico_id": str(oid)})
    resultado = {"titulo": topico.get("titulo"), "autor_id": topico.get("autor_id"), "respostas": respostas,
                 "removido": False}
    if confirmar:
        await db.topicos_forum.delete_one({"_id": oid})
        await db.respostas_forum.delete_many({"topico_id": str(oid)})
        resultado["removido"] = True
    return resultado


async def main(argv: List[str]) -> int:
    if not argv or argv[0] not in ("listar", "remover"):
        print(__doc__, file=sys.stderr)
        return 2
    load_dotenv()
    from database.connection import Database

    await Database.connect()
    try:
        db = Database.get_db()
        if argv[0] == "listar":
            linhas = await listar(db)
            print(f"{len(linhas)} tópico(s), do mais antigo ao mais novo:")
            for linha in linhas:
                data = f"{linha['data']:%d/%m/%Y %H:%M}" if linha["data"] else "sem data"
                autor = f"@{linha['username'] or '?'} ({linha['nome'] or 'sem nome'})"
                print(f"  {linha['id']}  {data}  {autor:45s}  {linha['respostas']:3d} resp.  "
                      f"{'[seed] ' if linha['seed'] else ''}{linha['titulo']}")
            return 0
        if len(argv) < 2:
            print("Informe o id do tópico.", file=sys.stderr)
            return 2
        r = await remover(db, argv[1].strip(), "--confirmar" in argv[2:])
    finally:
        await Database.disconnect()
    acao = "Removido" if r["removido"] else "Seria removido (rode com --confirmar)"
    print(f"{acao}: '{r['titulo']}' (autor_id={r['autor_id']}) e {r['respostas']} resposta(s).")
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main(sys.argv[1:])))
