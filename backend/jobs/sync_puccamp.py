"""
Sync dos projetos de extensão da PUC-Campinas (página pública "Projetos de
Extensão" do portal da universidade).

Grava com `origem: "puccamp"` e desativa os projetos que sumiram da página.
Uma coleta vazia é tratada como falha: nada é desativado.

Uso (a partir de backend/, usa o MONGO_URI do .env):
    python -m jobs.sync_puccamp
    python -m jobs.sync_puccamp --dry-run     # coleta e imprime, sem gravar
"""

import asyncio
import json
import logging
import sys
from datetime import datetime, timezone
from typing import Optional

from dotenv import load_dotenv

from services.fontes import PUCCAMP
from services.puccamp.coleta import PucCampClient, PucCampConfig, listar_extensao, registro_extensao
from services.sigaa import repositorio

logger = logging.getLogger("jobs.sync_puccamp")


async def executar_sync(db, cfg: PucCampConfig, client: Optional[PucCampClient] = None,
                        dry_run: bool = False) -> dict:
    client = client or PucCampClient(cfg)
    inicio = datetime.now(timezone.utc)
    run = {"fonte": PUCCAMP.origem, "instituicao": PUCCAMP.instituicao, "iniciada_em": inicio,
           "status": "executando", "dry_run": dry_run, "config": {"url": cfg.url_extensao}}
    run_id = None if dry_run else (await db.sigaa_sync_runs.insert_one(dict(run))).inserted_id

    stats = {"coletados": 0, "novos": 0, "atualizados": 0, "desativados": 0, "status": "sucesso"}
    erros: list[dict] = []
    registros: list[dict] = []
    try:
        projetos = await asyncio.to_thread(listar_extensao, client)
        registros = [registro_extensao(p) for p in projetos]
    except Exception as e:  # falha na coleta
        logger.error("PUC-Campinas: coleta falhou: %s", e)
        erros.append({"modulo": "extensao", "erro": f"consulta falhou: {e}"})
    stats["coletados"] = len(registros)

    if not registros:
        stats["status"] = "falha"
        if not erros:
            erros.append({"modulo": "extensao", "erro": "página sem projetos no ciclo vigente"})
    elif not dry_run:
        up = await repositorio.upsert_projetos(db, registros, fonte=PUCCAMP)
        stats["novos"], stats["atualizados"] = up.novos, up.atualizados
        stats["desativados"] = await repositorio.desativar_ausentes(db, "extensao", [], up.chaves, fonte=PUCCAMP)

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

    logger.info("Sync PUC-Campinas finalizado: status=%s coletados=%d novos=%d atualizados=%d desativados=%d%s",
                stats["status"], stats["coletados"], stats["novos"], stats["atualizados"], stats["desativados"],
                " [DRY-RUN: nada gravado]" if dry_run else "")
    if dry_run:
        print("\n=== Projetos coletados ===")
        print(json.dumps(registros, ensure_ascii=False, indent=2, default=str))
    return run


async def main(argv: Optional[list[str]] = None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    load_dotenv()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    cfg = PucCampConfig()
    if "--dry-run" in argv:
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
