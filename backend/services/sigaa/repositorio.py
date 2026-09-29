"""
Persistência dos projetos do SIGAA na collection `projetos`.

Regra de ouro: TODA operação de escrita filtra por `origem: "sigaa"`.
Projetos cadastrados manualmente pelos professores (sem `origem` ou com
outro valor) nunca são tocados — nem sobrescritos, nem desativados.

Chave natural: tipo + ano + título + coordenador (normalizados).
Campos editados por um administrador (`email_contato_manual`) nunca são
sobrescritos pelo sync.
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Iterable, Optional

from services.sigaa.parser import normalizar

ORIGEM = "sigaa"
TIPO_LABEL = {"pesquisa": "Pesquisa", "extensao": "Extensão"}


def chave_natural(registro: dict) -> str:
    partes = (
        registro.get("tipo_sigaa"),
        registro.get("ano"),
        registro.get("titulo"),
        registro.get("coordenador"),
    )
    return "|".join(normalizar(p) for p in partes)


@dataclass
class ResultadoUpsert:
    novos: int = 0
    atualizados: int = 0
    desativados: int = 0
    chaves: list[str] = field(default_factory=list)


async def _registro_anterior_sem_coordenador(db, registro: dict) -> Optional[dict]:
    """Se o detalhe falhou (sem coordenador), reaproveita o doc já existente
    com o mesmo id do SIGAA — evita criar duplicata com chave incompleta."""
    if registro.get("coordenador") or not registro.get("sigaa_id"):
        return None
    return await db.projetos.find_one({
        "origem": ORIGEM,
        "tipo_sigaa": registro["tipo_sigaa"],
        "sigaa_id": registro["sigaa_id"],
    })


async def _promover_chave_incompleta(db, registro: dict, chave: str) -> None:
    """Item salvo antes sem coordenador (detalhe falhou) e que agora veio
    completo: atualiza a chave do doc existente em vez de criar outro, para
    preservar o _id (candidaturas apontam para ele)."""
    if not registro.get("sigaa_id") or not registro.get("coordenador"):
        return
    if await db.projetos.find_one({"origem": ORIGEM, "chave_sigaa": chave}, {"_id": 1}):
        return
    await db.projetos.update_one(
        {
            "origem": ORIGEM,
            "tipo_sigaa": registro["tipo_sigaa"],
            "sigaa_id": registro["sigaa_id"],
            "nome_professor": None,
        },
        {"$set": {"chave_sigaa": chave}},
    )


async def upsert_projetos(db, registros: Iterable[dict], agora: Optional[datetime] = None) -> ResultadoUpsert:
    agora = agora or datetime.now(timezone.utc)
    res = ResultadoUpsert()

    for reg in registros:
        anterior = await _registro_anterior_sem_coordenador(db, reg)
        if anterior is not None:
            # Detalhe indisponível nesta run: mantém coordenador/contato já
            # conhecidos e só atualiza o que veio da listagem.
            chave = anterior["chave_sigaa"]
            campos = {
                "titulo": reg["titulo"],
                "categoria": reg.get("categoria"),
                "link_detalhe": reg.get("link_detalhe") or anterior.get("link_detalhe"),
                "ativo": True,
                "ultima_coleta": agora,
                "detalhe_ok": False,
            }
        else:
            chave = chave_natural(reg)
            await _promover_chave_incompleta(db, reg, chave)
            campos = {
                "tipo_sigaa": reg["tipo_sigaa"],
                "tipo": TIPO_LABEL.get(reg["tipo_sigaa"], reg["tipo_sigaa"]),
                "sigaa_id": reg.get("sigaa_id"),
                "codigo": reg.get("codigo"),
                "titulo": reg["titulo"],
                "descricao": reg.get("descricao"),
                "nome_professor": reg.get("coordenador"),
                "email_professor": reg.get("email"),
                "unidade": reg.get("unidade"),
                "situacao": reg.get("situacao"),
                "ano": reg.get("ano"),
                "categoria": reg.get("categoria"),
                "link_detalhe": reg.get("link_detalhe"),
                "periodo_inicio": reg.get("periodo_inicio"),
                "periodo_fim": reg.get("periodo_fim"),
                "instituicao": "UNIR",
                "ativo": True,
                "ultima_coleta": agora,
                "detalhe_ok": reg.get("detalhe_ok", False),
            }

        resultado = await db.projetos.update_one(
            {"origem": ORIGEM, "chave_sigaa": chave},
            {
                "$set": campos,
                "$setOnInsert": {"origem": ORIGEM, "chave_sigaa": chave, "primeira_coleta": agora},
            },
            upsert=True,
        )
        if resultado.upserted_id is not None:
            res.novos += 1
        else:
            res.atualizados += 1
        res.chaves.append(chave)
    return res


async def desativar_ausentes(
    db, tipo_sigaa: str, anos: list[str], chaves_vistas: list[str], agora: Optional[datetime] = None
) -> int:
    """Marca como inativos os projetos SIGAA do escopo coletado que sumiram da fonte.

    Só deve ser chamado quando a coleta daquele tipo teve sucesso (> 0 itens).
    """
    agora = agora or datetime.now(timezone.utc)
    resultado = await db.projetos.update_many(
        {
            "origem": ORIGEM,
            "tipo_sigaa": tipo_sigaa,
            "ano": {"$in": anos},
            "ativo": True,
            "chave_sigaa": {"$nin": chaves_vistas},
        },
        {"$set": {"ativo": False, "desativado_em": agora}},
    )
    return resultado.modified_count
