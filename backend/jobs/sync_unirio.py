"""
Job semanal: sincroniza projetos de pesquisa e extensão dos portais da UNIRIO.

Uso (a partir de backend/):
    python -m jobs.sync_unirio              # sync normal (grava no MongoDB)
    python -m jobs.sync_unirio --dry-run    # coleta e mostra o resultado, sem gravar
    python -m jobs.sync_unirio --captura    # imprime o HTML das páginas (diagnóstico)

Agendado via GitHub Actions (.github/workflows/sync-unirio.yml).

Mesmas regras de segurança do sync do SIGAA:
- Um módulo que retorna 0 itens, ou cuja busca falha, é tratado como FALHA:
  nada daquele módulo é desativado, um alerta é enviado e o processo sai com
  código 1.
- Falha no detalhe de um item não aborta nada — o item é salvo com os dados
  da listagem e o erro vai para o log da run.
- Cada execução é registrada em `sigaa_sync_runs` com `fonte: "unirio"`
  (mesma collection do SIGAA, para reaproveitar o usuário restrito do Atlas).
"""

import asyncio
import json
import logging
import os
import sys
from datetime import datetime, timezone
from typing import Awaitable, Callable, Optional

from dotenv import load_dotenv

from services.fontes import UNIRIO
from services.sigaa import repositorio
from services.unirio import parser
from services.unirio.config import UnirioConfig
from services.unirio.scraper import BASES, COLETORES, UnirioClient, url_inicial

logger = logging.getLogger("jobs.sync_unirio")

MAX_ERROS_REGISTRADOS = 200


async def executar_sync(
    db,
    cfg: UnirioConfig,
    coletores: Optional[dict] = None,
    client: Optional[UnirioClient] = None,
    alertar: Optional[Callable[[dict], Awaitable[None]]] = None,
    dry_run: bool = False,
) -> dict:
    coletores = coletores or COLETORES
    client = client or UnirioClient(cfg)
    inicio = datetime.now(timezone.utc)
    run = {
        "fonte": UNIRIO.origem,
        "iniciada_em": inicio,
        "status": "executando",
        "dry_run": dry_run,
        "config": {"modulos": cfg.modulos, "extensao_status": cfg.extensao_status},
    }
    run_id = None
    if not dry_run:
        await repositorio.garantir_modulo(db)
        run_id = (await db.sigaa_sync_runs.insert_one(dict(run))).inserted_id

    modulos: dict = {}
    erros: list[dict] = []
    amostras: dict = {}
    falhou = False

    for modulo in cfg.modulos:
        stats = {"coletados": 0, "novos": 0, "atualizados": 0, "desativados": 0,
                 "erros_detalhe": 0, "paginas": 0, "status": "sucesso"}
        try:
            res = await asyncio.to_thread(coletores[modulo], client)
        except Exception as e:  # falha na busca/listagem do módulo
            logger.error("UNIRIO %s: busca falhou: %s", modulo, e)
            erros.append({"modulo": modulo, "erro": f"busca falhou: {e}"})
            stats["status"] = "falha"
            falhou = True
            modulos[modulo] = stats
            continue

        erros.extend(res.erros)
        stats["erros_detalhe"] = len(res.erros)
        stats["coletados"] = len(res.itens)
        stats["paginas"] = res.paginas
        amostras[modulo] = res.itens[:3]

        if not res.itens:
            stats["status"] = "falha"
            falhou = True
            erros.append({"modulo": modulo, "erro": "coleta retornou 0 resultados"})
        elif not dry_run:
            up = await repositorio.upsert_projetos(db, res.itens, fonte=UNIRIO)
            stats["novos"], stats["atualizados"] = up.novos, up.atualizados
            stats["desativados"] = await repositorio.desativar_ausentes(db, modulo, [], up.chaves, fonte=UNIRIO)
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

    logger.info("Sync UNIRIO finalizado: status=%s duração=%ss requisições=%d%s",
                status, atualizacao["duracao_segundos"], client.total_requisicoes,
                " [DRY-RUN: nada gravado]" if dry_run else "")
    for modulo, s in modulos.items():
        logger.info("  %-9s coletados=%d páginas=%d novos=%d atualizados=%d desativados=%d erros_detalhe=%d [%s]",
                    modulo, s["coletados"], s["paginas"], s["novos"], s["atualizados"], s["desativados"],
                    s["erros_detalhe"], s["status"])
    if dry_run:
        for modulo, itens in amostras.items():
            print(f"\n=== Amostra ({modulo}) ===")
            print(json.dumps(itens, ensure_ascii=False, indent=2, default=str))
        if erros:
            print("\n=== Erros (primeiros 20) ===")
            print(json.dumps(erros[:20], ensure_ascii=False, indent=2, default=str))

    if status == "falha" and alertar and not dry_run:
        await alertar(run)
    return run


async def alertar_por_email(run: dict) -> None:
    """Avisa a equipe (EMAIL_SUPORTE ou SIGAA_ALERTA_EMAIL) sobre a falha."""
    from services.email import EMAIL_SUPORTE, enviar_email

    destino = os.getenv("UNIRIO_ALERTA_EMAIL") or os.getenv("SIGAA_ALERTA_EMAIL") or EMAIL_SUPORTE
    linhas = [f"- {m}: {s['status']} (coletados={s['coletados']})" for m, s in run["modulos"].items()]
    detalhes = "\n".join(f"- {e}" for e in run["erros"][:20])
    await enviar_email({
        "to": [destino],
        "subject": "[UniResu] Falha no sync semanal da UNIRIO",
        "text": (
            "O sync semanal de projetos dos portais da UNIRIO falhou. Nenhum projeto foi "
            "desativado nos módulos com falha.\n\n"
            f"Run: {run.get('_id')}\nIniciada em: {run['iniciada_em']:%d/%m/%Y %H:%M} UTC\n\n"
            "Módulos:\n" + "\n".join(linhas) + "\n\nErros (primeiros 20):\n" + detalhes
        ),
    })


def capturar(cfg: UnirioConfig, max_detalhes: int = 2) -> None:
    """Modo diagnóstico: imprime o HTML bruto da 1ª página de cada listagem e
    dos primeiros links de detalhe encontrados. Não usa o MongoDB.

    Serve para atualizar o parser e as fixtures de teste quando o layout dos
    portais muda (ou quando a máquina de desenvolvimento não alcança a UNIRIO).
    """
    client = UnirioClient(cfg)
    for modulo in cfg.modulos:
        url = url_inicial(cfg, modulo)
        html = client.get(url)
        _bloco(f"{modulo} listagem", url, html)
        links = parser.links_de_detalhe(html, modulo, BASES[modulo])
        print(f"### {modulo}: {len(links)} link(s) de detalhe reconhecidos; "
              f"próxima página: {parser.proxima_pagina(html, url)}", flush=True)
        for link in links[:max_detalhes]:
            _bloco(f"{modulo} detalhe", link, client.get(link))


def _bloco(nome: str, url: str, html: str) -> None:
    print(f"\n===== CAPTURA INICIO [{nome}] {url} ({len(html)} chars) =====", flush=True)
    print(html, flush=True)
    print(f"===== CAPTURA FIM [{nome}] =====\n", flush=True)


async def main(argv: list[str]) -> int:
    load_dotenv()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    cfg = UnirioConfig.from_env()

    if "--captura" in argv:
        await asyncio.to_thread(capturar, cfg)
        return 0

    dry_run = "--dry-run" in argv or os.getenv("UNIRIO_DRY_RUN", "").lower() in ("1", "true", "yes")
    if dry_run:
        run = await executar_sync(None, cfg, dry_run=True)
        return 1 if run["status"] == "falha" else 0

    from database.connection import Database

    await Database.connect()
    try:
        run = await executar_sync(Database.get_db(), cfg, alertar=alertar_por_email)
    finally:
        await Database.disconnect()
    return 1 if run["status"] == "falha" else 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main(sys.argv[1:])))
