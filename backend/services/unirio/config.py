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
from typing import Optional


def _lista(valor: str) -> list[str]:
    return [v.strip() for v in valor.split(",") if v.strip()]


def _env(nome: str, padrao):
    valor = os.getenv(nome)
    return valor.strip() if valor is not None and valor.strip() else padrao


# Portal da Pesquisa (web2py): o formulário de busca mora em default/index e,
# aceito, redireciona (303) para search/index com os resultados. Um POST direto
# em search/index volta para default/index com "Você precisa realizar uma busca".
URL_PESQUISA = "https://sistemas.unirio.br/projetos/search/index"
URL_PESQUISA_FORM = "https://sistemas.unirio.br/projetos/default/index"
URL_EXTENSAO = (
    "https://sistemas2.unirio.br/extensao/busca/projetos"
    "?cat_termos=titulo&f_ano=0&f_area=0&f_centro=0&f_cor=0&f_lin=0&f_status={status}&f_uni=0&termos="
)


DETALHES_MODOS = ("incremental", "completo")


@dataclass
class UnirioConfig:
    # Módulos coletados.
    modulos: list[str] = field(default_factory=lambda: ["pesquisa", "extensao"])
    # Filtro de status da busca de extensão (f_status). 1 = em andamento (o link
    # público usado como referência); 0 = todos.
    extensao_status: str = "1"
    # Anos de referência consultados no Portal da Pesquisa quando a busca sem
    # filtro não lista nada. Vazio = todos os anos oferecidos pelo formulário.
    pesquisa_anos: list[str] = field(default_factory=list)
    # Ignora projetos de pesquisa com ano de referência anterior a este
    # (0 = nenhum corte; a listagem traz tudo desde 1992, ~2.300 projetos).
    pesquisa_ano_minimo: int = 0
    # Teto de páginas percorridas por listagem (proteção contra loop de paginação).
    # Ao bater no teto a listagem é marcada incompleta e nada é desativado.
    max_paginas: int = 300
    # Teto de itens cujo detalhe é consultado por módulo (0 = sem limite).
    # Só vale em --dry-run/--captura: no sync real é ignorado.
    max_detalhes: int = 0
    # Quais páginas de detalhe abrir no sync real:
    #   incremental → só projetos novos e, na pesquisa, os ainda em execução
    #                 (para perceber quando encerram). Os já conhecidos e
    #                 encerrados ficam como estão. Execução semanal em minutos.
    #   completo    → todos (primeira carga, ou para reler tudo).
    # A listagem é sempre percorrida inteira: é ela que diz o que sumiu.
    detalhes: str = "incremental"
    # Pausa mínima entre requisições (nunca menos que 1s).
    pausa_segundos: float = 1.5
    timeout_segundos: float = 60.0
    # Os portais da UNIRIO derrubam conexões e devolvem 500 em rajadas curtas:
    # 5 tentativas com espera de 5, 10, 20 e 40 s (75 s no total) antes de
    # desistir de uma página.
    max_tentativas: int = 5
    backoff_base_segundos: float = 5.0

    @property
    def url_pesquisa(self) -> str:
        return _env("UNIRIO_URL_PESQUISA", URL_PESQUISA)

    @property
    def url_pesquisa_formulario(self) -> str:
        return _env("UNIRIO_URL_PESQUISA_FORM", URL_PESQUISA_FORM)

    @property
    def url_extensao(self) -> str:
        return _env("UNIRIO_URL_EXTENSAO", URL_EXTENSAO.format(status=self.extensao_status))

    @property
    def pesquisa_detalhe_prefixo(self) -> Optional[str]:
        """Prefixo de caminho dos links de detalhe do Portal da Pesquisa
        (ex.: "/projetos/search/"), para que links de outros controllers
        (perfil de pessoa, unidade) não sejam tomados por projetos. Vazio
        (padrão) = sem restrição; defina UNIRIO_PESQUISA_DETALHE_PREFIXO
        depois de conferir a listagem real."""
        return _env("UNIRIO_PESQUISA_DETALHE_PREFIXO", None)

    @classmethod
    def from_env(cls) -> "UnirioConfig":
        cfg = cls()
        cfg.modulos = [m.lower() for m in _lista(_env("UNIRIO_MODULOS", ",".join(cfg.modulos)))] or cfg.modulos
        cfg.extensao_status = str(_env("UNIRIO_EXTENSAO_STATUS", cfg.extensao_status))
        cfg.pesquisa_anos = _lista(_env("UNIRIO_PESQUISA_ANOS", ""))
        cfg.pesquisa_ano_minimo = max(0, int(_env("UNIRIO_PESQUISA_ANO_MINIMO", cfg.pesquisa_ano_minimo)))
        cfg.max_paginas = max(1, int(_env("UNIRIO_MAX_PAGINAS", cfg.max_paginas)))
        cfg.max_detalhes = max(0, int(_env("UNIRIO_MAX_DETALHES", cfg.max_detalhes)))
        detalhes = str(_env("UNIRIO_DETALHES", cfg.detalhes)).strip().lower()
        if detalhes not in DETALHES_MODOS:
            raise ValueError(f"UNIRIO_DETALHES inválido: {detalhes!r} (use {' ou '.join(DETALHES_MODOS)})")
        cfg.detalhes = detalhes
        cfg.pausa_segundos = max(1.0, float(_env("UNIRIO_PAUSA_SEGUNDOS", cfg.pausa_segundos)))
        cfg.timeout_segundos = float(_env("UNIRIO_TIMEOUT_SEGUNDOS", cfg.timeout_segundos))
        cfg.max_tentativas = max(1, int(_env("UNIRIO_MAX_TENTATIVAS", cfg.max_tentativas)))
        return cfg
