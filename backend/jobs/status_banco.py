"""
Resumo do banco de produção para quem não tem o Atlas à mão: quantos
projetos existem por fonte, módulo e situação, e as últimas execuções dos
syncs. Só leitura (funciona com o usuário restrito dos jobs).

Uso (a partir de backend/, usa o MONGO_URI do .env) ou pelo workflow
"Manutenção do banco" (tarefa `status`):
    python -m jobs.status_banco
"""

import asyncio
import sys

from dotenv import load_dotenv


async def resumo(db) -> dict:
    por_fonte = await db.projetos.aggregate([
        {"$group": {
            "_id": {"origem": {"$ifNull": ["$origem", "manual"]}, "instituicao": {"$ifNull": ["$instituicao", "-"]},
                    "modulo": "$modulo"},
            "total": {"$sum": 1},
            "ativos": {"$sum": {"$cond": [{"$ne": ["$ativo", False]}, 1, 0]}},
            "em_execucao": {"$sum": {"$cond": [
                {"$and": [{"$ne": ["$ativo", False]}, {"$eq": ["$situacao", "EM EXECUÇÃO"]}]}, 1, 0]}},
            "com_detalhe": {"$sum": {"$cond": [{"$eq": ["$detalhe_ok", True]}, 1, 0]}},
            "sem_link": {"$sum": {"$cond": [{"$in": [{"$ifNull": ["$link_detalhe", ""]}, ["", None]]}, 1, 0]}},
            "sem_email": {"$sum": {"$cond": [{"$and": [
                {"$in": [{"$ifNull": ["$email_professor", ""]}, ["", None]]},
                {"$in": [{"$ifNull": ["$email_contato_manual", ""]}, ["", None]]}]}, 1, 0]}},
            "bytes": {"$sum": {"$bsonSize": "$$ROOT"}},
        }},
        {"$sort": {"_id.origem": 1, "_id.instituicao": 1, "_id.modulo": 1}},
    ]).to_list(length=None)
    runs = await db.sigaa_sync_runs.find(
        {}, {"fonte": 1, "instituicao": 1, "status": 1, "iniciada_em": 1, "finalizada_em": 1,
             "duracao_segundos": 1, "modulos": 1, "dry_run": 1, "total_erros": 1},
    ).sort("iniciada_em", -1).to_list(length=8)
    return {"projetos": por_fonte, "runs": runs, "tamanho": await tamanho(db)}


async def tamanho(db) -> dict:
    """Ocupação da coleção de projetos e, quando o usuário pode ler, do banco
    inteiro. O Atlas gratuito (M0) limita dados + índices a 512 MB, por isso
    vale acompanhar antes de coletar instituições novas."""
    try:
        stats = await db.command("collStats", "projetos")
    except Exception as e:  # usuário sem collStats ou servidor sem o comando
        return {"erro": str(e)}
    dados = {
        "documentos": stats.get("count", 0),
        "dados_mb": stats.get("size", 0) / 1e6,
        "indices_mb": stats.get("totalIndexSize", 0) / 1e6,
        "disco_mb": stats.get("storageSize", 0) / 1e6,
        "media_kb": (stats.get("avgObjSize") or 0) / 1e3,
    }
    try:
        geral = await db.command("dbStats")
        dados["banco_mb"] = (geral.get("dataSize", 0) + geral.get("indexSize", 0)) / 1e6
    except Exception:
        pass
    return dados


def imprimir(dados: dict) -> None:
    print("Projetos por fonte, instituição e módulo "
          "(total / ativos / em execução / com detalhe / sem link / sem e-mail / MB):")
    for linha in dados["projetos"]:
        chave = linha["_id"]
        print(f"  {chave.get('origem') or 'manual':8s} {chave.get('instituicao') or '-':10s} {chave.get('modulo') or '-':10s} "
              f"{linha['total']:5d} / {linha['ativos']:5d} / {linha['em_execucao']:5d} / {linha['com_detalhe']:5d}"
              f" / {linha.get('sem_link', 0):5d} / {linha.get('sem_email', 0):5d}"
              f" / {linha.get('bytes', 0) / 1e6:6.1f}")
    t = dados.get("tamanho") or {}
    if "erro" in t:
        print(f"\nOcupação: não foi possível ler (collStats): {t['erro']}")
    elif t:
        print(f"\nOcupação da coleção projetos: {t['documentos']} documentos, {t['dados_mb']:.1f} MB de dados, "
              f"{t['indices_mb']:.1f} MB de índices, {t['disco_mb']:.1f} MB em disco, {t['media_kb']:.1f} KB por documento"
              + (f"; banco inteiro (dados + índices): {t['banco_mb']:.1f} MB de 512 MB no M0" if "banco_mb" in t else ""))
    print("\nÚltimas execuções dos syncs:")
    for r in dados["runs"]:
        inicio = r.get("iniciada_em")
        fim = r.get("finalizada_em")
        mods = ", ".join(f"{m}: {s.get('coletados', 0)} coletados, {s.get('novos', 0)} novos, "
                         f"{s.get('atualizados', 0)} atualizados [{s.get('status')}]"
                         for m, s in (r.get("modulos") or {}).items())
        rotulo = r.get("fonte", "sigaa") + (f"/{r['instituicao']}" if r.get("instituicao") else "")
        print(f"  {rotulo:12s} {r.get('status', '?'):18s} "
              f"início {inicio:%d/%m %H:%M} UTC" + (f", fim {fim:%H:%M}" if fim else ", em andamento")
              + (f", {r['duracao_segundos']:.0f}s" if r.get("duracao_segundos") else "")
              + (" [dry-run]" if r.get("dry_run") else "")
              + (f", erros={r['total_erros']}" if r.get("total_erros") else "")
              + (f"\n          {mods}" if mods else ""))


async def main() -> int:
    load_dotenv()
    from database.connection import Database

    await Database.connect()
    try:
        dados = await resumo(Database.get_db())
    finally:
        await Database.disconnect()
    imprimir(dados)
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
