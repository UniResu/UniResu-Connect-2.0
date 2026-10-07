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
    # Chave natural dos projetos da UNIRIO (mesma ideia, campo e origem próprios).
    await db.projetos.create_index(
        [("chave_unirio", ASCENDING)],
        name="uniq_chave_unirio",
        unique=True,
        partialFilterExpression={"origem": "unirio"},
    )
    await db.projetos.create_index(
        [("origem", ASCENDING), ("modulo", ASCENDING), ("unirio_id", ASCENDING)],
        name="unirio_id_por_modulo",
    )
    await db.projetos.create_index(
        [("ativo", ASCENDING), ("instituicao", ASCENDING), ("modulo", ASCENDING), ("unidade", ASCENDING)],
        name="listagem_filtros_v2",
    )
    await db.sigaa_sync_runs.create_index([("iniciada_em", DESCENDING)], name="runs_recentes")
    await db.sigaa_sync_runs.create_index([("fonte", ASCENDING), ("finalizada_em", DESCENDING)], name="runs_por_fonte")
    # Rate limit e checagem de duplicidade das candidaturas.
    await db.candidaturas.create_index(
        [("usuario_id", ASCENDING), ("data_candidatura", DESCENDING)],
        name="candidaturas_por_usuario",
    )
    # Username público (fórum/perfil). Sparse: contas antigas ainda sem o campo
    # não colidem entre si; o backfill de `migrar_dados` as preenche.
    await db.usuarios.create_index(
        [("username", ASCENDING)],
        name="uniq_username",
        unique=True,
        sparse=True,
    )
    logger.info("Índices do MongoDB verificados/criados.")


async def migrar_dados(db) -> None:
    """Migrações leves de dados, independentes dos índices (uma falha em
    create_index não pode impedir que rodem). Idempotentes."""
    from services.sigaa.repositorio import garantir_modulo
    from services.usernames import preencher_usernames
    from jobs.seed_forum import seed_forum

    migrados = await garantir_modulo(db)
    if migrados:
        logger.info("Campo `modulo` preenchido em %d projetos do SIGAA.", migrados)

    # Cada passo abaixo é independente: a falha de um não impede o seguinte.
    try:
        # Precisa rodar ANTES de `criar_indices` (ordem do lifespan em main.py):
        # o índice único em `username` só é criado com todo mundo preenchido.
        preenchidos = await preencher_usernames(db)
        if preenchidos:
            logger.info("Username gerado para %d usuário(s) sem o campo.", preenchidos)
    except Exception as e:
        logger.error("Falha no backfill de usernames: %s", e)

    try:
        inseridos = await seed_forum(db)
        if inseridos:
            logger.info("Seed do fórum: %d pergunta(s) inserida(s).", inseridos)
    except Exception as e:
        logger.error("Falha no seed do fórum: %s", e)
