"""
Configuração do sync com o SIGAA (UNIR por padrão; qualquer instituição de
`services.sigaa.instituicoes` via SIGAA_INSTITUICAO), lida de variáveis de ambiente.

Todas as variáveis têm default seguro, então o job roda sem nenhuma
configuração extra além de MONGO_URI.
"""

import os
from dataclasses import dataclass, field
from datetime import datetime

from services.sigaa.instituicoes import instituicao_sigaa


def _lista(valor: str) -> list[str]:
    return [v.strip() for v in valor.split(",") if v.strip()]


@dataclass
class SigaaConfig:
    # Instituição coletada (sigla) e endereço base do seu SIGAA.
    instituicao: str = "UNIR"
    base_url: str = "https://sigaa.unir.br"
    # Anos consultados. Default: ano corrente.
    anos: list[str] = field(default_factory=lambda: [str(datetime.now().year)])
    # Filtro de situação da consulta de pesquisa (vazio = sem filtro).
    pesquisa_situacao: str = "EM EXECUÇÃO"
    # Tipos de ação de extensão importados (o resto — eventos, cursos — é ignorado).
    extensao_tipos: list[str] = field(default_factory=lambda: ["PROJETO", "PROGRAMA"])
    # Módulos coletados.
    modulos: list[str] = field(default_factory=lambda: ["pesquisa", "extensao"])
    # Teto de itens por módulo cujo detalhe é aberto (0 = todos; útil no dry-run).
    max_itens: int = 0
    # Pausa mínima entre requisições (nunca menos que 1s).
    pausa_segundos: float = 1.5
    timeout_segundos: float = 60.0
    max_tentativas: int = 3
    backoff_base_segundos: float = 2.0

    @classmethod
    def para(cls, sigla: str, **kwargs) -> "SigaaConfig":
        """Configuração apontando para o SIGAA de uma instituição conhecida."""
        inst = instituicao_sigaa(sigla)
        kwargs.setdefault("modulos", list(inst.modulos))
        return cls(instituicao=inst.sigla, base_url=inst.base_url, **kwargs)

    @classmethod
    def from_env(cls) -> "SigaaConfig":
        cfg = cls.para(os.getenv("SIGAA_INSTITUICAO") or "UNIR")
        if os.getenv("SIGAA_BASE_URL"):
            cfg.base_url = os.environ["SIGAA_BASE_URL"].strip().rstrip("/")
        if os.getenv("SIGAA_ANOS"):
            cfg.anos = _lista(os.environ["SIGAA_ANOS"])
        if "SIGAA_PESQUISA_SITUACAO" in os.environ:
            cfg.pesquisa_situacao = os.environ["SIGAA_PESQUISA_SITUACAO"].strip()
        if os.getenv("SIGAA_EXTENSAO_TIPOS"):
            cfg.extensao_tipos = [t.upper() for t in _lista(os.environ["SIGAA_EXTENSAO_TIPOS"])]
        if os.getenv("SIGAA_MODULOS"):
            cfg.modulos = [m.lower() for m in _lista(os.environ["SIGAA_MODULOS"])]
        cfg.max_itens = max(0, int(os.getenv("SIGAA_MAX_ITENS") or 0))
        cfg.pausa_segundos = max(1.0, float(os.getenv("SIGAA_PAUSA_SEGUNDOS", cfg.pausa_segundos)))
        cfg.timeout_segundos = float(os.getenv("SIGAA_TIMEOUT_SEGUNDOS", cfg.timeout_segundos))
        cfg.max_tentativas = max(1, int(os.getenv("SIGAA_MAX_TENTATIVAS", cfg.max_tentativas)))
        return cfg
