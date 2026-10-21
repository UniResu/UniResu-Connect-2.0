"""
Recalcula a coordenação das ações de extensão do SIGAA já gravadas, com a
regra de `parser.escolher_coordenacao` (a FUNÇÃO na equipe decide: vice,
sub e coordenação adjunta não contam como coordenação). Usa a equipe e o
responsável pela ação guardados no banco, sem acessar os portais.

Sem --confirmar, só lista o que mudaria.

Uso (a partir de backend/) ou pelo workflow "Manutenção do banco"
(tarefa `recalcular-coordenacao`):
    python -m jobs.recalcular_coordenacao
    python -m jobs.recalcular_coordenacao --confirmar
"""

import asyncio
import sys
from collections import Counter

from dotenv import load_dotenv

from services.sigaa.parser import escolher_coordenacao, normalizar

FILTRO = {"origem": "sigaa", "modulo": "extensao", "equipe": {"$exists": True, "$ne": []}}
CAMPOS = {"titulo": 1, "instituicao": 1, "equipe": 1, "responsavel_acao": 1, "nome_professor": 1,
          "email_professor": 1}


def nova_coordenacao(doc: dict) -> tuple[str, str]:
    """(nome, e-mail) pela regra nova. O e-mail do responsável pela ação não
    fica guardado à parte: o e-mail atual serve como ele, a não ser que seja
    o de outro membro da equipe (a coordenação antiga, quando errada)."""
    equipe = doc.get("equipe") or []
    responsavel = doc.get("responsavel_acao")
    atual = (doc.get("email_professor") or "").lower() or None
    donos = {(m.get("email") or "").lower(): normalizar(m.get("nome")) for m in equipe if m.get("email")}
    if atual in donos and responsavel and donos[atual] != normalizar(responsavel):
        atual = None
    nome, email = escolher_coordenacao(equipe, responsavel, atual)
    return nome or doc.get("nome_professor"), email or doc.get("email_professor")


async def recalcular(db, confirmar: bool = False, exemplos: int = 20) -> dict:
    mudancas = []
    examinados = 0
    async for doc in db.projetos.find(FILTRO, CAMPOS):
        examinados += 1
        nome, email = nova_coordenacao(doc)
        if nome != doc.get("nome_professor") or email != doc.get("email_professor"):
            mudancas.append((doc, nome, email))

    print(f"{examinados} ações de extensão do SIGAA com equipe gravada; {len(mudancas)} mudam de coordenação "
          f"ou de e-mail.")
    por_instituicao = Counter(doc.get("instituicao") for doc, _, _ in mudancas)
    print("Por instituição: " + ", ".join(f"{k} {v}" for k, v in por_instituicao.most_common()))
    for doc, nome, email in mudancas[:exemplos]:
        print(f"\n- {doc.get('instituicao')} | {doc.get('titulo')}")
        print(f"    responsável pela ação: {doc.get('responsavel_acao')}")
        print(f"    coordenação: {doc.get('nome_professor')} -> {nome}")
        if email != doc.get("email_professor"):
            print(f"    e-mail: {doc.get('email_professor')} -> {email}")

    if confirmar:
        for doc, nome, email in mudancas:
            await db.projetos.update_one({"_id": doc["_id"]},
                                         {"$set": {"nome_professor": nome, "email_professor": email}})
        print(f"\n{len(mudancas)} projetos atualizados.")
    else:
        print("\nNada foi gravado (rode com --confirmar para aplicar).")
    return {"examinados": examinados, "mudancas": len(mudancas)}


async def main(argv: list[str]) -> int:
    load_dotenv()
    from database.connection import Database

    await Database.connect()
    try:
        await recalcular(Database.get_db(), confirmar="--confirmar" in argv)
    finally:
        await Database.disconnect()
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main(sys.argv[1:])))
