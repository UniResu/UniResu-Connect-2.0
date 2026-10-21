"""Recalcular a coordenação das ações de extensão já gravadas, pela função na equipe."""

from jobs.recalcular_coordenacao import recalcular

EQUIPE_MEDPOP = [
    {"nome": "CHRISTIAN COLLINS KUEHN", "categoria": "DOCENTE", "funcao": "VICE-COORDENADOR(A)",
     "email": "christian@unir.br"},
    {"nome": "ANTÔNIO COUTINHO NETO", "categoria": "DOCENTE", "funcao": "COORDENADOR(A)"},
]


async def _medpop(db, email):
    await db.projetos.insert_one({
        "origem": "sigaa", "modulo": "extensao", "instituicao": "UNIR", "titulo": "MEDPOP",
        "equipe": EQUIPE_MEDPOP, "responsavel_acao": "ANTÔNIO COUTINHO NETO",
        "nome_professor": "CHRISTIAN COLLINS KUEHN", "email_professor": email,
    })


async def test_sem_confirmar_nao_grava(db):
    await _medpop(db, "antonio@unir.br")
    r = await recalcular(db)
    doc = await db.projetos.find_one({"titulo": "MEDPOP"})
    assert r == {"examinados": 1, "mudancas": 1}
    assert doc["nome_professor"] == "CHRISTIAN COLLINS KUEHN"


async def test_confirmar_troca_a_vice_pelo_coordenador_e_mantem_o_email_do_responsavel(db):
    await _medpop(db, "antonio@unir.br")
    await recalcular(db, confirmar=True)
    doc = await db.projetos.find_one({"titulo": "MEDPOP"})
    assert doc["nome_professor"] == "ANTÔNIO COUTINHO NETO"
    assert doc["email_professor"] == "antonio@unir.br"


async def test_email_que_era_da_vice_nao_fica_com_o_coordenador(db):
    # O e-mail antigo era o da vice e o coordenador não publica e-mail: o da
    # vice fica como contato de reserva, para a candidatura chegar à equipe.
    await _medpop(db, "christian@unir.br")
    await recalcular(db, confirmar=True)
    doc = await db.projetos.find_one({"titulo": "MEDPOP"})
    assert doc["nome_professor"] == "ANTÔNIO COUTINHO NETO"
    assert doc["email_professor"] == "christian@unir.br"
