"""
Job semanal: sincroniza projetos de pesquisa e extensão dos portais da UNIRIO.

Uso (a partir de backend/):
    python -m jobs.sync_unirio              # sync normal (grava no MongoDB)
    python -m jobs.sync_unirio --dry-run    # coleta e mostra o resultado, sem gravar
    python -m jobs.sync_unirio --captura    # salva o HTML das páginas (diagnóstico)

Agendado via GitHub Actions (.github/workflows/sync-unirio.yml).

Mesmas regras de segurança do sync do SIGAA:
- Um módulo que retorna 0 itens, cuja busca falha ou cuja listagem ficou
  incompleta é tratado como FALHA: nada daquele módulo é desativado, um
  alerta é enviado e o processo sai com código 1.
- Falha no detalhe de um item não aborta nada — o item é salvo com os dados
  da listagem e o erro vai para o log da run.
- Cada execução é registrada em `sigaa_sync_runs` com `fonte: "unirio"`
  (mesma collection do SIGAA, para reaproveitar o usuário restrito do Atlas).
  Se o processo for morto no meio (timeout do Actions), a run fica "abortada".
"""

import asyncio
import base64
import gzip
import json
import logging
import os
import sys
from dataclasses import replace
from datetime import datetime, timezone
from pathlib import Path
from typing import Awaitable, Callable, Optional

from dotenv import load_dotenv

from services.fontes import UNIRIO
from services.http_client import ErroColeta
from services.sigaa import repositorio
from services.unirio import parser
from services.unirio.config import UnirioConfig
from services.unirio.scraper import (
    COLETORES,
    UnirioClient,
    anos_disponiveis_pesquisa,
    buscar_pesquisa,
    prefixo_detalhe,
    url_inicial,
)

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
    if not dry_run and cfg.max_detalhes:
        logger.warning("UNIRIO_MAX_DETALHES=%d ignorado no sync real (só vale em --dry-run/--captura).",
                       cfg.max_detalhes)
        cfg = replace(cfg, max_detalhes=0)
    client = client or UnirioClient(cfg)
    inicio = datetime.now(timezone.utc)
    run = {
        "fonte": UNIRIO.origem,
        "iniciada_em": inicio,
        "status": "executando",
        "dry_run": dry_run,
        "config": {"modulos": cfg.modulos, "extensao_status": cfg.extensao_status, "max_paginas": cfg.max_paginas},
    }
    run_id = None
    if not dry_run:
        await repositorio.garantir_modulo(db)
        run_id = (await db.sigaa_sync_runs.insert_one(dict(run))).inserted_id

    try:
        return await _executar(db, cfg, coletores, client, alertar, dry_run, run, run_id, inicio)
    except BaseException as e:  # inclui CancelledError/KeyboardInterrupt (SIGINT do Actions)
        if run_id is not None:
            await db.sigaa_sync_runs.update_one(
                {"_id": run_id},
                {"$set": {"status": "abortada", "finalizada_em": datetime.now(timezone.utc),
                          "erro": f"{type(e).__name__}: {e}"}},
            )
        raise


async def _executar(db, cfg, coletores, client, alertar, dry_run, run, run_id, inicio) -> dict:
    modulos: dict = {}
    erros: list[dict] = []
    amostras: dict = {}
    falhou = False

    for modulo in cfg.modulos:
        stats = {"coletados": 0, "novos": 0, "atualizados": 0, "desativados": 0,
                 "erros_detalhe": 0, "paginas": 0, "completa": True, "status": "sucesso"}
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
        stats["completa"] = res.completa
        amostras[modulo] = res.itens[:3]

        if not res.itens:
            stats["status"] = "falha"
            falhou = True
            erros.append({"modulo": modulo, "erro": "coleta retornou 0 resultados"})
        elif not res.completa:
            # Lemos só parte da listagem: gravamos o que veio (upsert é seguro),
            # mas não desativamos nada e tratamos como falha para alertar.
            stats["status"] = "falha"
            falhou = True
            erros.append({"modulo": modulo, "erro": "listagem incompleta (teto de páginas ou paginação "
                                                    "não reconhecida); nada foi desativado",
                          "paginas": res.paginas})
            if not dry_run:
                up = await repositorio.upsert_projetos(db, res.itens, fonte=UNIRIO)
                stats["novos"], stats["atualizados"] = up.novos, up.atualizados
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
        logger.info("  %-9s coletados=%d páginas=%d%s novos=%d atualizados=%d desativados=%d erros_detalhe=%d [%s]",
                    modulo, s["coletados"], s["paginas"], "" if s["completa"] else " (incompleta)",
                    s["novos"], s["atualizados"], s["desativados"], s["erros_detalhe"], s["status"])
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
    """Avisa a equipe (UNIRIO_ALERTA_EMAIL, SIGAA_ALERTA_EMAIL ou EMAIL_SUPORTE) sobre a falha."""
    from services.email import EMAIL_SUPORTE, enviar_email

    destino = os.getenv("UNIRIO_ALERTA_EMAIL") or os.getenv("SIGAA_ALERTA_EMAIL") or EMAIL_SUPORTE
    linhas = [f"- {m}: {s['status']} (coletados={s['coletados']}, páginas={s['paginas']})"
              for m, s in run["modulos"].items()]
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


# ─────────────────────────────────────────────
#  Modo captura (diagnóstico)
# ─────────────────────────────────────────────

LINHA_B64 = 8000  # tamanho de cada linha base64 impressa no log


def capturar(cfg: UnirioConfig, max_detalhes: int = 2, destino: Optional[str] = None) -> int:
    """Salva o HTML bruto da 1ª página de cada listagem e dos primeiros links de
    detalhe em `destino` (padrão: UNIRIO_CAPTURA_DIR ou ./captura) e imprime um
    índice. Também imprime cada página em gzip+base64 fatiado em linhas, para
    quem só tem acesso ao log do Actions (o artifact é o caminho confortável).

    Não usa o MongoDB. Falha em um módulo não impede a captura do outro.
    Devolve o número de módulos que falharam por completo.
    """
    pasta = Path(destino or os.getenv("UNIRIO_CAPTURA_DIR") or "captura")
    pasta.mkdir(parents=True, exist_ok=True)
    client = UnirioClient(cfg)
    falhas = 0
    for modulo in cfg.modulos:
        url = url_inicial(cfg, modulo)
        try:
            html = client.get(url)
            if modulo == "pesquisa":
                # Portal da Pesquisa: a listagem só existe após o POST da busca.
                html_form = html
                _salvar(pasta / "pesquisa_formulario.html", "pesquisa formulário", url, html_form)
                html = buscar_pesquisa(client, html_form=html_form)
                _salvar(pasta / "pesquisa_busca_vazia.html", "pesquisa busca vazia (POST)", url, html)
                anos = anos_disponiveis_pesquisa(html_form)
                if anos:
                    html_ano = buscar_pesquisa(client, ano=anos[-1], html_form=html_form)
                    _salvar(pasta / f"pesquisa_busca_{anos[-1]}.html", f"pesquisa busca {anos[-1]} (POST)",
                            url, html_ano)
                    if not parser.links_de_detalhe(html, modulo, url, prefixo_detalhe(cfg, modulo)):
                        html = html_ano
        except ErroColeta as e:
            print(f"### {modulo}: listagem FALHOU ({e})", flush=True)
            falhas += 1
            continue
        _salvar(pasta / f"{modulo}_listagem.html", f"{modulo} listagem", url, html)
        prefixo = prefixo_detalhe(cfg, modulo)
        links = parser.links_de_detalhe(html, modulo, url, prefixo)
        itens = parser.parse_listagem(html, modulo, url, prefixo)
        print(f"### {modulo}: {len(links)} link(s) de detalhe, {len(itens)} item(ns) reconhecidos; "
              f"próxima página: {parser.proxima_pagina(html, url)}", flush=True)
        for link in links[:max_detalhes]:
            try:
                _salvar(pasta / f"{modulo}_detalhe_{parser.id_da_url(link)}.html",
                        f"{modulo} detalhe", link, client.get(link))
            except ErroColeta as e:
                print(f"### {modulo}: detalhe {link} FALHOU ({e})", flush=True)
    print(f"### captura salva em {pasta.resolve()}", flush=True)
    return falhas


def _salvar(arquivo: Path, nome: str, url: str, html: str) -> None:
    arquivo.write_text(html, encoding="utf-8")
    dados = base64.b64encode(gzip.compress(html.encode("utf-8"))).decode("ascii")
    fatias = [dados[i:i + LINHA_B64] for i in range(0, len(dados), LINHA_B64)] or [""]
    print(f"===== CAPTURA [{nome}] {url} -> {arquivo.name} ({len(html)} chars, {len(fatias)} linhas b64) =====",
          flush=True)
    for i, fatia in enumerate(fatias, 1):
        print(f"CAPTURA-B64 {arquivo.name} {i}/{len(fatias)} {fatia}", flush=True)


async def main(argv: list[str]) -> int:
    load_dotenv()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    cfg = UnirioConfig.from_env()

    if "--captura" in argv:
        falhas = await asyncio.to_thread(capturar, cfg, cfg.max_detalhes or 2)
        return 1 if falhas == len(cfg.modulos) else 0

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
