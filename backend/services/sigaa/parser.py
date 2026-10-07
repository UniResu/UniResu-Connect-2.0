"""
Parser das páginas públicas do SIGAA/UNIR (pesquisa e extensão).

Funções puras: recebem HTML (str já decodificada) e devolvem dicts. Não
fazem rede — o fluxo de requisições fica em `scraper.py`. Isso permite
testar tudo com fixtures de HTML salvo.

Estrutura observada (set/2026):
- Pesquisa (listagem): tabela `table.listagem` agrupada por linhas
  `tr.centro` (campus/núcleo) e `tr.ano`. Cada projeto ocupa 3 linhas:
  (código | título), (coordenador | tipo | situação | link), (descrição).
- Extensão (listagem): tabela `table.listagem` com colunas
  "Ano - Título" | tipo da ação | sigla do departamento. Não traz
  coordenador nem situação — esses vêm da página de detalhe.
- Detalhes: pares `<th>Rótulo:</th><td>valor</td>` + seções `<h4>`.
"""

import re
import unicodedata
from datetime import date, datetime
from typing import Optional

from bs4 import BeautifulSoup

BASE_URL = "https://sigaa.unir.br"
CAMINHO_DETALHE_EXTENSAO = "/sigaa/link/public/extensao/visualizacaoAcaoExtensao/{id}"
URL_DETALHE_EXTENSAO = BASE_URL + CAMINHO_DETALHE_EXTENSAO


def url_detalhe_extensao(sigaa_id, base_url: str = BASE_URL) -> str:
    """Link público (GET) da página de uma ação de extensão no SIGAA da instituição."""
    return base_url.rstrip("/") + CAMINHO_DETALHE_EXTENSAO.format(id=sigaa_id)

SITUACAO_EM_EXECUCAO = "EM EXECUÇÃO"

_RE_EMAIL = re.compile(r"[\w.+-]+@[\w-]+(?:\.[\w-]+)+")
_RE_DATA = re.compile(r"(\d{2}/\d{2}/\d{4})")
_RE_PARAMS_JSF = re.compile(r"'([^']+)':'([^']*)'")


# ─────────────────────────────────────────────
#  Utilidades de texto
# ─────────────────────────────────────────────

def limpar(txt: Optional[str]) -> str:
    """Colapsa espaços/quebras de linha."""
    return re.sub(r"\s+", " ", txt or "").strip()


def normalizar(txt: Optional[str]) -> str:
    """Remove acentos, maiúsculas e espaços extras — para comparar/chavear."""
    txt = unicodedata.normalize("NFKD", limpar(txt))
    txt = "".join(c for c in txt if not unicodedata.combining(c))
    return txt.upper()


def _soup(html: str) -> BeautifulSoup:
    return BeautifulSoup(html, "html.parser")


# ─────────────────────────────────────────────
#  Formulário JSF
# ─────────────────────────────────────────────

def achar_form(soup: BeautifulSoup, form_id: Optional[str] = None):
    """Acha o <form> principal (o que carrega o javax.faces.ViewState)."""
    if form_id:
        form = soup.find("form", id=form_id)
        if form:
            return form
    for form in soup.find_all("form"):
        if form.find("input", {"name": "javax.faces.ViewState"}):
            return form
    raise ValueError("Formulário JSF não encontrado — o layout do SIGAA mudou?")


def payload_base(form) -> dict:
    """Copia todos os campos do form com seus valores padrão (inclui ViewState).

    Botões não entram: no JSF só o botão "clicado" vai no POST.
    Checkboxes/radios não marcados também não são enviados.
    """
    dados: dict = {}
    for inp in form.find_all("input"):
        nome = inp.get("name")
        if not nome:
            continue
        tipo = (inp.get("type") or "text").lower()
        if tipo in ("submit", "button", "image", "reset"):
            continue
        if tipo in ("checkbox", "radio") and not inp.has_attr("checked"):
            continue
        dados[nome] = inp.get("value", "")
    for sel in form.find_all("select"):
        nome = sel.get("name")
        if not nome:
            continue
        opt = sel.find("option", selected=True) or sel.find("option")
        dados[nome] = opt.get("value", "") if opt else ""
    for ta in form.find_all("textarea"):
        if ta.get("name"):
            dados[ta["name"]] = ta.get_text()
    return dados


def _marcar_checkbox_da_linha(tag, dados: dict) -> None:
    """No SIGAA cada filtro tem um checkbox na mesma <tr> que o "liga"."""
    linha = tag.find_parent("tr") if tag else None
    chk = linha.find("input", {"type": "checkbox"}) if linha else None
    if chk and chk.get("name"):
        dados[chk["name"]] = chk.get("value") or "on"


def aplicar_filtro_select(form, dados: dict, texto_opcao: str) -> bool:
    """Seleciona, em qualquer <select>, a opção cujo texto bate com `texto_opcao`."""
    alvo = normalizar(texto_opcao)
    for sel in form.find_all("select"):
        for opt in sel.find_all("option"):
            if normalizar(opt.get_text()) == alvo:
                dados[sel["name"]] = opt.get("value", "")
                _marcar_checkbox_da_linha(sel, dados)
                return True
    return False


def aplicar_filtro_texto(form, dados: dict, palavras_rotulo: list[str], valor: str) -> bool:
    """Preenche o <input type=text> cuja linha tem um rótulo com alguma das palavras."""
    alvos = [normalizar(p) for p in palavras_rotulo]
    for inp in form.find_all("input"):
        if (inp.get("type") or "text").lower() != "text" or not inp.get("name"):
            continue
        linha = inp.find_parent("tr")
        rotulo = normalizar(linha.get_text(" ")) if linha else ""
        if any(a in rotulo for a in alvos):
            dados[inp["name"]] = valor
            _marcar_checkbox_da_linha(inp, dados)
            return True
    return False


_PLACEHOLDER_OPCAO = ("", "0")


def opcoes_select(form, nome_contem: str) -> list[tuple[str, str]]:
    """Opções (valor, texto) do <select> cujo name contém `nome_contem`, sem a
    opção vazia "-- SELECIONE --". Lista vazia se o select não existe."""
    alvo = normalizar(nome_contem)
    for sel in form.find_all("select"):
        if alvo in normalizar(sel.get("name")):
            opcoes = []
            for opt in sel.find_all("option"):
                valor, texto = opt.get("value", ""), limpar(opt.get_text())
                if valor in _PLACEHOLDER_OPCAO or texto.startswith("--") or "SELECIONE" in normalizar(texto):
                    continue
                opcoes.append((valor, texto))
            return opcoes
    return []


def aplicar_select_por_nome(form, dados: dict, nome_contem: str, valor: str) -> bool:
    """Seleciona, no <select> cujo name contém `nome_contem`, a opção de valor `valor`."""
    alvo = normalizar(nome_contem)
    for sel in form.find_all("select"):
        if alvo in normalizar(sel.get("name")):
            dados[sel["name"]] = valor
            _marcar_checkbox_da_linha(sel, dados)
            return True
    return False


def opcao_disponivel(form, textos: list[str]) -> Optional[str]:
    """Primeiro texto da lista que existe como opção em algum <select>."""
    alvos = {normalizar(t): t for t in textos}
    for sel in form.find_all("select"):
        for opt in sel.find_all("option"):
            texto = normalizar(opt.get_text())
            if texto in alvos:
                return alvos[texto]
    return None


def opcoes_de_situacao(form) -> list[str]:
    return [texto for _, texto in opcoes_select(form, "situacao")]


def resultados_excessivos(html: str) -> bool:
    """O SIGAA de algumas instituições limita a consulta pública e pede para
    restringir a busca ("A consulta retornou 599 resultados. Por favor,
    restrinja mais a busca." ou "resultados excessivos")."""
    texto = normalizar(BeautifulSoup(html, "html.parser").get_text(" "))
    return "RESTRINJA MAIS A BUSCA" in texto or "RESULTADOS EXCESSIVOS" in texto


def situacao_vigente(texto: Optional[str]) -> bool:
    """Situação de projeto de pesquisa que conta como em execução, nas
    variações que os SIGAAs publicam (EM EXECUÇÃO, EM ANDAMENTO, RENOVADO)."""
    t = normalizar(texto)
    return any(p in t for p in ("EXEC", "ANDAMENTO", "RENOVAD", "VIGENTE"))


def aplicar_botao_buscar(form, dados: dict) -> None:
    """Inclui name=value do botão de busca — é assim que o JSF sabe a ação."""
    for b in form.find_all("input", {"type": ["submit", "image", "button"]}):
        rotulo = normalizar(f"{b.get('value', '')} {b.get('name') or ''}")
        if "BUSCAR" in rotulo or "CONSULT" in rotulo:
            dados[b["name"]] = b.get("value", "Buscar")
            return
    raise ValueError("Botão Buscar não encontrado — o layout do SIGAA mudou?")


def params_link_jsf(onclick: str) -> dict:
    """Extrai os parâmetros `{'k':'v', ...}` de um link `jsfcljs(form, {...})` do JSF."""
    m = re.search(r"\{([^}]*)\}\s*,", onclick or "")
    return dict(_RE_PARAMS_JSF.findall(m.group(1))) if m else {}


# ─────────────────────────────────────────────
#  Diagnóstico (dry-run em instituições novas)
# ─────────────────────────────────────────────

def diagnostico_pagina(html: str, limite_texto: int = 1500) -> str:
    """Resumo da estrutura de uma página do SIGAA que não rendeu itens: tabelas,
    formulários, botões e o começo do texto visível. Serve para adaptar o
    parser a versões diferentes do SIGAA sem precisar baixar o HTML inteiro."""
    soup = _soup(html)
    tabelas = [f"table(class={t.get('class')}, id={t.get('id')}, linhas={len(t.find_all('tr'))})"
               for t in soup.find_all("table")][:12]
    forms = [f"form(id={f.get('id')}, action={f.get('action')})" for f in soup.find_all("form")][:6]
    botoes = [f"{b.get('type')}:{b.get('name')}={b.get('value')}"
              for b in soup.find_all("input", {"type": ["submit", "button"]})][:10]
    selects = [f"select({s.get('name')}, {len(s.find_all('option'))} opções)" for s in soup.find_all("select")][:10]
    for t in soup(["script", "style"]):
        t.decompose()
    texto = limpar(soup.get_text(" "))[:limite_texto]
    return ("DIAGNÓSTICO DA PÁGINA\n  tabelas: " + "; ".join(tabelas) + "\n  forms: " + "; ".join(forms)
            + "\n  botões: " + "; ".join(botoes) + "\n  selects: " + "; ".join(selects)
            + "\n  texto: " + texto)


# ─────────────────────────────────────────────
#  Listagens
# ─────────────────────────────────────────────

def _tabela_resultados(soup: BeautifulSoup):
    return soup.find("table", class_="listagem")


def parse_listagem_pesquisa(html: str) -> list[dict]:
    """Projetos de pesquisa da tabela de resultados."""
    tabela = _tabela_resultados(_soup(html))
    if tabela is None:
        return []
    corpo = tabela.find("tbody") or tabela
    itens: list[dict] = []
    centro: Optional[str] = None
    ano: Optional[str] = None
    atual: Optional[dict] = None

    for tr in corpo.find_all("tr", recursive=False):
        classes = tr.get("class") or []
        tds = tr.find_all("td", recursive=False)
        if "centro" in classes:
            centro = limpar(tr.get_text())
            continue
        if "ano" in classes:
            ano = limpar(tr.get_text())
            continue
        if not tds:
            continue
        # 1ª linha do projeto: código (rowspan=2) + título
        if tds[0].get("rowspan") == "2" and len(tds) >= 2:
            codigo = limpar(tds[0].get_text())
            m_ano = re.search(r"-(\d{4})$", codigo)
            atual = {
                "codigo": codigo,
                "titulo": limpar(tds[1].get_text()),
                "unidade": centro,
                "ano": ano or (m_ano.group(1) if m_ano else None),
            }
            continue
        # 2ª linha: coordenador | tipo | situação | link de detalhe
        if atual is not None and len(tds) >= 3 and "coordenador" not in atual:
            link = tr.find("a", onclick=True)
            params = params_link_jsf(link["onclick"]) if link else {}
            atual.update({
                "coordenador": limpar(tds[0].get_text()) or None,
                "categoria": limpar(tds[1].get_text()) or None,
                "situacao": limpar(tds[2].get_text()) or None,
                "sigaa_id": params.get("id"),
                "detalhe_params": params,
            })
            itens.append(atual)
            atual = None
    return itens


def parse_listagem_extensao(html: str, base_url: str = BASE_URL) -> list[dict]:
    """Ações de extensão da tabela de resultados. `base_url` é o SIGAA da
    instituição, usado para montar o link de detalhe de cada ação."""
    tabela = _tabela_resultados(_soup(html))
    if tabela is None:
        return []
    corpo = tabela.find("tbody") or tabela
    itens: list[dict] = []
    for tr in corpo.find_all("tr", recursive=False):
        tds = tr.find_all("td", recursive=False)
        if len(tds) < 3:
            continue
        texto = limpar(tds[0].get_text())
        m = re.match(r"^(\d{4})\s*-\s*(.+)$", texto)
        ano, titulo = (m.group(1), m.group(2)) if m else (None, texto)
        link = tds[0].find("a", onclick=True) or tr.find("a", onclick=True)
        params = params_link_jsf(link["onclick"]) if link else {}
        sigaa_id = params.get("idAtividadeExtensaoSelecionada") or params.get("id")
        itens.append({
            "sigaa_id": sigaa_id,
            "detalhe_params": params,
            "onclick": (link["onclick"][:300] if link else None),
            "titulo": titulo,
            "ano": ano,
            "categoria": limpar(tds[1].get_text()) or None,
            "unidade": limpar(tds[2].get_text()) or None,
            "link_detalhe": url_detalhe_extensao(sigaa_id, base_url) if sigaa_id else None,
        })
    return itens


# ─────────────────────────────────────────────
#  Detalhes
# ─────────────────────────────────────────────

def _campos_th_td(soup: BeautifulSoup) -> dict:
    """Mapa {RÓTULO NORMALIZADO: valor} a partir dos pares <th>/<td>."""
    campos: dict = {}
    for th in soup.find_all("th"):
        rotulo = normalizar(th.get_text()).rstrip(":").strip()
        td = th.find_next_sibling("td")
        if rotulo and td is not None and rotulo not in campos:
            campos[rotulo] = limpar(td.get_text(" "))
    return campos


def _secao_h4(soup: BeautifulSoup, *titulos: str) -> Optional[str]:
    alvos = {normalizar(t) for t in titulos}
    for h4 in soup.find_all("h4"):
        if normalizar(h4.get_text()) in alvos:
            nxt = h4.find_next_sibling()
            texto = limpar(nxt.get_text(" ")) if nxt is not None else ""
            return texto or None
    return None


def _email(valor: Optional[str]) -> Optional[str]:
    m = _RE_EMAIL.search(valor or "")
    return m.group(0).lower() if m else None


def _periodo(valor: Optional[str]) -> tuple[Optional[str], Optional[str]]:
    datas = _RE_DATA.findall(valor or "")
    iso = [datetime.strptime(d, "%d/%m/%Y").date().isoformat() for d in datas[:2]]
    return (iso[0] if iso else None, iso[1] if len(iso) > 1 else None)


def parse_detalhe_pesquisa(html: str) -> dict:
    soup = _soup(html)
    c = _campos_th_td(soup)
    if "COORDENADOR" not in c and "TITULO" not in c:
        raise ValueError("Página de detalhe de pesquisa inesperada.")
    inicio, fim = _periodo(c.get("PERIODO DO PROJETO"))
    return {
        "coordenador": c.get("COORDENADOR") or None,
        "email": _email(c.get("E-MAIL")),
        "unidade": c.get("CENTRO") or None,
        "situacao": c.get("SITUACAO") or None,
        "periodo_inicio": inicio,
        "periodo_fim": fim,
        "descricao": _secao_h4(soup, "Descrição"),
    }


_RE_CATEGORIA = re.compile(r"CATEGORIA\s*:\s*(.*?)\s*(?:FUNCAO\s*:|$)")
_RE_FUNCAO = re.compile(r"FUNCAO\s*:\s*(.*)$")


def parse_equipe(soup: BeautifulSoup) -> list[dict]:
    """Membros da equipe da ação de extensão (tabelas `equipeProjeto`): nome,
    categoria (DOCENTE, DISCENTE, TECNICO...) e função (COORDENADOR(A),
    MEMBRO...), como o SIGAA publica."""
    equipe: list[dict] = []
    for tabela in soup.find_all("table", class_="equipeProjeto"):
        span = tabela.find("span", class_="nome")
        if span is None:
            continue
        # O nome vem antes de "Categoria:"; função e categoria podem estar
        # quebradas em várias linhas e dentro de <font>, por isso a leitura é
        # feita sobre o texto corrido normalizado.
        linhas = [limpar(linha) for linha in span.get_text("\n").split("\n") if limpar(linha)]
        nome = next((linha for linha in linhas if not normalizar(linha).startswith(("CATEGORIA", "FUNCAO"))), None)
        texto = normalizar(span.get_text(" "))
        m_cat, m_fun = _RE_CATEGORIA.search(texto), _RE_FUNCAO.search(texto)
        if nome:
            equipe.append({
                "nome": nome,
                "categoria": (m_cat.group(1).strip() or None) if m_cat else None,
                "funcao": (m_fun.group(1).strip() or None) if m_fun else None,
            })
    return equipe


def coordenacao_da_equipe(equipe: list[dict]) -> Optional[str]:
    """Quem coordena de fato: membro com função de coordenação, de preferência
    docente. O campo "Responsável pela Ação" do SIGAA pode trazer um discente."""
    coordenadores = [m for m in equipe if "COORDENADOR" in normalizar(m.get("funcao"))]
    docentes = [m for m in coordenadores if "DOCENTE" in normalizar(m.get("categoria"))]
    escolhido = (docentes or coordenadores or [None])[0]
    return escolhido["nome"] if escolhido else None


def parse_detalhe_extensao(html: str) -> dict:
    soup = _soup(html)
    c = _campos_th_td(soup)
    if "RESPONSAVEL PELA ACAO" not in c and "TITULO" not in c:
        raise ValueError("Página de detalhe de extensão inesperada.")
    inicio, fim = _periodo(c.get("PERIODO DE REALIZACAO"))
    responsavel = c.get("RESPONSAVEL PELA ACAO") or None
    equipe = parse_equipe(soup)
    return {
        # Coordenação docente da equipe; sem equipe publicada, fica o responsável.
        "coordenador": coordenacao_da_equipe(equipe) or responsavel,
        "responsavel_acao": responsavel,
        "equipe": equipe,
        "email": _email(c.get("E-MAIL DO RESPONSAVEL")),
        "unidade": c.get("UNIDADE PROPONENTE") or None,
        "periodo_inicio": inicio,
        "periodo_fim": fim,
        "descricao": _secao_h4(soup, "Resumo"),
    }


def situacao_por_periodo(inicio: Optional[str], fim: Optional[str], hoje: Optional[date] = None) -> Optional[str]:
    """Extensão não publica "situação": derivamos do período de realização."""
    if not inicio or not fim:
        return None
    hoje = hoje or date.today()
    if hoje < date.fromisoformat(inicio):
        return "NÃO INICIADO"
    if hoje > date.fromisoformat(fim):
        return "FINALIZADO"
    return SITUACAO_EM_EXECUCAO
