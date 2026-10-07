"""
Sync dos projetos e programas de extensão da UFV (dados abertos).

Consulta a API do portal dados.ufv.br, grava com `origem: "ufv"` e desativa
os projetos da UFV que deixaram de estar em execução (sumiram da consulta).
Uma consulta vazia ou com erro é tratada como falha: nada é desativado.

Uso (a partir de backend/, usa o MONGO_URI do .env):
    python -m jobs.sync_ufv
    python -m jobs.sync_ufv --dry-run     # consulta e imprime, sem gravar
"""

import asyncio
import json
import logging
import sys
from datetime import datetime, timezone
from typing import Optional

from dotenv import load_dotenv

from services.fontes import UFV
from services.sigaa import repositorio
from services.ufv.coleta import UfvClient, UfvConfig, listar_extensao, registro_extensao

logger = logging.getLogger("jobs.sync_ufv")


async def executar_sync(db, cfg: UfvConfig, client: Optional[UfvClient] = None, dry_run: bool = False,
                        listar=listar_extensao) -> dict:
    client = client or UfvClient(cfg)
    inicio = datetime.now(timezone.utc)
    run = {"fonte": UFV.origem, "iniciada_em": inicio, "status": "executando", "dry_run": dry_run,
           "config": {"modulos": ["extensao"], "recurso": cfg.recurso_extensao}}
    run_id = None if dry_run else (await db.sigaa_sync_runs.insert_one(dict(run))).inserted_id

    stats = {"coletados": 0, "novos": 0, "atualizados": 0, "desativados": 0, "sem_coordenador": 0,
             "status": "sucesso"}
    erros: list[dict] = []
    registros: list[dict] = []
    try:
        linhas = await asyncio.to_thread(listar, client)
        registros = [r for r in (registro_extensao(linha) for linha in linhas) if r["titulo"]]
    except Exception as e:  # falha na consulta
        logger.error("UFV extensão: consulta falhou: %s", e)
        erros.append({"modulo": "extensao", "erro": f"consulta falhou: {e}"})
    stats["coletados"] = len(registros)
    stats["sem_coordenador"] = sum(1 for r in registros if not r["coordenador"])

    if not registros:
        stats["status"] = "falha"
        if not erros:
            erros.append({"modulo": "extensao", "erro": "consulta retornou 0 projetos em execução"})
    elif not dry_run:
        up = await repositorio.upsert_projetos(db, registros, fonte=UFV)
        stats["novos"], stats["atualizados"] = up.novos, up.atualizados
        stats["desativados"] = await repositorio.desativar_ausentes(db, "extensao", [], up.chaves, fonte=UFV)

    fim = datetime.now(timezone.utc)
    atualizacao = {
        "status": stats["status"],
        "finalizada_em": fim,
        "duracao_segundos": round((fim - inicio).total_seconds(), 1),
        "requisicoes": client.total_requisicoes,
        "modulos": {"extensao": stats},
        "total_erros": len(erros),
        "erros": erros,
    }
    if run_id is not None:
        await db.sigaa_sync_runs.update_one({"_id": run_id}, {"$set": atualizacao})
    run.update(atualizacao, _id=run_id)

    logger.info("Sync UFV finalizado: status=%s duração=%ss requisições=%d%s", stats["status"],
                atualizacao["duracao_segundos"], client.total_requisicoes, " [DRY-RUN: nada gravado]" if dry_run else "")
    logger.info("  extensao  coletados=%d novos=%d atualizados=%d desativados=%d sem_coordenador=%d [%s]",
                stats["coletados"], stats["novos"], stats["atualizados"], stats["desativados"],
                stats["sem_coordenador"], stats["status"])
    if dry_run:
        print("\n=== Amostra (extensao) ===")
        print(json.dumps(registros[:3], ensure_ascii=False, indent=2, default=str))
    return run


async def main(argv: Optional[list[str]] = None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    load_dotenv()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    dry_run = "--dry-run" in argv
    cfg = UfvConfig.from_env()
    if dry_run:
        run = await executar_sync(None, cfg, dry_run=True)
        return 1 if run["status"] == "falha" else 0

    from database.connection import Database

    await Database.connect()
    try:
        run = await executar_sync(Database.get_db(), cfg)
    finally:
        await Database.disconnect()
    return 1 if run["status"] == "falha" else 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
