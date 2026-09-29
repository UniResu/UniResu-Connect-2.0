"""Candidatura com carta de intenção: validação, montagem do e-mail e fluxo (Resend mockado)."""

from datetime import datetime, timedelta, timezone

import pytest
from pydantic import ValidationError

import controllers.candidatura_controller as cc
from models.candidatura_model import CandidaturaCreate

CARTA = (
    "Sou estudante do 5º período de Ciência da Computação e tenho interesse em robótica educacional.\n\n"
    "Quero participar deste projeto porque já atuei como monitor de programação e gostaria de levar "
    "esse conhecimento para escolas públicas da região.\n\n"
    "Tenho disponibilidade de 12 horas semanais, às tardes, e posso começar imediatamente."
)
assert len(CARTA) >= 300


def dados(**extra):
    base = {"nome": "Maria Silva", "curso_periodo": "Ciência da Computação — 5º período",
            "email": "maria@exemplo.com", "lattes_url": "http://lattes.cnpq.br/1234567890123456", "carta": CARTA}
    base.update(extra)
    return base


PROJETO = {"titulo": "Robótica educacional", "nome_professor": "ANA PAULA SOUZA", "email_professor": "ana@unir.br"}


# ── Validação ──

class TestValidacao:
    def test_dados_validos(self):
        d = CandidaturaCreate(**dados())
        assert d.lattes_url == "http://lattes.cnpq.br/1234567890123456"

    def test_carta_curta_e_rejeitada(self):
        with pytest.raises(ValidationError, match="carta"):
            CandidaturaCreate(**dados(carta="Quero participar." * 5))

    def test_carta_so_com_espacos_nao_conta(self):
        with pytest.raises(ValidationError):
            CandidaturaCreate(**dados(carta="   " * 200))

    def test_lattes_opcional(self):
        assert CandidaturaCreate(**dados(lattes_url="")).lattes_url is None
        assert CandidaturaCreate(**dados(lattes_url=None)).lattes_url is None

    @pytest.mark.parametrize("url", [
        "https://evil.com/lattes.cnpq.br",
        "javascript:alert(1)",
        "https://lattes.cnpq.br.evil.com/123",
        "lattes.cnpq.br/123",
    ])
    def test_lattes_so_aceita_dominio_do_cnpq(self, url):
        with pytest.raises(ValidationError, match="Lattes"):
            CandidaturaCreate(**dados(lattes_url=url))

    def test_email_invalido(self):
        with pytest.raises(ValidationError):
            CandidaturaCreate(**dados(email="nao-e-email"))

    def test_sanitiza_quebras_de_linha_e_controle(self):
        d = CandidaturaCreate(**dados(nome="Maria\r\nBcc: x@y.com\x00", carta="\x07" + CARTA + "\n\n\n\n\nFim.  "))
        assert d.nome == "Maria Bcc: x@y.com"
        assert "\x07" not in d.carta and "\n\n\n" not in d.carta
        assert d.carta.endswith("Fim.")


# ── Montagem dos e-mails ──

class TestEmails:
    def test_email_ao_coordenador(self):
        m = cc.montar_email_coordenador(PROJETO, CandidaturaCreate(**dados()))
        assert m["subject"] == "Carta de intenção — Robótica educacional — Maria Silva"
        assert m["to"] == ["ana@unir.br"]
        assert m["reply_to"] == "maria@exemplo.com"
        assert "attachments" not in m
        assert CARTA in m["text"]
        assert "Tenho disponibilidade de 12 horas semanais" in m["html"]

    def test_lattes_como_link_no_final(self):
        m = cc.montar_email_coordenador(PROJETO, CandidaturaCreate(**dados()))
        assert m["text"].rstrip().endswith("Currículo Lattes: http://lattes.cnpq.br/1234567890123456")
        assert m["html"].endswith(
            '<p>Currículo Lattes: <a href="http://lattes.cnpq.br/1234567890123456">'
            "http://lattes.cnpq.br/1234567890123456</a></p>"
        )

    def test_sem_lattes_nao_menciona(self):
        m = cc.montar_email_coordenador(PROJETO, CandidaturaCreate(**dados(lattes_url=None)))
        assert "Lattes" not in m["text"] and "Lattes" not in m["html"]

    def test_contato_manual_do_admin_tem_prioridade(self):
        projeto = {**PROJETO, "email_contato_manual": "secretaria@unir.br"}
        assert cc.montar_email_coordenador(projeto, CandidaturaCreate(**dados()))["to"] == ["secretaria@unir.br"]

    def test_html_do_aluno_e_escapado(self):
        m = cc.montar_email_coordenador(
            PROJETO, CandidaturaCreate(**dados(nome="<script>x</script>", carta="<b>oi</b> " + CARTA))
        )
        assert "<script>" not in m["html"] and "&lt;script&gt;" in m["html"]
        assert "<b>oi</b>" not in m["html"]

    def test_confirmacao_ao_aluno_sem_email_do_coordenador(self):
        m = cc.montar_email_confirmacao(PROJETO, CandidaturaCreate(**dados()))
        assert m["to"] == ["maria@exemplo.com"]
        assert "Robótica educacional" in m["subject"]
        assert CARTA in m["text"]
        assert "ana@unir.br" not in m["text"] + m["html"]


# ── Fluxo pelo endpoint ──

@pytest.fixture
def emails(monkeypatch):
    enviados = []

    async def falso(params):
        enviados.append(params)
        return True, f"id-{len(enviados)}"

    monkeypatch.setattr(cc, "enviar_email", falso)
    return enviados


async def _projeto(db, **extra):
    return str((await db.projetos.insert_one({**PROJETO, **extra})).inserted_id)


async def test_candidatura_envia_carta_e_confirmacao(api, db, emails):
    pid = await _projeto(db)
    r = await api.post(f"/api/projetos/{pid}/candidatar", json=dados())

    assert r.status_code == 200, r.text
    assert r.json()["email_enviado"] is True and r.json()["confirmacao_enviada"] is True
    assert [e["to"] for e in emails] == [["ana@unir.br"], ["maria@exemplo.com"]]

    doc = await db.candidaturas.find_one({})
    assert doc["carta_intencao"] == CARTA
    assert doc["nome_aluno"] == "Maria Silva"
    assert doc["lattes_url"] == "http://lattes.cnpq.br/1234567890123456"
    assert doc["status"] == "pendente"
    assert doc["usuario_id"] == "aluno-1"
    assert doc["email_enviado"] is True and doc["email_provider_id"] == "id-1"


async def test_candidatura_fica_salva_mesmo_se_email_falhar(api, db, monkeypatch):
    async def falha(params):
        return False, None
    monkeypatch.setattr(cc, "enviar_email", falha)

    r = await api.post(f"/api/projetos/{await _projeto(db)}/candidatar", json=dados())
    assert r.status_code == 200
    assert (await db.candidaturas.find_one({}))["email_enviado"] is False


async def test_projeto_sem_contato_recusa(api, db, emails):
    pid = await _projeto(db, email_professor=None)
    r = await api.post(f"/api/projetos/{pid}/candidatar", json=dados())
    assert r.status_code == 400
    assert "contato" in r.json()["detail"]
    assert emails == [] and await db.candidaturas.count_documents({}) == 0


async def test_projeto_inativo_retorna_404(api, db, emails):
    pid = await _projeto(db, ativo=False)
    assert (await api.post(f"/api/projetos/{pid}/candidatar", json=dados())).status_code == 404


async def test_validacao_no_endpoint_retorna_422(api, db, emails):
    pid = await _projeto(db)
    r = await api.post(f"/api/projetos/{pid}/candidatar", json=dados(carta="curta"))
    assert r.status_code == 422
    assert emails == []


async def test_candidatura_duplicada(api, db, emails):
    pid = await _projeto(db)
    await api.post(f"/api/projetos/{pid}/candidatar", json=dados())
    r = await api.post(f"/api/projetos/{pid}/candidatar", json=dados())
    assert r.status_code == 409


async def test_rate_limit_por_hora(api, db, emails, monkeypatch):
    monkeypatch.setattr(cc, "LIMITE_POR_HORA", 2)
    agora = datetime.now(timezone.utc)
    await db.candidaturas.insert_many([
        {"usuario_id": "aluno-1", "projeto_id": "outro", "data_candidatura": agora - timedelta(minutes=m)}
        for m in (5, 30)
    ])
    r = await api.post(f"/api/projetos/{await _projeto(db)}/candidatar", json=dados())
    assert r.status_code == 429
    assert emails == []


async def test_rate_limit_ignora_candidaturas_antigas(api, db, emails, monkeypatch):
    monkeypatch.setattr(cc, "LIMITE_POR_HORA", 2)
    antiga = datetime.now(timezone.utc) - timedelta(hours=3)
    await db.candidaturas.insert_many([
        {"usuario_id": "aluno-1", "projeto_id": "outro", "data_candidatura": antiga} for _ in range(2)
    ])
    r = await api.post(f"/api/projetos/{await _projeto(db)}/candidatar", json=dados())
    assert r.status_code == 200
