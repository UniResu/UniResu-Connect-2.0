"""
Remove os projetos de TESTE cadastrados manualmente antes da chegada dos
projetos do SIGAA/UNIR (e da UNIRIO).

Critério: documentos da collection `projetos` SEM `origem` (ou seja, não
vieram de nenhuma coleta) e criados antes da primeira coleta do SIGAA
(`primeira_coleta` mais antiga entre os docs `origem: "sigaa"`). Projetos
cadastrados por professores DEPOIS disso são preservados.

Por padrão só lista (dry-run). Para apagar de fato: --confirmar.
As candidaturas que apontam para os projetos removidos também são apagadas
(--manter-candidaturas preserva). `--todos` ignora a data de corte e inclui
todo projeto sem origem de coleta (útil enquanto a plataforma só tem os
cadastros de teste).

Uso (a partir de backend/, usa o MONGO_URI do .env — precisa de um usuário
com permissão de `remove`; o usuário restrito do job não tem). Também roda
pelo GitHub Actions (workflow "Manutenção do banco"):
    python -m jobs.remover_projetos_teste
    python -m jobs.remover_projetos_teste --confirmar
    python -m jobs.remover_projetos_teste --antes-de 2026-09-29 --confirmar
    python -m jobs.remover_projetos_teste --todos --confirmar
"""

import argparse
import asyncio
import sys
from datetime import datetime, timezone
from typing import Optional

from bson import ObjectId
from dotenv import load_dotenv


async def data_corte(db, antes_de: Optional[str]) -> Optional[datetime]:
    """Data limite: a informada, ou a primeira coleta do SIGAA registrada."""
    if antes_de:
        return datetime.fromisoformat(antes_de).replace(tzinfo=timezone.utc)
    doc = await db.projetos.find_one({"origem": "sigaa", "primeira_coleta": {"$ne": None}},
                                     sort=[("primeira_coleta", 1)], projection={"primeira_coleta": 1})
    if not doc:
        return None
    corte = doc["primeira_coleta"]
    return corte if corte.tzinfo else corte.replace(tzinfo=timezone.utc)


def _criado_em(doc: dict) -> Optional[datetime]:
    """Data de criação: `data_publicacao` (ISO) ou o timestamp do ObjectId."""
    valor = doc.get("data_publicacao")
    if isinstance(valor, str):
        try:
            dt = datetime.fromisoformat(valor)
            return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
        except ValueError:
            pass
    if isinstance(valor, datetime):
        return valor if valor.tzinfo else valor.replace(tzinfo=timezone.utc)
    oid = doc.get("_id")
    return oid.generation_time if isinstance(oid, ObjectId) else None


async def listar_projetos_teste(db, corte: Optional[datetime]) -> list[dict]:
    """Projetos manuais (sem `origem`) criados antes da data de corte.
    Sem data de corte (nenhuma coleta registrada), devolve todos os manuais."""
    manuais = await db.projetos.find({"origem": {"$exists": False}}).to_list(None)
    if corte is None:
        return manuais
    return [d for d in manuais if (_criado_em(d) or corte) < corte]


async def remover_projetos_teste(db, corte: Optional[datetime], confirmar: bool,
                                 manter_candidaturas: bool = False) -> dict:
    alvos = await listar_projetos_teste(db, corte)
    ids = [d["_id"] for d in alvos]
    resumo = {"corte": corte.isoformat() if corte else None, "projetos": len(ids), "candidaturas": 0,
              "removido": False, "titulos": [d.get("titulo") for d in alvos]}
    if ids:
        resumo["candidaturas"] = await db.candidaturas.count_documents(
            {"projeto_id": {"$in": [str(i) for i in ids] + ids}})
    if confirmar and ids:
        if not manter_candidaturas and resumo["candidaturas"]:
            await db.candidaturas.delete_many({"projeto_id": {"$in": [str(i) for i in ids] + ids}})
        await db.projetos.delete_many({"_id": {"$in": ids}})
        resumo["removido"] = True
    return resumo


async def main() -> int:
    load_dotenv()
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--confirmar", action="store_true", help="apaga de fato (sem isso, só lista)")
    ap.add_argument("--antes-de", help="data de corte AAAA-MM-DD (padrão: primeira coleta do SIGAA)")
    ap.add_argument("--todos", action="store_true",
                    help="sem data de corte: todo projeto sem origem de coleta (SIGAA/UNIRIO) é alvo")
    ap.add_argument("--manter-candidaturas", action="store_true", help="não apaga as candidaturas desses projetos")
    args = ap.parse_args()

    from database.connection import Database

    await Database.connect()
    try:
        db = Database.get_db()
        corte = None if args.todos else await data_corte(db, args.antes_de)
        resumo = await remover_projetos_teste(db, corte, args.confirmar, args.manter_candidaturas)
    finally:
        await Database.disconnect()

    if args.todos:
        print("Data de corte: (nenhuma, --todos: todos os projetos sem origem de coleta)")
    else:
        print(f"Data de corte: {resumo['corte'] or '(nenhuma coleta registrada: todos os manuais)'}")
    print(f"Projetos de teste encontrados: {resumo['projetos']} (candidaturas ligadas: {resumo['candidaturas']})")
    for t in resumo["titulos"]:
        print(f"  - {t}")
    if resumo["removido"]:
        print("Removidos.")
    elif resumo["projetos"]:
        print("Nada foi apagado (dry-run). Rode de novo com --confirmar para remover.")
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
