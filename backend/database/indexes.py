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
    # Chave natural dos projetos da UFV (dados abertos).
    await db.projetos.create_index(
        [("chave_ufv", ASCENDING)],
        name="uniq_chave_ufv",
        unique=True,
        partialFilterExpression={"origem": "ufv"},
    )
    # Chave natural dos projetos da PUC-Campinas (página pública de extensão).
    await db.projetos.create_index(
        [("chave_puccamp", ASCENDING)],
        name="uniq_chave_puccamp",
        unique=True,
        partialFilterExpression={"origem": "puccamp"},
    )
    await db.projetos.create_index(
        [("ativo", ASCENDING), ("instituicao", ASCENDING), ("modulo", ASCENDING), ("unidade", ASCENDING)],
        name="listagem_filtros_v2",
    )
    # Filtro e contagem por grande área do CNPq (busca e /projetos/filtros).
    await db.projetos.create_index([("area_conhecimento", ASCENDING)], name="area_conhecimento")
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
    # Respostas do fórum: listagem por tópico em ordem cronológica e contagem.
    # O `_id` no fim é o desempate da ordenação (paginação estável); o índice
    # também atende consultas só por (topico_id, data_criacao).
    await db.respostas_forum.create_index(
        [("topico_id", ASCENDING), ("data_criacao", ASCENDING), ("_id", ASCENDING)],
        name="respostas_por_topico",
    )
    # Primeira pergunta de cada autor (selo "Primeiro contato" no fórum).
    await db.topicos_forum.create_index(
        [("autor_id", ASCENDING), ("data_criacao", ASCENDING), ("_id", ASCENDING)],
        name="topicos_por_autor",
    )
    logger.info("Índices do MongoDB verificados/criados.")


async def migrar_forum_legado(db) -> dict:
    """Tópicos antigos do fórum: `autor_email` vira `autor_id` (quando o e-mail
    corresponde a uma conta) e sai do documento; `likes`/`dislikes` inteiros
    viram listas. Idempotente. Devolve contagens."""
    contagem = {"autores": 0, "emails_removidos": 0, "votos": 0}

    cursor = db.topicos_forum.find({"autor_email": {"$exists": True}}, {"autor_email": 1, "autor_id": 1})
    for doc in await cursor.to_list(length=None):
        campos = {}
        if not doc.get("autor_id") and doc.get("autor_email"):
            usuario = await db.usuarios.find_one({"email": doc["autor_email"]}, {"_id": 1})
            if usuario:
                campos["autor_id"] = str(usuario["_id"])
                contagem["autores"] += 1
        update = {"$unset": {"autor_email": ""}}
        if campos:
            update["$set"] = campos
        await db.topicos_forum.update_one({"_id": doc["_id"]}, update)
        contagem["emails_removidos"] += 1

    cursor = db.topicos_forum.find({}, {"likes": 1, "dislikes": 1})
    for doc in await cursor.to_list(length=None):
        listas = {c: [] for c in ("likes", "dislikes") if not isinstance(doc.get(c), list)}
        if listas:
            await db.topicos_forum.update_one({"_id": doc["_id"]}, {"$set": listas})
            contagem["votos"] += 1
    return contagem


async def migrar_niveis_academicos(db) -> int:
    """Contas de discente com os níveis da primeira versão (graduacao,
    mestrado, doutorado) passam para os valores atuais (em andamento).
    Idempotente. Devolve quantos documentos mudaram."""
    from models.usuario_model import NIVEIS_ANTIGOS

    total = 0
    for antigo, novo in NIVEIS_ANTIGOS.items():
        resultado = await db.usuarios.update_many({"dados_aluno.nivel": antigo},
                                                   {"$set": {"dados_aluno.nivel": novo.value}})
        total += resultado.modified_count
    return total


async def migrar_dados(db) -> None:
    """Migrações leves de dados, independentes dos índices (uma falha em
    create_index não pode impedir que rodem). Idempotentes."""
    from services.areas import garantir_area_conhecimento
    from services.campi import garantir_campus
    from services.sigaa.repositorio import garantir_modulo
    from services.usernames import preencher_usernames
    from jobs.seed_forum import seed_forum

    migrados = await garantir_modulo(db)
    if migrados:
        logger.info("Campo `modulo` preenchido em %d projetos do SIGAA.", migrados)

    # Cada passo abaixo é independente: a falha de um não impede o seguinte.
    try:
        classificados = await garantir_area_conhecimento(db)
        if classificados:
            logger.info("Campo `area_conhecimento` preenchido em %d projeto(s).", classificados)
    except Exception as e:
        logger.error("Falha ao preencher a área do conhecimento dos projetos: %s", e)

    try:
        # O índice único vem ANTES do backfill: é ele, e não a leitura em
        # memória, que garante a unicidade se dois processos preencherem ao
        # mesmo tempo (o backfill trata a colisão tentando o sufixo seguinte).
        # Sparse: quem ainda não tem o campo não colide.
        await db.usuarios.create_index([("username", ASCENDING)], name="uniq_username", unique=True, sparse=True)
    except Exception as e:
        logger.error("Falha ao criar o índice uniq_username (usernames repetidos no banco?): %s", e)

    try:
        preenchidos = await preencher_usernames(db)
        if preenchidos:
            logger.info("Username gerado para %d usuário(s) sem o campo.", preenchidos)
    except Exception as e:
        logger.error("Falha no backfill de usernames: %s", e)

    try:
        campi = await garantir_campus(db)
        if campi:
            logger.info("Campo `campus` preenchido em %d projetos.", campi)
    except Exception as e:
        logger.error("Falha ao preencher o campus dos projetos: %s", e)

    try:
        niveis = await migrar_niveis_academicos(db)
        if niveis:
            logger.info("Grau de instrução atualizado em %d conta(s) de discente.", niveis)
    except Exception as e:
        logger.error("Falha na migração dos graus de instrução: %s", e)

    try:
        contagem = await migrar_forum_legado(db)
        if any(contagem.values()):
            logger.info("Fórum legado migrado: %s", contagem)
    except Exception as e:
        logger.error("Falha na migração dos tópicos legados do fórum: %s", e)

    try:
        inseridos = await seed_forum(db)
        if inseridos:
            logger.info("Seed do fórum: %d pergunta(s) inserida(s).", inseridos)
    except Exception as e:
        logger.error("Falha no seed do fórum: %s", e)
