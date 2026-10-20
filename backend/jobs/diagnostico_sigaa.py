"""
Diagnóstico de uma consulta pública do SIGAA, sem gravar nada no banco.

Mostra o que o coletor vê em cada etapa (formulário, busca, listagem e o
detalhe do primeiro item), com trechos do HTML cru, para adaptar o coletor a
SIGAAs que não devolvem itens ou cujo detalhe não abre:

    SIGAA_INSTITUICAO=UFPA python -m jobs.diagnostico_sigaa pesquisa 2026
"""

import sys
from datetime import date

from bs4 import BeautifulSoup

from services.sigaa import parser, scraper
from services.sigaa.config import SigaaConfig


def _cortar(texto: str, limite: int) -> str:
    texto = " ".join((texto or "").split())
    return texto if len(texto) <= limite else texto[:limite] + " [...]"


def _rotulo_da_linha(tag) -> str:
    """Texto da <tr> do campo sem as opções dos selects (que podem ter centenas)."""
    linha = tag.find_parent("tr")
    if linha is None:
        return "(fora de tabela)"
    partes = [s for s in linha.find_all(string=True) if s.parent.name not in ("option", "script")]
    return _cortar(" ".join(partes), 80)


def _campos(form) -> list[str]:
    saida = []
    for tag in form.find_all(["input", "select", "textarea"]):
        tipo = tag.name if tag.name != "input" else (tag.get("type") or "text").lower()
        if tipo == "hidden" and tag.get("name") == "javax.faces.ViewState":
            continue
        extra = ""
        if tag.name == "select":
            opcoes = tag.find_all("option")
            extra = f" opções={len(opcoes)}"
            if len(opcoes) <= 12:
                extra += " [" + "; ".join(
                    f"{o.get('value')}={_cortar(o.get_text(), 30)}{' (selecionada)' if o.has_attr('selected') else ''}"
                    for o in opcoes) + "]"
        elif tipo in ("checkbox", "radio"):
            extra = f" value={tag.get('value')!r} checked={tag.has_attr('checked')}"
        elif tipo != "hidden":
            extra = f" value={_cortar(tag.get('value', ''), 40)!r}"
        else:
            extra = f" value={_cortar(tag.get('value', ''), 60)!r}"
        saida.append(f"    {tipo:9} {tag.get('name')}{extra} | linha: {_rotulo_da_linha(tag)}")
    return saida


def _mensagens(soup) -> str:
    """Avisos do JSF (ul de erros/infos) que explicam uma busca vazia."""
    textos = []
    for tag in soup.find_all(["ul", "div", "span"], class_=True):
        classes = " ".join(tag.get("class") or []).lower()
        if any(p in classes for p in ("erro", "error", "info", "warning", "aviso", "msg")):
            texto = _cortar(tag.get_text(" "), 200)
            if texto and texto not in textos:
                textos.append(texto)
    return " || ".join(textos[:5]) or "(nenhuma)"


def _texto_depois_do_form(soup) -> str:
    """Texto visível depois do formulário de busca, onde a listagem ou o aviso
    de busca vazia apareceriam."""
    form = soup.find("form")
    if form is None:
        return "(sem form)"
    partes = []
    for irmao in form.find_all_next(string=True):
        if irmao.parent.name in ("script", "style", "option"):
            continue
        partes.append(irmao)
        if sum(len(p) for p in partes) > 2000:
            break
    texto = " ".join(" ".join(partes).split())
    return _cortar(texto[texto.rfind("Cancelar") + 8:] if "Cancelar" in texto else texto, 300)


def _resposta(titulo: str, resp) -> BeautifulSoup:
    historico = " -> ".join(f"{r.status_code} {r.headers.get('location', '')}" for r in resp.history) or "sem redirecionamento"
    soup = BeautifulSoup(resp.text, "html.parser")
    tabela = soup.find("table", class_="listagem")
    print(f"  {titulo}: HTTP {resp.status_code}, {len(resp.text)} caracteres, url final {resp.url}")
    print(f"    redirecionamentos: {historico}")
    print(f"    mensagens: {_mensagens(soup)}")
    print(f"    table.listagem: {'linhas=' + str(len(tabela.find_all('tr'))) if tabela else 'não existe'}")
    if tabela is None:
        print(f"    texto depois do form: {_texto_depois_do_form(soup)}")
    return soup


def _variante(client, url: str, dados: dict, titulo: str, tirar) -> None:
    """Refaz a busca numa sessão nova, sem os campos para os quais `tirar(nome)` é verdadeiro."""
    form = parser.achar_form(BeautifulSoup(client.get(url), "html.parser"))
    base = parser.payload_base(form)
    for nome in list(base):
        if nome.startswith(form.get("id") + ":check") or nome.startswith(form.get("id") + ":select"):
            base.pop(nome)
    base.update({k: v for k, v in dados.items() if k != "javax.faces.ViewState"})
    for nome in [k for k in base if tirar(k)]:
        base.pop(nome)
    _resposta(titulo, client.request_raw("POST", url, data=base))


def _cookies(client) -> str:
    return ", ".join(f"{c.name} (path={c.path})" for c in client.session.cookies) or "nenhum"


def diagnosticar(modulo: str, ano: str) -> None:
    cfg = SigaaConfig.from_env()
    client = scraper.SigaaClient(cfg)
    url = scraper.urls_consulta(cfg.base_url)[modulo]
    print(f"\n######## {cfg.instituicao} {modulo} {ano} ({url})")

    html_form = client.get(url)
    soup_form = BeautifulSoup(html_form, "html.parser")
    form = parser.achar_form(soup_form)
    print(f"  form: id={form.get('id')} action={form.get('action')}; outros forms: "
          f"{[f.get('id') for f in soup_form.find_all('form') if f is not form]}")
    print(f"  cookies: {_cookies(client)}")
    print("  campos:")
    print("\n".join(_campos(form)))

    situacao = cfg.pesquisa_situacao if modulo == "pesquisa" else None
    try:
        dados = scraper.montar_payload_busca(html_form, modulo, ano, situacao)
    except (ValueError, scraper.SigaaErro) as e:
        print(f"  payload da busca: ERRO {e}")
        return
    print("  payload da busca (sem ViewState):")
    for k, v in dados.items():
        if k != "javax.faces.ViewState" and v not in ("", None):
            print(f"    {k} = {_cortar(str(v), 60)!r}")

    resp = client.request_raw("POST", url, data=dados)
    soup = _resposta("busca do coletor", resp)
    if modulo == "pesquisa":
        itens = parser.parse_listagem_pesquisa(resp.text)
    else:
        itens = parser.parse_listagem_extensao(resp.text, cfg.base_url)
    print(f"    itens reconhecidos: {len(itens)}")

    if not itens:
        # Variações da busca, para separar "filtro errado" de "módulo vazio".
        def e_ano(k):
            return k.lower().endswith(("ano", "checkano", "buscaano", "selectbuscaano"))

        def e_tipo(k):
            return "tipo" in k.lower()

        _variante(client, url, dados, "busca sem o ano", e_ano)
        if modulo == "extensao":
            _variante(client, url, dados, "busca sem o tipo de ação", e_tipo)
            _variante(client, url, dados, "busca sem ano nem tipo", lambda k: e_ano(k) or e_tipo(k))
        return

    tabela = soup.find("table", class_="listagem")
    linhas = (tabela.find("tbody") or tabela).find_all("tr", recursive=False)
    print("  primeiras linhas da listagem (HTML cru):")
    for tr in linhas[:4]:
        print(f"    {_cortar(str(tr), 900)}")
    print(f"  forms da listagem: {[(f.get('id'), f.get('action')) for f in soup.find_all('form')]}")
    item = itens[0]
    print(f"  primeiro item: { {k: item.get(k) for k in ('sigaa_id', 'titulo', 'situacao', 'link_detalhe', 'detalhe_params')} }")
    sem_link = [i for i in itens if not i.get("link_detalhe") and not i.get("detalhe_params")]
    print(f"  itens sem link de detalhe: {len(sem_link)} de {len(itens)}")
    print(f"  cookies: {_cookies(client)}")

    if item.get("link_detalhe"):
        resp_d = client.request_raw("GET", item["link_detalhe"])
        _resposta("detalhe pelo link público", resp_d)
        print(f"    {parser.diagnostico_pagina(resp_d.text, 400)}")
    if item.get("detalhe_params"):
        form_lista = parser.achar_form(soup, "formConsulta")
        payload = parser.payload_base(form_lista)
        payload.update(item["detalhe_params"])
        print(f"  postback do detalhe: form {form_lista.get('id')} (action {form_lista.get('action')}), "
              f"parâmetros do link {item['detalhe_params']}")
        resp_d = client.request_raw("POST", url, data=payload)
        _resposta("detalhe por postback", resp_d)
        print(f"    {parser.diagnostico_pagina(resp_d.text, 400)}")
        acao = form_lista.get("action")
        if acao and not url.endswith(acao):
            alvo = cfg.base_url.rstrip("/") + acao if acao.startswith("/") else acao
            resp_a = client.request_raw("POST", alvo, data=payload)
            _resposta(f"detalhe por postback na action do form ({alvo})", resp_a)
            print(f"    {parser.diagnostico_pagina(resp_a.text, 400)}")


if __name__ == "__main__":
    modulo = sys.argv[1] if len(sys.argv) > 1 else "pesquisa"
    ano = sys.argv[2] if len(sys.argv) > 2 and sys.argv[2] else str(date.today().year)
    diagnosticar(modulo, ano)
