"""
Cliente HTTP compartilhado pelas coletas (SIGAA/UNIR e portais da UNIRIO).

Boas maneiras com os servidores públicos: pausa mínima entre QUALQUER
requisição (nunca < 1s), timeout e retry com backoff exponencial.
"""

import logging
import time
from typing import Callable, Optional, Protocol

import requests

logger = logging.getLogger(__name__)

USER_AGENT = "UniResuConnect/2.1 (+https://uniresu.org; coleta semanal de projetos publicos)"


class ErroColeta(Exception):
    """Falha de rede/HTTP após esgotar as tentativas, ou página inesperada."""


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
        self.total_requisicoes = 0

    def _aguardar_vez(self) -> None:
        if self._ultima is not None:
            falta = self.cfg.pausa_segundos - (self._clock() - self._ultima)
            if falta > 0:
                self._sleep(falta)

    def request(self, method: str, url: str, **kwargs) -> str:
        ultimo_erro: Optional[Exception] = None
        for tentativa in range(1, self.cfg.max_tentativas + 1):
            self._aguardar_vez()
            try:
                self.total_requisicoes += 1
                resp = self.session.request(method, url, timeout=self.cfg.timeout_segundos, **kwargs)
                self._ultima = self._clock()
                if resp.status_code >= 500 or resp.status_code == 429:
                    raise self.erro(f"HTTP {resp.status_code} em {url}")
                resp.raise_for_status()
                if self.encoding_padrao:
                    resp.encoding = resp.encoding or self.encoding_padrao
                return resp.text
            except (requests.RequestException, ErroColeta) as e:
                self._ultima = self._clock()
                ultimo_erro = e
                if tentativa < self.cfg.max_tentativas:
                    espera = self.cfg.backoff_base_segundos * (2 ** (tentativa - 1))
                    logger.warning("%s: tentativa %d falhou (%s); nova tentativa em %.0fs",
                                   self.nome, tentativa, e, espera)
                    self._sleep(espera)
        raise self.erro(f"Falha após {self.cfg.max_tentativas} tentativas: {ultimo_erro}")

    def get(self, url: str, **kwargs) -> str:
        return self.request("GET", url, **kwargs)

    def post(self, url: str, data: dict) -> str:
        return self.request("POST", url, data=data)
