"""
Persistência dos projetos coletados (SIGAA/UNIR, portais da UNIRIO) na
collection `projetos`.

Regra de ouro: TODA operação de escrita filtra por `origem` da fonte.
Projetos cadastrados manualmente pelos professores (sem `origem` ou com
outro valor) nunca são tocados — nem sobrescritos, nem desativados — e uma
fonte nunca encosta nos documentos de outra.

Chave natural: módulo + ano + título + coordenador (normalizados), gravada
no campo exclusivo da fonte (`chave_sigaa`, `chave_unirio`).
Campos editados por um administrador (`email_contato_manual`) nunca são
sobrescritos pelo sync.
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Iterable, Optional

from services.areas import classificar_area
from services.fontes import MODULO_LABEL, MODULOS, SIGAA, Fonte
from services.sigaa.parser import normalizar

# Compatibilidade com o código antigo, que só conhecia o SIGAA.
ORIGEM = SIGAA.origem
TIPO_LABEL = MODULO_LABEL


def chave_natural(registro: dict) -> str:
    partes = (
        registro.get("modulo"),
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


def _id_fonte(registro: dict, fonte: Fonte) -> Optional[str]:
    return registro.get(fonte.campo_id) or registro.get("id_fonte")


async def _registro_anterior_sem_coordenador(db, registro: dict, fonte: Fonte) -> Optional[dict]:
    """Se o detalhe falhou (sem coordenador), reaproveita o doc já existente
    com o mesmo id na fonte — evita criar duplicata com chave incompleta."""
    id_fonte = _id_fonte(registro, fonte)
    if registro.get("coordenador") or not id_fonte:
        return None
    return await db.projetos.find_one({
        "origem": fonte.origem,
        "modulo": registro["modulo"],
        fonte.campo_id: id_fonte,
    })


async def _confirmar_presenca(db, registro: dict, fonte: Fonte, agora: datetime) -> Optional[str]:
    """Item já conhecido cujo detalhe não foi reaberto: marca ativo e visto
    agora, pelo id na fonte. Devolve a chave do doc (ou None se não existe)."""
    id_fonte = _id_fonte(registro, fonte)
    if not id_fonte:
        return None
    doc = await db.projetos.find_one(
        {"origem": fonte.origem, "modulo": registro["modulo"], fonte.campo_id: id_fonte},
        {fonte.campo_chave: 1},
    )
    if not doc or not doc.get(fonte.campo_chave):
        return None
    campos = {"ativo": True, "ultima_coleta": agora}
    if registro.get("link_detalhe"):
        campos["link_detalhe"] = registro["link_detalhe"]
    await db.projetos.update_one({"_id": doc["_id"]}, {"$set": campos})
    return doc[fonte.campo_chave]


async def _promover_chave_incompleta(db, registro: dict, chave: str, fonte: Fonte) -> None:
    """Item salvo antes sem coordenador (detalhe falhou) e que agora veio
    completo: atualiza a chave do doc existente em vez de criar outro, para
    preservar o _id (candidaturas apontam para ele)."""
    id_fonte = _id_fonte(registro, fonte)
    if not id_fonte or not registro.get("coordenador"):
        return
    if await db.projetos.find_one({"origem": fonte.origem, fonte.campo_chave: chave}, {"_id": 1}):
        return
    await db.projetos.update_one(
        {
            "origem": fonte.origem,
            "modulo": registro["modulo"],
            fonte.campo_id: id_fonte,
            "nome_professor": None,
        },
        {"$set": {fonte.campo_chave: chave}},
    )


def _campos_completos(reg: dict, fonte: Fonte, agora: datetime) -> dict:
    modulo = reg["modulo"]
    campos = {
        "modulo": modulo,
        "tipo": MODULO_LABEL.get(modulo, modulo),
        fonte.campo_id: _id_fonte(reg, fonte),
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
        "instituicao": fonte.instituicao,
        "ativo": True,
        "ultima_coleta": agora,
        "detalhe_ok": reg.get("detalhe_ok", False),
    }
    if fonte is SIGAA:
        # Nome histórico do módulo nos docs do SIGAA (índices e dados antigos).
        campos["tipo_sigaa"] = modulo
    # Campos extras que a fonte queira guardar (ex.: área temática, palavras-chave).
    campos.update(reg.get("extras") or {})
    # Grande área do CNPq, derivada do que a fonte publica (área CNPq da UFV,
    # unidade, título, descrição...). Vale para todas as fontes.
    campos["area_conhecimento"] = classificar_area(campos)
    return campos


async def upsert_projetos(
    db, registros: Iterable[dict], agora: Optional[datetime] = None, fonte: Fonte = SIGAA
) -> ResultadoUpsert:
    agora = agora or datetime.now(timezone.utc)
    res = ResultadoUpsert()

    for reg in registros:
        if reg.get("so_listagem"):
            # Modo incremental: o detalhe não foi reaberto de propósito. Só
            # confirmamos que o projeto continua na fonte, sem tocar no que o
            # detalhe anterior gravou (coordenador, e-mail, situação, resumo).
            chave = await _confirmar_presenca(db, reg, fonte, agora)
            if chave is not None:
                res.atualizados += 1
                res.chaves.append(chave)
                continue
            # Não estava mais no banco: segue como item só de listagem.
        anterior = await _registro_anterior_sem_coordenador(db, reg, fonte)
        if anterior is not None:
            # Detalhe indisponível nesta run: mantém coordenador/contato já
            # conhecidos e só atualiza o que veio da listagem.
            chave = anterior[fonte.campo_chave]
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
            await _promover_chave_incompleta(db, reg, chave, fonte)
            campos = _campos_completos(reg, fonte, agora)

        resultado = await db.projetos.update_one(
            {"origem": fonte.origem, fonte.campo_chave: chave},
            {
                "$set": campos,
                "$setOnInsert": {"origem": fonte.origem, fonte.campo_chave: chave, "primeira_coleta": agora},
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
    db,
    modulo: str,
    anos: list[str],
    chaves_vistas: list[str],
    agora: Optional[datetime] = None,
    fonte: Fonte = SIGAA,
    ano_minimo: Optional[int] = None,
) -> int:
    """Marca como inativos os projetos da fonte, no escopo coletado, que sumiram dela.

    Só deve ser chamado quando a coleta daquele módulo teve sucesso (> 0 itens).
    `anos` vazio significa "sem recorte por ano" (fontes que listam tudo de uma vez).
    `ano_minimo` restringe o escopo a projetos com ano >= ele (coleta da UNIRIO
    com UNIRIO_PESQUISA_ANO_MINIMO): os mais antigos não foram lidos, então
    não podem ser dados como ausentes.
    """
    agora = agora or datetime.now(timezone.utc)
    filtro = {
        "origem": fonte.origem,
        "modulo": modulo,
        "ativo": True,
        fonte.campo_chave: {"$nin": chaves_vistas},
    }
    if anos:
        filtro["ano"] = {"$in": anos}
    elif ano_minimo:
        # `ano` é gravado como texto de 4 dígitos: a comparação lexicográfica
        # equivale à numérica, e docs sem ano (null) ficam fora do escopo.
        filtro["ano"] = {"$gte": str(ano_minimo)}
    resultado = await db.projetos.update_many(filtro, {"$set": {"ativo": False, "desativado_em": agora}})
    return resultado.modified_count


async def garantir_modulo(db) -> int:
    """Migração leve: docs do SIGAA gravados antes do campo `modulo` ganham o
    valor de `tipo_sigaa`. Idempotente, uma única operação no servidor
    (update com pipeline, MongoDB >= 4.2); roda no startup da API e no início
    dos jobs. Devolve quantos docs foram migrados."""
    resultado = await db.projetos.update_many(
        {"origem": SIGAA.origem, "modulo": {"$exists": False}, "tipo_sigaa": {"$in": list(MODULOS)}},
        [{"$set": {"modulo": "$tipo_sigaa"}}],
    )
    return resultado.modified_count
