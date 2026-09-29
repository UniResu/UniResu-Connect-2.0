"""
Configuração do sync com o SIGAA/UNIR, lida de variáveis de ambiente.

Todas as variáveis têm default seguro, então o job roda sem nenhuma
configuração extra além de MONGO_URI.
"""

import os
from dataclasses import dataclass, field
from datetime import datetime


def _lista(valor: str) -> list[str]:
    return [v.strip() for v in valor.split(",") if v.strip()]


@dataclass
class SigaaConfig:
    # Anos consultados. Default: ano corrente.
    anos: list[str] = field(default_factory=lambda: [str(datetime.now().year)])
    # Filtro de situação da consulta de pesquisa (vazio = sem filtro).
    pesquisa_situacao: str = "EM EXECUÇÃO"
    # Tipos de ação de extensão importados (o resto — eventos, cursos — é ignorado).
    extensao_tipos: list[str] = field(default_factory=lambda: ["PROJETO", "PROGRAMA"])
    # Módulos coletados.
    modulos: list[str] = field(default_factory=lambda: ["pesquisa", "extensao"])
    # Pausa mínima entre requisições (nunca menos que 1s).
    pausa_segundos: float = 1.5
    timeout_segundos: float = 60.0
    max_tentativas: int = 3
    backoff_base_segundos: float = 2.0

    @classmethod
    def from_env(cls) -> "SigaaConfig":
        cfg = cls()
        if os.getenv("SIGAA_ANOS"):
            cfg.anos = _lista(os.environ["SIGAA_ANOS"])
        if "SIGAA_PESQUISA_SITUACAO" in os.environ:
            cfg.pesquisa_situacao = os.environ["SIGAA_PESQUISA_SITUACAO"].strip()
        if os.getenv("SIGAA_EXTENSAO_TIPOS"):
            cfg.extensao_tipos = [t.upper() for t in _lista(os.environ["SIGAA_EXTENSAO_TIPOS"])]
        if os.getenv("SIGAA_MODULOS"):
            cfg.modulos = [m.lower() for m in _lista(os.environ["SIGAA_MODULOS"])]
        cfg.pausa_segundos = max(1.0, float(os.getenv("SIGAA_PAUSA_SEGUNDOS", cfg.pausa_segundos)))
        cfg.timeout_segundos = float(os.getenv("SIGAA_TIMEOUT_SEGUNDOS", cfg.timeout_segundos))
        cfg.max_tentativas = max(1, int(os.getenv("SIGAA_MAX_TENTATIVAS", cfg.max_tentativas)))
        return cfg
