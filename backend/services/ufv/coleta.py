"""
Projetos e programas de extensão da UFV (Universidade Federal de Viçosa),
a partir do portal de dados abertos da universidade (dados.ufv.br, CKAN).

Em vez de raspar páginas, a coleta consulta a API DataStore do CKAN com SQL
e pede só o que está em execução hoje (DataInicio <= hoje <= DataTermino):
poucas requisições, sem carga sobre o sistema de registro da UFV.

O conjunto de projetos de PESQUISA da UFV também está no portal, mas os
dados param em 2010; por isso só a extensão é coletada.
"""

import json
import logging
import os
import re
from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Optional

from services.http_client import ClienteHttp, ErroColeta
from services.sigaa.parser import SITUACAO_EM_EXECUCAO

logger = logging.getLogger(__name__)

URL_API = "https://dados.ufv.br/api/3/action/datastore_search_sql"
# Recurso "Projetos e programas de extensão" (dataset projetos-e-programas-de-extensao).
RECURSO_EXTENSAO = "07e95bf4-c474-4f64-b677-f7686e861aa2"

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
    tamanho_pagina: int = 200
    pausa_segundos: float = 2.0
    pausa_proporcional: float = 1.0
    timeout_segundos: float = 90.0
    max_tentativas: int = 3
    backoff_base_segundos: float = 10.0
    modulos: list[str] = field(default_factory=lambda: ["extensao"])

    @classmethod
    def from_env(cls) -> "UfvConfig":
        cfg = cls()
        cfg.url_api = str(_env("UFV_URL_API", cfg.url_api))
        cfg.recurso_extensao = str(_env("UFV_RECURSO_EXTENSAO", cfg.recurso_extensao))
        cfg.tamanho_pagina = max(10, int(_env("UFV_TAMANHO_PAGINA", cfg.tamanho_pagina)))
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
