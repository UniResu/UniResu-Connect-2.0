"""
Projetos de extensão da PUC-Campinas, a partir da página pública
"Projetos de Extensão" do portal da universidade.

A página lista os Projetos de Atividades de Extensão Institucional (PAEI)
do ciclo vigente, agrupados pelos quatro Programas Institucionais de
Extensão (PIE). Cada projeto aparece como um bloco de texto rotulado:

    DOCENTE: CAIO DE SALVI LAZANEO
    ESCOLA: ELC
    FACULDADE: Cinema e Audiovisual
    TÍTULO: Cartas do Vida Nova: filmes-cartas e produção partilhada do conhecimento
    PÚBLICO: Escola E. Profa. ..., Conj. Habitacional Vida Nova, Campinas
    RESUMO: estimular práticas de criação audiovisual ...

A vigência do ciclo vem numa linha "Vigência de 01/08/2026 a 31/01/2029".
A mesma página tem, mais abaixo, ciclos antigos em outro formato; a coleta
lê só o trecho do ciclo vigente. Não há e-mail nem página por projeto: o
link de detalhe é a própria página.
"""

import re
import unicodedata
from dataclasses import dataclass
from datetime import date
from typing import Optional

from bs4 import BeautifulSoup

from services.http_client import ClienteHttp, ErroColeta
from services.sigaa.parser import SITUACAO_EM_EXECUCAO, normalizar

# O endereço antigo (/projetos-de-extensao/) redireciona para esta página.
URL_EXTENSAO = "https://www.puc-campinas.edu.br/extensao/"

ROTULOS = ("DOCENTE", "ESCOLA", "FACULDADE", "TÍTULO", "PÚBLICO", "RESUMO")
_ROTULOS_RE = "|".join(ROTULOS)
_RE_CAMPO = re.compile(rf"({_ROTULOS_RE})\s*:\s*(.*?)(?=(?:{_ROTULOS_RE})\s*:|PIE\s*\d|$)", re.S)
_RE_VIGENCIA = re.compile(r"Vig[êe]ncia de (\d{2}/\d{2}/\d{4}) a (\d{2}/\d{2}/\d{4})", re.I)
_RE_PIE = re.compile(r"PIE\s*(\d)\s*[–-]\s*([^\n]+)")
# Onde começam os ciclos antigos (fim do trecho vigente).
_RE_FIM_CICLO = re.compile(r"Projetos de Extens[ãa]o\s+Anos?\s+de|Anos? de 20\d\d|Bi[êe]nio|PLANOS DE TRABALHO", re.I)


class PucCampErro(ErroColeta):
    pass


@dataclass
class PucCampConfig:
    url_extensao: str = URL_EXTENSAO
    pausa_segundos: float = 2.0
    timeout_segundos: float = 60.0
    max_tentativas: int = 3


class PucCampClient(ClienteHttp):
    erro = PucCampErro
    nome = "PUC-Campinas"


def texto_da_pagina(html: str) -> str:
    """Texto corrido da página, uma linha por bloco, sem scripts nem estilos."""
    soup = BeautifulSoup(html, "html.parser")
    for tag in soup(["script", "style", "noscript", "svg"]):
        tag.decompose()
    texto = soup.get_text("\n")
    linhas = (" ".join(linha.split()) for linha in texto.splitlines())
    return "\n".join(linha for linha in linhas if linha)


def _iso(data_br: str) -> Optional[str]:
    try:
        dia, mes, ano = data_br.split("/")
        return date(int(ano), int(mes), int(dia)).isoformat()
    except (ValueError, AttributeError):
        return None


_MINUSCULAS = {"de", "da", "do", "das", "dos", "e"}


def nome_proprio(nome: str) -> str:
    """"ANA CECÍLIA MATTEI DE ARRUDA CAMPOS" vira "Ana Cecília Mattei de Arruda Campos"."""
    partes = nome.strip().lower().split()
    return " ".join(p if (p in _MINUSCULAS and i > 0) else p[:1].upper() + p[1:] for i, p in enumerate(partes))


def _sem_acento(txt: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFKD", txt) if not unicodedata.combining(c))


def nomes_da_tabela(texto: str) -> dict[str, str]:
    """A página abre com uma tabela "título / docente" em que os nomes vêm em
    caixa normal. Devolve {nome normalizado: nome como publicado}, para os
    blocos (que trazem o nome em maiúsculas) exibirem a grafia original."""
    nomes: dict[str, str] = {}
    for linha in texto.splitlines():
        if linha.isupper() or ":" in linha or len(linha.split()) < 2 or len(linha) > 80:
            continue
        palavras = linha.split()
        if all(p[:1].isupper() or p.lower() in _MINUSCULAS for p in palavras) and not any(c.isdigit() for c in linha):
            nomes.setdefault(normalizar(linha), linha)
    return nomes


def trecho_vigente(texto: str) -> tuple[str, Optional[str], Optional[str]]:
    """Trecho do ciclo vigente (da linha de vigência até o início dos ciclos
    antigos) e as datas de início e fim do ciclo, em ISO."""
    m = _RE_VIGENCIA.search(texto)
    if not m:
        return "", None, None
    resto = texto[m.end():]
    fim = _RE_FIM_CICLO.search(resto)
    return (resto[:fim.start()] if fim else resto), _iso(m.group(1)), _iso(m.group(2))


def parse_extensao(html: str) -> list[dict]:
    """Projetos do ciclo vigente, cada um com os campos rotulados e o PIE."""
    texto = texto_da_pagina(html)
    trecho, inicio, fim = trecho_vigente(texto)
    nomes = nomes_da_tabela(texto)
    projetos: list[dict] = []
    vistos: set[str] = set()
    for bloco in re.split(r"(?=DOCENTE\s*:)", trecho):
        if not bloco.strip().startswith("DOCENTE"):
            continue
        # PIE do bloco: o último cabeçalho "PIE n – nome" antes dele no trecho.
        pos = trecho.find(bloco)
        pies = list(_RE_PIE.finditer(trecho[:pos]))
        pie = pies[-1].group(2).strip() if pies else None
        campos = {rotulo: " ".join(valor.split()) for rotulo, valor in _RE_CAMPO.findall(bloco)}
        titulo = campos.get("TÍTULO", "").strip()
        docente = campos.get("DOCENTE", "").strip()
        if not titulo or not docente or normalizar(titulo) in vistos:
            continue
        vistos.add(normalizar(titulo))
        projetos.append({
            "docente": nomes.get(normalizar(docente)) or nome_proprio(docente),
            "escola": campos.get("ESCOLA") or None,
            "faculdade": campos.get("FACULDADE") or None,
            "titulo": titulo,
            "publico": campos.get("PÚBLICO") or None,
            "resumo": campos.get("RESUMO") or None,
            "programa": pie,
            "inicio": inicio,
            "fim": fim,
        })
    return projetos


def listar_extensao(client: PucCampClient) -> list[dict]:
    return parse_extensao(client.get(client.cfg.url_extensao))


def _situacao(inicio: Optional[str], fim: Optional[str], hoje: date) -> str:
    if inicio and hoje.isoformat() < inicio:
        return "NÃO INICIADO"
    if fim and hoje.isoformat() > fim:
        return "FINALIZADO"
    return SITUACAO_EM_EXECUCAO


def _frase(txt: Optional[str]) -> Optional[str]:
    """Primeira letra maiúscula (os resumos da página começam em minúscula)."""
    if not txt:
        return None
    return txt[:1].upper() + txt[1:]


def identificador(titulo: str) -> str:
    """Id estável do projeto na fonte (a página não publica código)."""
    base = re.sub(r"[^a-z0-9]+", "-", _sem_acento(titulo).lower()).strip("-")
    return base[:120]


def registro_extensao(proj: dict, hoje: Optional[date] = None, url: str = URL_EXTENSAO) -> dict:
    """Projeto da página -> registro no formato de repositorio.upsert_projetos."""
    hoje = hoje or date.today()
    faculdade = proj.get("faculdade")
    unidade = None
    if faculdade:
        unidade = faculdade if faculdade.lower().startswith("faculdade") else f"Faculdade de {faculdade}"
    descricao = _frase(proj.get("resumo"))
    if proj.get("publico"):
        descricao = (descricao + "\n\n" if descricao else "") + f"Público: {proj['publico']}"
    extras = {
        "area_tematica": proj.get("programa"),
        "escola": proj.get("escola"),
    }
    return {
        "modulo": "extensao",
        "puccamp_id": identificador(proj["titulo"]),
        "codigo": None,
        "titulo": proj["titulo"],
        "coordenador": proj.get("docente"),
        "email": None,  # a página não publica e-mail
        "unidade": unidade,
        "situacao": _situacao(proj.get("inicio"), proj.get("fim"), hoje),
        "ano": (proj.get("inicio") or "")[:4] or None,
        "categoria": "Projeto de Atividade de Extensão Institucional",
        "link_detalhe": url,
        "descricao": descricao,
        "periodo_inicio": proj.get("inicio"),
        "periodo_fim": proj.get("fim"),
        "extras": {k: v for k, v in extras.items() if v},
        "detalhe_ok": True,
    }
