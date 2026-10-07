"""
Projetos e programas de extensão da UFV (Universidade Federal de Viçosa),
a partir do portal de dados abertos da universidade (dados.ufv.br, CKAN).

Em vez de raspar páginas, a coleta consulta a API DataStore do CKAN com SQL
e pede só o que está em execução hoje (DataInicio <= hoje <= DataTermino):
poucas requisições, sem carga sobre o sistema de registro da UFV.

Os projetos de PESQUISA vêm do mesmo portal, mas por outro caminho: o
DataStore do CKAN só carregou as linhas até 2010, enquanto o CSV completo
do recurso (uns 225 MB, uma linha por participante, atualizado todo mês)
vai até os projetos registrados hoje. Baixamos o CSV inteiro em uma única
requisição e filtramos localmente os projetos vigentes.
"""

import csv
import io
import json
import logging
import os
import re
from collections import Counter
from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Iterable, Optional

from services.http_client import ClienteHttp, ErroColeta
from services.sigaa.parser import SITUACAO_EM_EXECUCAO

logger = logging.getLogger(__name__)

URL_API = "https://dados.ufv.br/api/3/action/datastore_search_sql"
# Recurso "Projetos e programas de extensão" (dataset projetos-e-programas-de-extensao).
RECURSO_EXTENSAO = "07e95bf4-c474-4f64-b677-f7686e861aa2"
# CSV completo do recurso "Projetos de pesquisa" (dataset projetos-de-pesquisa).
URL_CSV_PESQUISA = ("https://dados.ufv.br/dataset/95043f7b-631e-4a91-ab33-3f29dbfe6904/resource/"
                    "7defe111-4adb-43d7-b3c0-5ca149210a5c/download/projetos-pesquisa.csv")
# Página pública de detalhe de um projeto de pesquisa (parâmetro: numero_registro).
URL_DETALHE_PESQUISA = "https://www2.dti.ufv.br/sisppg/scripts/projetos/verProjeto.php?registro={registro}"
# Situações do CSV de pesquisa que contam como projeto vigente. As demais são
# "Concluído", "Seleção de IC - Projeto inscrito" (ainda não começou),
# "Revisado", "Excluído", "Cancelado" e "Não Registrado".
PESQUISA_SITUACOES_VIGENTES = ("Registrado",)
# Papéis no projeto, do mais ao menos indicado para figurar como coordenação.
PESQUISA_PAPEIS_COORDENACAO = ("Líder", "Co-Líder", "Executor")

COLUNAS = ("CodigoLancamento", "NumeroRegistro", "Tipo", "Titulo", "AreaCNPQ", "AreaTematica",
           "AreaTematica2", "Envolvidos", "DataInicio", "DataTermino", "LinhaExtensao", "Objetivo",
           "PalavrasChave", "Financiado", "URL")


class UfvErro(ErroColeta):
    pass


def _env(nome: str, padrao):
    valor = os.getenv(nome)
    return padrao if valor is None or valor.strip() == "" else valor


@dataclass
class UfvConfig:
    url_api: str = URL_API
    recurso_extensao: str = RECURSO_EXTENSAO
    url_csv_pesquisa: str = URL_CSV_PESQUISA
    tamanho_pagina: int = 200
    pausa_segundos: float = 2.0
    pausa_proporcional: float = 1.0
    timeout_segundos: float = 300.0  # o CSV de pesquisa tem uns 225 MB
    max_tentativas: int = 3
    backoff_base_segundos: float = 10.0
    modulos: list[str] = field(default_factory=lambda: ["extensao", "pesquisa"])
    pesquisa_situacoes: tuple[str, ...] = PESQUISA_SITUACOES_VIGENTES
    # Projetos "Registrado" muito antigos nunca foram encerrados no sistema;
    # só entram os registrados de poucos anos para cá.
    pesquisa_ano_minimo: int = field(default_factory=lambda: date.today().year - 4)

    @classmethod
    def from_env(cls) -> "UfvConfig":
        cfg = cls()
        cfg.url_api = str(_env("UFV_URL_API", cfg.url_api))
        cfg.recurso_extensao = str(_env("UFV_RECURSO_EXTENSAO", cfg.recurso_extensao))
        cfg.url_csv_pesquisa = str(_env("UFV_URL_CSV_PESQUISA", cfg.url_csv_pesquisa))
        cfg.tamanho_pagina = max(10, int(_env("UFV_TAMANHO_PAGINA", cfg.tamanho_pagina)))
        cfg.modulos = [m.strip().lower() for m in str(_env("UFV_MODULOS", ",".join(cfg.modulos))).split(",")
                       if m.strip()]
        cfg.pesquisa_situacoes = tuple(s.strip() for s in
                                       str(_env("UFV_PESQUISA_SITUACOES", ",".join(cfg.pesquisa_situacoes))).split(",")
                                       if s.strip())
        cfg.pesquisa_ano_minimo = int(_env("UFV_PESQUISA_ANO_MINIMO", cfg.pesquisa_ano_minimo))
        return cfg


class UfvClient(ClienteHttp):
    erro = UfvErro
    nome = "UFV"


def sql_extensao_em_execucao(recurso: str, limite: int, deslocamento: int) -> str:
    colunas = ", ".join(f'"{c}"' for c in COLUNAS)
    return (f'SELECT {colunas} FROM "{recurso}" '
            f'WHERE "DataInicio" <= NOW() AND "DataTermino" >= NOW() '
            f'ORDER BY "CodigoLancamento" LIMIT {int(limite)} OFFSET {int(deslocamento)}')


def consultar(client: UfvClient, sql: str) -> list[dict]:
    texto = client.get(client.cfg.url_api, params={"sql": sql})
    try:
        corpo = json.loads(texto)
    except ValueError as e:
        raise UfvErro(f"resposta não é JSON: {texto[:200]!r}") from e
    if not corpo.get("success"):
        raise UfvErro(f"API do CKAN recusou a consulta: {corpo.get('error')}")
    return corpo["result"]["records"]


def listar_extensao(client: UfvClient) -> list[dict]:
    """Todos os projetos/programas de extensão em execução hoje, página a página."""
    cfg = client.cfg
    registros: list[dict] = []
    deslocamento = 0
    while True:
        pagina = consultar(client, sql_extensao_em_execucao(cfg.recurso_extensao, cfg.tamanho_pagina, deslocamento))
        registros.extend(pagina)
        if len(pagina) < cfg.tamanho_pagina:
            break
        deslocamento += cfg.tamanho_pagina
        if deslocamento > 50_000:  # proteção contra laço sem fim
            raise UfvErro("paginação não terminou")
    logger.info("UFV extensão: %d projetos/programas em execução", len(registros))
    return registros


# "NOME (Coordenador, 01/02/2024 a 31/12/2026), OUTRO NOME (Colaborador(a) Voluntário(a), ...)"
_COORDENADOR = re.compile(
    r"(?:^|,\s*)([^,()]+?)\s*\(Coordenador\w*\s*,\s*(\d{2}/\d{2}/\d{4})\s*a\s*(\d{2}/\d{2}/\d{4})\)")


def _data_br(texto: str) -> Optional[date]:
    try:
        return datetime.strptime(texto, "%d/%m/%Y").date()
    except ValueError:
        return None


def coordenador_atual(envolvidos: Optional[str], hoje: Optional[date] = None) -> Optional[str]:
    """Nome do(a) coordenador(a) vigente na lista de envolvidos.

    Prefere quem coordena no período que inclui hoje (o mais recente, se
    houver mais de um); senão, quem coordenou por último.
    """
    hoje = hoje or date.today()
    candidatos = []
    for m in _COORDENADOR.finditer(envolvidos or ""):
        nome = m.group(1).strip()
        inicio, fim = _data_br(m.group(2)), _data_br(m.group(3))
        if nome and inicio and fim:
            candidatos.append((inicio, fim, nome))
    vigentes = [c for c in candidatos if c[0] <= hoje <= c[1]]
    if vigentes:
        return max(vigentes, key=lambda c: (c[0], c[1]))[2]   # quem assumiu por último
    if candidatos:
        return max(candidatos, key=lambda c: (c[1], c[0]))[2]  # quem coordenou por último
    return None


def _data_iso(valor) -> Optional[str]:
    texto = str(valor or "")[:10]
    return texto if re.fullmatch(r"\d{4}-\d{2}-\d{2}", texto) else None


def _lista(texto: Optional[str]) -> list[str]:
    return [p.strip() for p in re.split(r"[,;]", texto or "") if p.strip()]


def registro_extensao(rec: dict, hoje: Optional[date] = None) -> dict:
    """Linha do CKAN -> registro no formato aceito por repositorio.upsert_projetos."""
    inicio = _data_iso(rec.get("DataInicio"))
    tematica = [t for t in (rec.get("AreaTematica"), rec.get("AreaTematica2")) if t and str(t).strip()]
    financiado = str(rec.get("Financiado") or "").strip()
    extras = {
        "area_cnpq": (rec.get("AreaCNPQ") or "").strip() or None,
        "area_tematica": tematica[0].strip() if tematica else None,
        "linhas_extensao": _lista(rec.get("LinhaExtensao")),
        "palavras_chave": _lista(rec.get("PalavrasChave")),
        "financiamento": ("Com financiamento" if financiado.lower().startswith("s")
                          else "Sem financiamento" if financiado else None),
    }
    return {
        "modulo": "extensao",
        "ufv_id": str(int(rec["CodigoLancamento"])) if rec.get("CodigoLancamento") is not None else None,
        "codigo": (rec.get("NumeroRegistro") or "").strip() or None,
        "titulo": (rec.get("Titulo") or "").strip(),
        "coordenador": coordenador_atual(rec.get("Envolvidos"), hoje),
        "email": None,  # o conjunto de dados não traz e-mail
        "unidade": None,
        "situacao": SITUACAO_EM_EXECUCAO,
        "ano": inicio[:4] if inicio else None,
        "categoria": (rec.get("Tipo") or "").strip() or None,  # Projeto ou Programa
        "link_detalhe": (rec.get("URL") or "").strip() or None,
        "descricao": (rec.get("Objetivo") or "").strip() or None,
        "periodo_inicio": inicio,
        "periodo_fim": _data_iso(rec.get("DataTermino")),
        "extras": {k: v for k, v in extras.items() if v not in (None, [], "")},
        "detalhe_ok": True,
    }


# ── Pesquisa (CSV completo) ──────────────────────────────────────────────────

def _ano_int(valor) -> Optional[int]:
    try:
        return int(float(str(valor).strip()))
    except (TypeError, ValueError):
        return None


def _vigente(linha: dict, cfg: UfvConfig, hoje: date) -> bool:
    """Linha do CSV pertence a um projeto em execução hoje?"""
    if (linha.get("situacao") or "").strip() not in cfg.pesquisa_situacoes:
        return False
    ano = _ano_int(linha.get("ano"))
    if ano is None or ano < cfg.pesquisa_ano_minimo:
        return False
    inicio = _data_iso(linha.get("data_inicio"))
    fim = _data_iso(linha.get("data_fim"))
    if inicio and date.fromisoformat(inicio) > hoje:
        return False
    if fim and date.fromisoformat(fim) < hoje:
        return False
    return True


def agrupar_pesquisa(linhas: Iterable[dict], cfg: UfvConfig, hoje: Optional[date] = None,
                     estatisticas: Optional[dict] = None) -> list[dict]:
    """Junta as linhas (uma por participante) em um dicionário por projeto,
    só para os projetos vigentes. `estatisticas`, quando passado, recebe a
    contagem de linhas por situação e ano recente, útil no dry-run."""
    hoje = hoje or date.today()
    projetos: dict[str, dict] = {}
    contagem: Counter = Counter()
    total = 0
    for linha in linhas:
        total += 1
        ano = _ano_int(linha.get("ano"))
        if ano is not None and ano >= hoje.year - 6:
            contagem[((linha.get("situacao") or "").strip() or "(vazio)", ano)] += 1
        if not _vigente(linha, cfg, hoje):
            continue
        codigo = (linha.get("codigo_projeto") or "").strip()
        if not codigo:
            continue
        grupo = projetos.setdefault(codigo, {**linha, "equipe": []})
        nome = (linha.get("nome_pessoa") or "").strip()
        if nome:
            grupo["equipe"].append({"nome": nome, "funcao": (linha.get("tipo_participacao_projeto") or "").strip()})
    if estatisticas is not None:
        estatisticas["linhas"] = total
        estatisticas["projetos_vigentes"] = len(projetos)
        estatisticas["por_situacao_ano"] = dict(contagem)
    logger.info("UFV pesquisa: %d linhas lidas, %d projetos vigentes (situações %s, ano >= %d)",
                total, len(projetos), "/".join(cfg.pesquisa_situacoes), cfg.pesquisa_ano_minimo)
    return list(projetos.values())


def ler_csv_pesquisa(conteudo: bytes) -> Iterable[dict]:
    """Linhas do CSV (separador ';', UTF-8 com BOM), uma por participante."""
    csv.field_size_limit(10**8)
    texto = io.TextIOWrapper(io.BytesIO(conteudo), encoding="utf-8-sig", errors="replace", newline="")
    return csv.DictReader(texto, delimiter=";")


def listar_pesquisa(client: UfvClient, hoje: Optional[date] = None,
                    estatisticas: Optional[dict] = None) -> list[dict]:
    """Baixa o CSV completo de pesquisa e devolve os projetos vigentes agrupados."""
    cfg = client.cfg
    resp = client.request_raw("GET", cfg.url_csv_pesquisa)
    conteudo = resp.content
    logger.info("UFV pesquisa: CSV baixado (%.1f MB)", len(conteudo) / 1e6)
    return agrupar_pesquisa(ler_csv_pesquisa(conteudo), cfg, hoje, estatisticas)


def coordenador_pesquisa(equipe: list[dict]) -> Optional[str]:
    for papel in PESQUISA_PAPEIS_COORDENACAO:
        for pessoa in equipe:
            if pessoa.get("funcao") == papel and pessoa.get("nome"):
                return pessoa["nome"]
    return None


def _link_pesquisa(numero_registro) -> Optional[str]:
    registro = re.sub(r"\D", "", str(numero_registro or ""))
    return URL_DETALHE_PESQUISA.format(registro=registro) if registro.strip("0") else None


def registro_pesquisa(grupo: dict) -> dict:
    """Projeto agrupado do CSV -> registro no formato aceito por repositorio.upsert_projetos."""
    inicio = _data_iso(grupo.get("data_inicio"))
    ano = _ano_int(grupo.get("ano"))
    linha_pesquisa = (grupo.get("nome_linha_pesquisa") or grupo.get("linha_pesquisa") or "").strip()
    financiamento = (grupo.get("tipo_financiamento") or "").strip()
    equipe = grupo.get("equipe") or []
    extras = {
        "area_cnpq": (grupo.get("area_conhecimento_cnpq") or "").strip() or None,
        "linha_pesquisa": linha_pesquisa or None,
        "grupo_pesquisa": (grupo.get("grupo_pesquisa") or "").strip() or None,
        "palavras_chave": _lista(grupo.get("palavra_chave")),
        "modalidade": (grupo.get("modalidade_treinamento") or "").strip() or None,
        "modalidade_projeto": (grupo.get("modalidade_projeto") or "").strip() or None,
        "local_execucao": (grupo.get("local_execucao") or "").strip() or None,
        "financiamento": "Com financiamento" if financiamento else None,
        "departamento_sigla": (grupo.get("sigla_depto") or "").strip() or None,
        "equipe": equipe[:50],
    }
    return {
        "modulo": "pesquisa",
        "ufv_id": f"p{grupo['codigo_projeto'].strip()}",
        "codigo": (grupo.get("numero_registro") or "").strip() or None,
        "titulo": (grupo.get("titulo") or "").strip(),
        "coordenador": coordenador_pesquisa(equipe),
        "email": None,  # o conjunto de dados não traz e-mail
        "unidade": (grupo.get("sigla_depto") or "").strip() or None,
        "situacao": SITUACAO_EM_EXECUCAO,
        "ano": str(ano) if ano else (inicio[:4] if inicio else None),
        "categoria": (grupo.get("modalidade_treinamento") or grupo.get("modalidade_projeto") or "").strip() or None,
        "link_detalhe": _link_pesquisa(grupo.get("numero_registro")),
        "descricao": (grupo.get("resumo_dos_objetivos") or "").strip() or None,
        "periodo_inicio": inicio,
        "periodo_fim": _data_iso(grupo.get("data_fim")),
        "extras": {k: v for k, v in extras.items() if v not in (None, [], "")},
        "detalhe_ok": True,
    }
