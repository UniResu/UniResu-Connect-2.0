"""
Links para o SIGAA de origem de um projeto coletado.

As ações de extensão têm página pública própria (`link_detalhe`, gravado na
coleta). Os projetos de pesquisa não têm: no SIGAA o detalhe da pesquisa só
abre por um formulário JSF, sem endereço fixo. Para eles, a plataforma
aponta para a consulta pública de projetos da instituição, onde o projeto é
encontrado pelo código ou pelo título.
"""

from typing import Any, Optional

from services.sigaa.instituicoes import INSTITUICOES_SIGAA

# Páginas públicas de consulta, por módulo (as mesmas que a coleta usa).
CAMINHOS_CONSULTA = {
    "pesquisa": "/sigaa/public/pesquisa/consulta_projetos.jsf",
    "extensao": "/sigaa/public/extensao/consulta_extensao.jsf",
}


def link_consulta(doc: dict[str, Any]) -> Optional[str]:
    """Consulta pública do SIGAA da instituição do projeto, no módulo dele.
    None para projetos que não vieram do SIGAA ou de instituição desconhecida."""
    if doc.get("origem") != "sigaa":
        return None
    modulo = doc.get("modulo") or doc.get("tipo_sigaa")
    caminho = CAMINHOS_CONSULTA.get(modulo or "")
    instituicao = INSTITUICOES_SIGAA.get((doc.get("instituicao") or "UNIR").strip().upper())
    if not caminho or instituicao is None:
        return None
    return instituicao.base_url.rstrip("/") + caminho
