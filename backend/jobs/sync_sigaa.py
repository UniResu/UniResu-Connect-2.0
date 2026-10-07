"""
Job semanal: sincroniza projetos de pesquisa e extensão de uma instituição
que usa o SIGAA (UNIR por padrão; as demais em services/sigaa/instituicoes.py).

Uso (a partir de backend/):
    python -m jobs.sync_sigaa
    SIGAA_INSTITUICAO=UFRN python -m jobs.sync_sigaa
    SIGAA_INSTITUICAO=UFRN python -m jobs.sync_sigaa --dry-run   # coleta e imprime, sem gravar

Agendado via GitHub Actions (.github/workflows/sync-sigaa.yml).

Regras de segurança:
- Um módulo (pesquisa/extensão) que retorna 0 itens, ou cuja busca falha,
  é tratado como FALHA: nada daquele módulo é desativado, um alerta é
  enviado e o processo sai com código 1 (o Actions marca a run como falha).
- Falha no detalhe de um item não aborta nada — o item é salvo com os
  dados da listagem e o erro vai para o log da run.
- Cada execução é registrada em `sigaa_sync_runs`.
"""

import asyncio
import json
import os
import logging
import sys
from datetime import datetime, timezone
from typing import Awaitable, Callable, Optional

from dotenv import load_dotenv

from services.fontes import fonte_sigaa
from services.sigaa import repositorio
from services.sigaa.config import SigaaConfig
from services.sigaa.scraper import COLETORES, SigaaClient

logger = logging.getLogger("jobs.sync_sigaa")

MAX_ERROS_REGISTRADOS = 200


async def executar_sync(
    db,
    cfg: SigaaConfig,
    coletores: Optional[dict] = None,
    client: Optional[SigaaClient] = None,
    alertar: Optional[Callable[[dict], Awaitable[None]]] = None,
    dry_run: bool = False,
) -> dict:
    coletores = coletores or COLETORES
    client = client or SigaaClient(cfg)
    fonte = fonte_sigaa(cfg.instituicao)
    inicio = datetime.now(timezone.utc)
    if not dry_run:
        await repositorio.garantir_modulo(db)
    run = {
        "fonte": "sigaa",
        "instituicao": fonte.instituicao,
        "iniciada_em": inicio,
        "status": "executando",
        "dry_run": dry_run,
        "config": {"anos": cfg.anos, "modulos": cfg.modulos, "pesquisa_situacao": cfg.pesquisa_situacao,
                   "extensao_tipos": cfg.extensao_tipos, "base_url": cfg.base_url},
    }
    run_id = None if dry_run else (await db.sigaa_sync_runs.insert_one(dict(run))).inserted_id
    amostras: dict[str, list] = {}

    modulos: dict = {}
    erros: list[dict] = []
    falhou = False

    for modulo in cfg.modulos:
        stats = {"coletados": 0, "novos": 0, "atualizados": 0, "desativados": 0,
                 "erros_detalhe": 0, "status": "sucesso"}
        registros: list[dict] = []
        anos_ok: list[str] = []
        for ano in cfg.anos:
            try:
                res = await asyncio.to_thread(coletores[modulo], client, ano)
            except Exception as e:  # falha na busca/listagem do módulo
                logger.error("%s %s %s: busca falhou: %s", fonte.rotulo, modulo, ano, e)
                erros.append({"modulo": modulo, "ano": ano, "erro": f"busca falhou: {e}"})
                continue
            registros.extend(res.itens)
            erros.extend(res.erros)
            stats["erros_detalhe"] += len(res.erros)
            if res.itens:
                anos_ok.append(ano)

        stats["coletados"] = len(registros)
        amostras[modulo] = registros[:3]
        if registros and not dry_run:
            up = await repositorio.upsert_projetos(db, registros, fonte=fonte)
            stats["novos"], stats["atualizados"] = up.novos, up.atualizados
            if anos_ok:
                stats["desativados"] = await repositorio.desativar_ausentes(db, modulo, anos_ok, up.chaves,
                                                                            fonte=fonte)
        if set(anos_ok) != set(cfg.anos):
            # 0 resultados (ou busca falhou) em algum ano: não desativamos
            # nada desse ano e tratamos como falha para alertar.
            stats["status"] = "falha"
            falhou = True
            erros.append({"modulo": modulo, "erro": "coleta retornou 0 resultados",
                          "anos_sem_resultado": sorted(set(cfg.anos) - set(anos_ok))})
        modulos[modulo] = stats

    if falhou:
        status = "falha"
    elif erros:
        status = "sucesso_com_erros"
    else:
        status = "sucesso"

    fim = datetime.now(timezone.utc)
    atualizacao = {
        "status": status,
        "finalizada_em": fim,
        "duracao_segundos": round((fim - inicio).total_seconds(), 1),
        "requisicoes": client.total_requisicoes,
        "modulos": modulos,
        "total_erros": len(erros),
        "erros": erros[:MAX_ERROS_REGISTRADOS],
    }
    if run_id is not None:
        await db.sigaa_sync_runs.update_one({"_id": run_id}, {"$set": atualizacao})
    run.update(atualizacao, _id=run_id)

    logger.info("Sync %s finalizado: status=%s duração=%ss requisições=%d",
                fonte.rotulo, status, atualizacao["duracao_segundos"], client.total_requisicoes)
    for modulo, s in modulos.items():
        logger.info("  %-9s coletados=%d novos=%d atualizados=%d desativados=%d erros_detalhe=%d [%s]",
                    modulo, s["coletados"], s["novos"], s["atualizados"], s["desativados"],
                    s["erros_detalhe"], s["status"])

    if dry_run:
        for modulo, amostra in amostras.items():
            print(f"\n=== Amostra ({fonte.instituicao}, {modulo}) ===")
            print(json.dumps(amostra, ensure_ascii=False, indent=2, default=str))
        if erros:
            print("\n=== Erros (primeiros 10) ===")
            print(json.dumps(erros[:10], ensure_ascii=False, indent=2, default=str))
    elif status == "falha" and alertar:
        await alertar(run)
    return run


async def alertar_por_email(run: dict) -> None:
    """Avisa a equipe (EMAIL_SUPORTE ou SIGAA_ALERTA_EMAIL) sobre a falha."""
    from services.email import EMAIL_SUPORTE, enviar_email

    destino = os.getenv("SIGAA_ALERTA_EMAIL") or EMAIL_SUPORTE
    sigla = run.get("instituicao") or "UNIR"
    linhas = [f"- {m}: {s['status']} (coletados={s['coletados']})" for m, s in run["modulos"].items()]
    detalhes = "\n".join(f"- {e}" for e in run["erros"][:20])
    await enviar_email({
        "to": [destino],
        "subject": f"[UniResu] Falha no sync semanal do SIGAA/{sigla}",
        "text": (
            f"O sync semanal de projetos do SIGAA/{sigla} falhou. Nenhum projeto foi desativado "
            "nos módulos com falha.\n\n"
            f"Run: {run['_id']}\nIniciada em: {run['iniciada_em']:%d/%m/%Y %H:%M} UTC\n\n"
            "Módulos:\n" + "\n".join(linhas) + "\n\nErros (primeiros 20):\n" + detalhes
        ),
    })


async def main(argv: Optional[list[str]] = None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    load_dotenv()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    if "--dry-run" in argv:
        run = await executar_sync(None, SigaaConfig.from_env(), dry_run=True)
        return 1 if run["status"] == "falha" else 0

    from database.connection import Database

    await Database.connect()
    try:
        run = await executar_sync(Database.get_db(), SigaaConfig.from_env(), alertar=alertar_por_email)
    finally:
        await Database.disconnect()
    return 1 if run["status"] == "falha" else 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
