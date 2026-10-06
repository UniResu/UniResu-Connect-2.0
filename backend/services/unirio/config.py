"""
Configuração do sync com os portais públicos da UNIRIO, lida de variáveis
de ambiente. Todas têm default seguro: o job roda só com MONGO_URI.

Fontes:
- Portal da Pesquisa (SISPP): https://sistemas.unirio.br/projetos/search/index
- Portal da Extensão (ProExC): https://sistemas2.unirio.br/extensao/busca/projetos

Uma variável vazia conta como ausente: o workflow exporta
`${{ inputs.x || vars.X }}`, que vira "" quando nada está definido.
"""

import os
from dataclasses import dataclass, field
from urllib.parse import urlparse


def _lista(valor: str) -> list[str]:
    return [v.strip() for v in valor.split(",") if v.strip()]


def _env(nome: str, padrao):
    valor = os.getenv(nome)
    return valor.strip() if valor is not None and valor.strip() else padrao


URL_PESQUISA = "https://sistemas.unirio.br/projetos/search/index"
URL_EXTENSAO = (
    "https://sistemas2.unirio.br/extensao/busca/projetos"
    "?cat_termos=titulo&f_ano=0&f_area=0&f_centro=0&f_cor=0&f_lin=0&f_status={status}&f_uni=0&termos="
)


@dataclass
class UnirioConfig:
    # Módulos coletados.
    modulos: list[str] = field(default_factory=lambda: ["pesquisa", "extensao"])
    # Filtro de status da busca de extensão (f_status). 1 = em andamento (o link
    # público usado como referência); 0 = todos.
    extensao_status: str = "1"
    # Teto de páginas percorridas por listagem (proteção contra loop de paginação).
    # Ao bater no teto a listagem é marcada incompleta e nada é desativado.
    max_paginas: int = 300
    # Teto de itens cujo detalhe é consultado por módulo (0 = sem limite).
    # Só vale em --dry-run/--captura: no sync real é ignorado.
    max_detalhes: int = 0
    # Pausa mínima entre requisições (nunca menos que 1s).
    pausa_segundos: float = 1.5
    timeout_segundos: float = 60.0
    max_tentativas: int = 3
    backoff_base_segundos: float = 2.0

    @property
    def url_pesquisa(self) -> str:
        return _env("UNIRIO_URL_PESQUISA", URL_PESQUISA)

    @property
    def url_extensao(self) -> str:
        return _env("UNIRIO_URL_EXTENSAO", URL_EXTENSAO.format(status=self.extensao_status))

    @property
    def pesquisa_detalhe_prefixo(self) -> str:
        """Prefixo de caminho dos links de detalhe do Portal da Pesquisa.

        Padrão: o diretório do controller da listagem ("/projetos/search/"),
        para que links de outros controllers (perfil de pessoa, unidade) não
        sejam tomados por projetos. Ajustável por UNIRIO_PESQUISA_DETALHE_PREFIXO
        caso o detalhe more em outro controller (ex.: "/projetos/projeto/").
        """
        caminho = urlparse(self.url_pesquisa).path or "/"
        return _env("UNIRIO_PESQUISA_DETALHE_PREFIXO", caminho.rsplit("/", 1)[0] + "/")

    @classmethod
    def from_env(cls) -> "UnirioConfig":
        cfg = cls()
        cfg.modulos = [m.lower() for m in _lista(_env("UNIRIO_MODULOS", ",".join(cfg.modulos)))] or cfg.modulos
        cfg.extensao_status = str(_env("UNIRIO_EXTENSAO_STATUS", cfg.extensao_status))
        cfg.max_paginas = max(1, int(_env("UNIRIO_MAX_PAGINAS", cfg.max_paginas)))
        cfg.max_detalhes = max(0, int(_env("UNIRIO_MAX_DETALHES", cfg.max_detalhes)))
        cfg.pausa_segundos = max(1.0, float(_env("UNIRIO_PAUSA_SEGUNDOS", cfg.pausa_segundos)))
        cfg.timeout_segundos = float(_env("UNIRIO_TIMEOUT_SEGUNDOS", cfg.timeout_segundos))
        cfg.max_tentativas = max(1, int(_env("UNIRIO_MAX_TENTATIVAS", cfg.max_tentativas)))
        return cfg
