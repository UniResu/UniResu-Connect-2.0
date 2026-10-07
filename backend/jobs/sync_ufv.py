"""
Sync dos projetos da UFV (dados abertos): extensão pela API DataStore do
CKAN e pesquisa pelo CSV completo do recurso.

Grava com `origem: "ufv"` e desativa, módulo a módulo, os projetos da UFV
que deixaram de estar em execução (sumiram da coleta). Uma coleta vazia ou
com erro em um módulo é tratada como falha daquele módulo: nada dele é
desativado e o outro módulo segue normalmente.

Uso (a partir de backend/, usa o MONGO_URI do .env):
    python -m jobs.sync_ufv
    python -m jobs.sync_ufv --dry-run     # coleta e imprime, sem gravar
    UFV_MODULOS=pesquisa python -m jobs.sync_ufv --dry-run
"""

import asyncio
import json
import logging
import sys
from datetime import datetime, timezone
from typing import Callable, Optional

from dotenv import load_dotenv

from services.fontes import UFV
from services.sigaa import repositorio
from services.ufv.coleta import (UfvClient, UfvConfig, listar_extensao, listar_pesquisa, registro_extensao,
                                 registro_pesquisa)

logger = logging.getLogger("jobs.sync_ufv")

# Por módulo: (função que coleta as linhas brutas, função que converte em registro).
COLETORES: dict[str, tuple[Callable, Callable]] = {
    "extensao": (listar_extensao, registro_extensao),
    "pesquisa": (listar_pesquisa, registro_pesquisa),
}


def _stats_vazios() -> dict:
    return {"coletados": 0, "novos": 0, "atualizados": 0, "desativados": 0, "sem_coordenador": 0,
            "status": "sucesso"}


async def executar_sync(db, cfg: UfvConfig, client: Optional[UfvClient] = None, dry_run: bool = False,
                        coletores: Optional[dict] = None) -> dict:
    client = client or UfvClient(cfg)
    coletores = coletores or COLETORES
    modulos = [m for m in cfg.modulos if m in coletores]
    inicio = datetime.now(timezone.utc)
    run = {"fonte": UFV.origem, "iniciada_em": inicio, "status": "executando", "dry_run": dry_run,
           "config": {"modulos": modulos, "recurso": cfg.recurso_extensao,
                      "pesquisa_situacoes": list(cfg.pesquisa_situacoes),
                      "pesquisa_ano_minimo": cfg.pesquisa_ano_minimo}}
    run_id = None if dry_run else (await db.sigaa_sync_runs.insert_one(dict(run))).inserted_id

    por_modulo: dict[str, dict] = {}
    amostras: dict[str, list] = {}
    estatisticas: dict[str, dict] = {}
    erros: list[dict] = []
    for modulo in modulos:
        listar, converter = coletores[modulo]
        stats = _stats_vazios()
        registros: list[dict] = []
        try:
            if modulo == "pesquisa":
                estatisticas[modulo] = {}
                linhas = await asyncio.to_thread(listar, client, None, estatisticas[modulo])
            else:
                linhas = await asyncio.to_thread(listar, client)
            registros = [r for r in (converter(linha) for linha in linhas) if r["titulo"]]
        except Exception as e:  # falha na coleta deste módulo
            logger.error("UFV %s: coleta falhou: %s", modulo, e)
            erros.append({"modulo": modulo, "erro": f"consulta falhou: {e}"})
        stats["coletados"] = len(registros)
        stats["sem_coordenador"] = sum(1 for r in registros if not r["coordenador"])

        if not registros:
            stats["status"] = "falha"
            if not any(e["modulo"] == modulo for e in erros):
                erros.append({"modulo": modulo, "erro": "consulta retornou 0 projetos em execução"})
        elif not dry_run:
            up = await repositorio.upsert_projetos(db, registros, fonte=UFV)
            stats["novos"], stats["atualizados"] = up.novos, up.atualizados
            stats["desativados"] = await repositorio.desativar_ausentes(db, modulo, [], up.chaves, fonte=UFV)
        por_modulo[modulo] = stats
        amostras[modulo] = registros[:3]

    status = "sucesso" if all(s["status"] == "sucesso" for s in por_modulo.values()) else "falha"
    fim = datetime.now(timezone.utc)
    atualizacao = {
        "status": status,
        "finalizada_em": fim,
        "duracao_segundos": round((fim - inicio).total_seconds(), 1),
        "requisicoes": client.total_requisicoes,
        "modulos": por_modulo,
        "total_erros": len(erros),
        "erros": erros,
    }
    if run_id is not None:
        await db.sigaa_sync_runs.update_one({"_id": run_id}, {"$set": atualizacao})
    run.update(atualizacao, _id=run_id)

    logger.info("Sync UFV finalizado: status=%s duração=%ss requisições=%d%s", status,
                atualizacao["duracao_segundos"], client.total_requisicoes, " [DRY-RUN: nada gravado]" if dry_run else "")
    for modulo, stats in por_modulo.items():
        logger.info("  %-9s coletados=%d novos=%d atualizados=%d desativados=%d sem_coordenador=%d [%s]", modulo,
                    stats["coletados"], stats["novos"], stats["atualizados"], stats["desativados"],
                    stats["sem_coordenador"], stats["status"])
    if dry_run:
        for modulo, amostra in amostras.items():
            print(f"\n=== Amostra ({modulo}) ===")
            print(json.dumps(amostra, ensure_ascii=False, indent=2, default=str))
        if estatisticas.get("pesquisa", {}).get("por_situacao_ano"):
            print("\n=== Pesquisa: linhas do CSV por situação e ano (anos recentes) ===")
            contagem = estatisticas["pesquisa"]["por_situacao_ano"]
            for (situacao, ano), n in sorted(contagem.items(), key=lambda kv: (kv[0][0], kv[0][1])):
                print(f"  {situacao:36s} {ano}  {n:7d}")
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
