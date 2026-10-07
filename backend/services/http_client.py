"""
Cliente HTTP compartilhado pelas coletas (SIGAA/UNIR e portais da UNIRIO).

Boas maneiras com os servidores públicos: pausa mínima entre QUALQUER
requisição (nunca < 1s), timeout e retry com backoff exponencial.
"""

import logging
import time
from typing import Callable, Optional, Protocol

import requests
from bs4.dammit import EncodingDetector

logger = logging.getLogger(__name__)

USER_AGENT = "UniResuConnect/2.1 (+https://uniresu.org; coleta semanal de projetos publicos)"


class ErroColeta(Exception):
    """Falha de rede/HTTP após esgotar as tentativas, ou página inesperada."""


class ErroDefinitivo(ErroColeta):
    """Resposta 4xx (menos 429): repetir não ajuda, então não há nova tentativa."""


def _retry_after(resp) -> float:
    """Segundos pedidos pelo cabeçalho Retry-After (só a forma numérica)."""
    valor = (getattr(resp, "headers", None) or {}).get("Retry-After") or ""
    try:
        return max(0.0, min(float(valor), 600.0))
    except ValueError:
        return 0.0


class ConfigHttp(Protocol):
    pausa_segundos: float
    timeout_segundos: float
    max_tentativas: int
    backoff_base_segundos: float


class ClienteHttp:
    """Sessão HTTP com throttle, timeout e retry com backoff."""

    #: Exceção levantada ao esgotar as tentativas (subclasses podem especializar).
    erro = ErroColeta
    #: Encoding usado quando o servidor não declara um (o SIGAA manda ISO-8859-1).
    encoding_padrao: Optional[str] = None
    nome = "HTTP"

    def __init__(
        self,
        cfg: ConfigHttp,
        session: Optional[requests.Session] = None,
        sleep: Callable[[float], None] = time.sleep,
        clock: Callable[[], float] = time.monotonic,
    ):
        self.cfg = cfg
        self.session = session or requests.Session()
        self.session.headers.setdefault("User-Agent", USER_AGENT)
        self._sleep = sleep
        self._clock = clock
        self._ultima: Optional[float] = None
        self._ultima_duracao = 0.0
        self.total_requisicoes = 0

    def _pausa_atual(self) -> float:
        """Pausa mínima antes da próxima requisição. Com `pausa_proporcional`
        (fator > 0 na config), a pausa cresce com o tempo que o servidor levou
        para responder a anterior: servidor lento recebe menos pedidos."""
        fator = float(getattr(self.cfg, "pausa_proporcional", 0) or 0)
        return max(self.cfg.pausa_segundos, fator * self._ultima_duracao)

    def _aguardar_vez(self) -> None:
        if self._ultima is not None:
            falta = self._pausa_atual() - (self._clock() - self._ultima)
            if falta > 0:
                self._sleep(falta)

    def request(self, method: str, url: str, **kwargs) -> str:
        return self.request_raw(method, url, **kwargs).text

    def request_raw(self, method: str, url: str, **kwargs):
        """Como `request`, mas devolve o objeto Response (status, histórico de
        redirecionamentos, cabeçalhos) — útil no modo captura/diagnóstico."""
        ultimo_erro: Optional[Exception] = None
        for tentativa in range(1, self.cfg.max_tentativas + 1):
            self._aguardar_vez()
            inicio = self._clock()
            retry_after = 0.0
            try:
                self.total_requisicoes += 1
                resp = self.session.request(method, url, timeout=self.cfg.timeout_segundos, **kwargs)
                self._ultima = self._clock()
                self._ultima_duracao = self._ultima - inicio
                if resp.status_code >= 500 or resp.status_code == 429:
                    retry_after = _retry_after(resp)
                    raise self.erro(f"HTTP {resp.status_code} em {url}")
                if resp.status_code >= 400:
                    raise ErroDefinitivo(f"HTTP {resp.status_code} em {url}")
                resp.raise_for_status()
                self._ajustar_encoding(resp)
                return resp
            except (requests.RequestException, ErroColeta) as e:
                self._ultima = self._clock()
                self._ultima_duracao = self._ultima - inicio
                if isinstance(e, ErroDefinitivo):
                    raise
                ultimo_erro = e
                if tentativa < self.cfg.max_tentativas:
                    # Respeita o Retry-After do servidor quando ele pede mais.
                    espera = max(self.cfg.backoff_base_segundos * (2 ** (tentativa - 1)), retry_after)
                    logger.warning("%s: tentativa %d falhou (%s); nova tentativa em %.0fs",
                                   self.nome, tentativa, e, espera)
                    self._sleep(espera)
        raise self.erro(f"Falha após {self.cfg.max_tentativas} tentativas: {ultimo_erro}")

    def _ajustar_encoding(self, resp) -> None:
        """Sem charset no Content-Type, o `requests` assume ISO-8859-1 para text/*
        e páginas UTF-8 viram mojibake. Preferimos o charset declarado no HTML
        (<meta charset>), depois o padrão da fonte, depois a detecção do requests."""
        cabecalhos = getattr(resp, "headers", None) or {}
        if "charset=" in (cabecalhos.get("content-type") or "").lower():
            return
        conteudo = getattr(resp, "content", None)
        declarado = EncodingDetector.find_declared_encoding(conteudo, is_html=True) if conteudo else None
        resp.encoding = declarado or self.encoding_padrao or getattr(resp, "apparent_encoding", None) or "utf-8"

    def get(self, url: str, **kwargs) -> str:
        return self.request("GET", url, **kwargs)

    def post(self, url: str, data: dict) -> str:
        return self.request("POST", url, data=data)
