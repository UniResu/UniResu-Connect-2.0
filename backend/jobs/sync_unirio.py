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
import inspect
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
from services.sigaa.parser import SITUACAO_EM_EXECUCAO
from services.unirio import parser
from services.unirio.config import UnirioConfig
from services.unirio.scraper import (
    COLETORES,
    UnirioClient,
    anos_disponiveis_pesquisa,
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
        "config": {"modulos": cfg.modulos, "extensao_status": cfg.extensao_status, "max_paginas": cfg.max_paginas,
                   "detalhes": cfg.detalhes},
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


async def ids_sem_detalhe(db, modulo: str, cfg: UnirioConfig) -> set[str]:
    """Ids (unirio_id) cujo detalhe não precisa ser reaberto nesta execução.

    Modo `incremental`: projetos já gravados com detalhe. Na pesquisa, os que
    ainda constam como em execução ficam de fora do conjunto (são reabertos
    para perceber o encerramento); na extensão a própria listagem já vem
    filtrada por "em andamento", então sumir dela é o sinal de encerramento.
    Modo `completo`: conjunto vazio (reabre tudo).
    """
    if cfg.detalhes != "incremental":
        return set()
    filtro: dict = {"origem": UNIRIO.origem, "modulo": modulo, "detalhe_ok": True,
                    UNIRIO.campo_id: {"$ne": None}}
    if modulo == "pesquisa":
        filtro["situacao"] = {"$ne": SITUACAO_EM_EXECUCAO}
    cursor = db.projetos.find(filtro, {UNIRIO.campo_id: 1})
    return {str(doc[UNIRIO.campo_id]) for doc in await cursor.to_list(length=None)}


def _coletar(coletor, client, pular: set[str]):
    """Chama o coletor passando `pular_detalhe` quando ele aceita (os coletores
    reais aceitam; dublês de teste podem receber só o cliente)."""
    if "pular_detalhe" in inspect.signature(coletor).parameters:
        return coletor(client, pular_detalhe=pular)
    return coletor(client)


async def _executar(db, cfg, coletores, client, alertar, dry_run, run, run_id, inicio) -> dict:
    modulos: dict = {}
    erros: list[dict] = []
    amostras: dict = {}
    falhou = False

    for modulo in cfg.modulos:
        stats = {"coletados": 0, "novos": 0, "atualizados": 0, "desativados": 0,
                 "erros_detalhe": 0, "detalhes_pulados": 0, "paginas": 0, "completa": True, "status": "sucesso"}
        try:
            pular = set() if dry_run or db is None else await ids_sem_detalhe(db, modulo, cfg)
            res = await asyncio.to_thread(_coletar, coletores[modulo], client, pular)
        except Exception as e:  # falha na busca/listagem do módulo
            logger.error("UNIRIO %s: busca falhou: %s", modulo, e)
            erros.append({"modulo": modulo, "erro": f"busca falhou: {e}"})
            stats["status"] = "falha"
            falhou = True
            modulos[modulo] = stats
            continue

        erros.extend(res.erros)
        stats["erros_detalhe"] = len(res.erros)
        stats["detalhes_pulados"] = getattr(res, "pulados", 0)
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
        logger.info("  %-9s coletados=%d páginas=%d%s novos=%d atualizados=%d desativados=%d erros_detalhe=%d "
                    "detalhes_pulados=%d [%s]",
                    modulo, s["coletados"], s["paginas"], "" if s["completa"] else " (incompleta)",
                    s["novos"], s["atualizados"], s["desativados"], s["erros_detalhe"], s["detalhes_pulados"],
                    s["status"])
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
                # Portal da Pesquisa: a listagem só existe após o POST da busca,
                # enviado à página do formulário (default/index).
                url_form = cfg.url_pesquisa_formulario
                html_form = client.get(url_form)
                _salvar(pasta / "pesquisa_formulario.html", "pesquisa formulário", url_form, html_form)
                html, url = _diagnostico_pesquisa(client, url_form, html_form, pasta)
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


def _diagnostico_pesquisa(client: UnirioClient, url_form: str, html_form: str, pasta: Path) -> tuple[str, str]:
    """Envia a busca do Portal da Pesquisa sem filtro e com o último ano, e
    registra status, redirecionamentos, cookies e tamanho de cada resposta.
    Devolve (html, url final) da variante que listou algo (ou da última)."""
    from services.unirio.scraper import exige_busca, payload_pesquisa

    anos = anos_disponiveis_pesquisa(html_form)
    print(f"### pesquisa: anos no formulário: {anos[:3]}...{anos[-3:]} ({len(anos)}); "
          f"cookies após GET: {sorted(client.session.cookies.get_dict().keys())}", flush=True)
    variantes = [("vazia", None), (anos[-1], anos[-1])] if anos else [("vazia", None)]
    escolhido = (html_form, url_form)
    for i, (nome, ano) in enumerate(variantes):
        if i > 0:
            # o _formkey do web2py é de uso único: formulário novo a cada POST
            html_form = client.get(url_form)
        try:
            resp = client.request_raw("POST", url_form, data=payload_pesquisa(html_form, ano))
        except ErroColeta as e:
            print(f"### pesquisa POST {nome}: FALHOU ({e})", flush=True)
            continue
        historico = [(r.status_code, r.headers.get("Location")) for r in resp.history]
        itens = parser.parse_listagem(resp.text, "pesquisa", str(resp.url))
        print(f"### pesquisa POST {nome}: status={resp.status_code} final={resp.url} "
              f"redirecionamentos={historico} tamanho={len(resp.text)} exige_busca={exige_busca(resp.text)} "
              f"itens={len(itens)}", flush=True)
        _salvar(pasta / f"pesquisa_post_{nome}.html", f"pesquisa POST {nome}", str(resp.url), resp.text)
        if itens:
            escolhido = (resp.text, str(resp.url))
            break  # a busca sem filtro já lista tudo; não precisamos das outras variantes
    return escolhido


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
