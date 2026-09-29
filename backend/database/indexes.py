"""
Índices do MongoDB (equivalente às "migrações" deste projeto).

`criar_indices` é idempotente: o MongoDB ignora índices que já existem com a
mesma especificação. Roda no startup da API.
"""

import logging

from pymongo import ASCENDING, DESCENDING

logger = logging.getLogger(__name__)


async def criar_indices(db) -> None:
    # Chave natural dos projetos do SIGAA — única só entre docs origem=sigaa,
    # para não afetar os projetos cadastrados manualmente.
    await db.projetos.create_index(
        [("chave_sigaa", ASCENDING)],
        name="uniq_chave_sigaa",
        unique=True,
        partialFilterExpression={"origem": "sigaa"},
    )
    await db.projetos.create_index(
        [("origem", ASCENDING), ("tipo_sigaa", ASCENDING), ("sigaa_id", ASCENDING)],
        name="sigaa_id_por_tipo",
    )
    await db.projetos.create_index(
        [("ativo", ASCENDING), ("tipo_sigaa", ASCENDING), ("unidade", ASCENDING)],
        name="listagem_filtros",
    )
    await db.sigaa_sync_runs.create_index([("iniciada_em", DESCENDING)], name="runs_recentes")
    # Rate limit e checagem de duplicidade das candidaturas.
    await db.candidaturas.create_index(
        [("usuario_id", ASCENDING), ("data_candidatura", DESCENDING)],
        name="candidaturas_por_usuario",
    )
    logger.info("Índices do MongoDB verificados/criados.")
