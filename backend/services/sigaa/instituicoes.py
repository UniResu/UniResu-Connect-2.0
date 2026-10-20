"""
Instituições que usam o SIGAA (sistema da UFRN adotado por dezenas de
universidades e institutos federais) e expõem a consulta pública de projetos.

O coletor é o mesmo da UNIR: muda só o endereço base e a sigla. `ATIVAS`
são as instituições cujo portal público foi verificado (as duas páginas de
consulta respondem sem login); são as que o agendamento semanal coleta.
As demais ficam registradas para execução manual e verificação futura.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class InstituicaoSigaa:
    sigla: str
    nome: str
    base_url: str
    # Módulos com consulta pública funcionando (padrão: pesquisa e extensão).
    modulos: tuple[str, ...] = ("pesquisa", "extensao")
    # Portais lentos: espera maior por resposta e teto de detalhes abertos por
    # execução (0 = todos). Com teto, a coleta é incremental: abre primeiro os
    # detalhes que faltam e completa o resto nas semanas seguintes.
    timeout_segundos: float = 60.0
    max_detalhes: int = 0


_LISTA = [
    InstituicaoSigaa("UNIR", "Universidade Federal de Rondônia", "https://sigaa.unir.br"),
    InstituicaoSigaa("UFRN", "Universidade Federal do Rio Grande do Norte", "https://sigaa.ufrn.br"),
    InstituicaoSigaa("UFPB", "Universidade Federal da Paraíba", "https://sigaa.ufpb.br"),
    InstituicaoSigaa("UFPI", "Universidade Federal do Piauí", "https://sigaa.ufpi.br"),
    InstituicaoSigaa("UFG", "Universidade Federal de Goiás", "https://sigaa.sistemas.ufg.br"),
    InstituicaoSigaa("UFCAT", "Universidade Federal de Catalão", "https://sigaa.sistemas.ufcat.edu.br"),
    InstituicaoSigaa("UFJ", "Universidade Federal de Jataí", "https://sigaa.sistemas.ufj.edu.br"),
    InstituicaoSigaa("UFS", "Universidade Federal de Sergipe", "https://www.sigaa.ufs.br"),
    InstituicaoSigaa("UNB", "Universidade de Brasília", "https://sigaa.unb.br"),
    InstituicaoSigaa("UFRRJ", "Universidade Federal Rural do Rio de Janeiro", "https://sigaa.ufrrj.br"),
    InstituicaoSigaa("UFSB", "Universidade Federal do Sul da Bahia", "https://sig.ufsb.edu.br"),
    InstituicaoSigaa("UFCA", "Universidade Federal do Cariri", "https://sig.ufca.edu.br",
                     modulos=("extensao",)),  # nenhum projeto de pesquisa na consulta pública
    InstituicaoSigaa("UNILAB", "Universidade da Integração Internacional da Lusofonia Afro-Brasileira",
                     "https://sig.unilab.edu.br"),
    InstituicaoSigaa("UNILA", "Universidade Federal da Integração Latino-Americana", "https://sig.unila.edu.br"),
    InstituicaoSigaa("UFMA", "Universidade Federal do Maranhão", "https://sigaa.ufma.br"),
    InstituicaoSigaa("UFPA", "Universidade Federal do Pará", "https://sigaa.ufpa.br"),
    InstituicaoSigaa("UFERSA", "Universidade Federal Rural do Semi-Árido", "https://sigaa.ufersa.edu.br"),
    InstituicaoSigaa("UFAL", "Universidade Federal de Alagoas", "https://sigaa.sig.ufal.br"),
    InstituicaoSigaa("UFCG", "Universidade Federal de Campina Grande", "https://sigaa.ufcg.edu.br",
                     modulos=("pesquisa",)),  # nenhuma ação na consulta pública de extensão
    InstituicaoSigaa("UFLA", "Universidade Federal de Lavras", "https://sigaa.ufla.br"),
    InstituicaoSigaa("UFRA", "Universidade Federal Rural da Amazônia", "https://sigaa.ufra.edu.br"),
    InstituicaoSigaa("UFOB", "Universidade Federal do Oeste da Bahia", "https://sig.ufob.edu.br"),
    InstituicaoSigaa("UNEMAT", "Universidade do Estado de Mato Grosso", "https://sigaa.unemat.br",
                     modulos=("extensao",)),  # a consulta de pesquisa dá erro no portal
    InstituicaoSigaa("UEMA", "Universidade Estadual do Maranhão", "https://sis.sig.uema.br"),
    InstituicaoSigaa("UFRB", "Universidade Federal do Recôncavo da Bahia", "https://sistemas.ufrb.edu.br"),
    InstituicaoSigaa("UFSJ", "Universidade Federal de São João del-Rei", "https://sig.ufsj.edu.br",
                     modulos=("extensao",)),  # nenhum projeto de pesquisa na consulta pública
    InstituicaoSigaa("IFPA", "Instituto Federal do Pará", "https://sigaa.ifpa.edu.br"),
    InstituicaoSigaa("IFS", "Instituto Federal de Sergipe", "https://sigaa.ifs.edu.br"),
    InstituicaoSigaa("IFES", "Instituto Federal do Espírito Santo", "https://sigaa.ifes.edu.br"),
    InstituicaoSigaa("IFRJ", "Instituto Federal do Rio de Janeiro", "https://sigaa.ifrj.edu.br"),
    InstituicaoSigaa("IFAL", "Instituto Federal de Alagoas", "https://sigaa.ifal.edu.br"),
    InstituicaoSigaa("CEFET-MG", "Centro Federal de Educação Tecnológica de Minas Gerais", "https://sig.cefetmg.br"),
    InstituicaoSigaa("UEMASUL", "Universidade Estadual da Região Tocantina do Maranhão", "https://sigaa.uemasul.edu.br"),
    InstituicaoSigaa("UESPI", "Universidade Estadual do Piauí", "https://sigaa.uespi.br"),
    InstituicaoSigaa("UERN", "Universidade do Estado do Rio Grande do Norte", "https://sigaa.uern.br"),
    InstituicaoSigaa("IFRS", "Instituto Federal do Rio Grande do Sul", "https://sig.ifrs.edu.br"),
    InstituicaoSigaa("IFFAR", "Instituto Federal Farroupilha", "https://sig.iffarroupilha.edu.br"),
    InstituicaoSigaa("IFC", "Instituto Federal Catarinense", "https://sig.ifc.edu.br"),
    InstituicaoSigaa("IFSC", "Instituto Federal de Santa Catarina", "https://sig.ifsc.edu.br"),
    InstituicaoSigaa("IFPR", "Instituto Federal do Paraná", "https://sigaa.ifpr.edu.br"),
    InstituicaoSigaa("IFSUDESTEMG", "Instituto Federal do Sudeste de Minas Gerais", "https://sig.ifsudestemg.edu.br"),
    InstituicaoSigaa("IFAM", "Instituto Federal do Amazonas", "https://sig.ifam.edu.br"),
    InstituicaoSigaa("IFAC", "Instituto Federal do Acre", "https://sig.ifac.edu.br"),
    # Sem projetos na consulta pública de pesquisa. O detalhe da extensão só
    # abre por postback e leva perto de um minuto por ação.
    InstituicaoSigaa("UFC", "Universidade Federal do Ceará", "https://si3.ufc.br",
                     modulos=("extensao",), timeout_segundos=300.0, max_detalhes=120),
    InstituicaoSigaa("UFABC", "Universidade Federal do ABC", "https://sig.ufabc.edu.br"),
    InstituicaoSigaa("UFPE", "Universidade Federal de Pernambuco", "https://sigaa.ufpe.br"),
    InstituicaoSigaa("UFRPE", "Universidade Federal Rural de Pernambuco", "https://sigs.ufrpe.br"),
    InstituicaoSigaa("UNIFESSPA", "Universidade Federal do Sul e Sudeste do Pará", "https://sigaa.unifesspa.edu.br"),
    InstituicaoSigaa("UFOPA", "Universidade Federal do Oeste do Pará", "https://sigaa.ufopa.edu.br"),
    InstituicaoSigaa("UFRR", "Universidade Federal de Roraima", "https://sigaa.ufrr.br"),
    InstituicaoSigaa("UNIFEI", "Universidade Federal de Itajubá", "https://sigaa.unifei.edu.br"),
    InstituicaoSigaa("UDESC", "Universidade do Estado de Santa Catarina", "https://portal.udesc.br"),
    InstituicaoSigaa("UFAPE", "Universidade Federal do Agreste de Pernambuco", "https://sigs.ufape.edu.br"),
    InstituicaoSigaa("UFBA", "Universidade Federal da Bahia", "https://sigaa.ufba.br"),
    InstituicaoSigaa("UFDPAR", "Universidade Federal do Delta do Parnaíba", "https://sigaa.ufdpar.edu.br"),
    InstituicaoSigaa("UEM", "Universidade Estadual de Maringá", "https://sigs.uem.br"),
    InstituicaoSigaa("UNIFAP", "Universidade Federal do Amapá", "https://sigaa.unifap.br"),
    InstituicaoSigaa("UFFS", "Universidade Federal da Fronteira Sul", "https://sigaa.uffs.edu.br"),
    InstituicaoSigaa("UNIVASF", "Universidade Federal do Vale do São Francisco", "https://sig.univasf.edu.br"),
    InstituicaoSigaa("UFT", "Universidade Federal do Tocantins", "https://sigaa.uft.edu.br"),
    InstituicaoSigaa("UFAC", "Universidade Federal do Acre", "https://sigaa.ufac.br"),
    InstituicaoSigaa("UEPA", "Universidade do Estado do Pará", "https://sigaa.uepa.br"),
    InstituicaoSigaa("IFTO", "Instituto Federal do Tocantins", "https://sigaa.ifto.edu.br"),
    InstituicaoSigaa("IFAP", "Instituto Federal do Amapá", "https://sigaa.ifap.edu.br"),
]

INSTITUICOES_SIGAA: dict[str, InstituicaoSigaa] = {i.sigla: i for i in _LISTA}

# Portais verificados em 07/10/2026 (as consultas públicas respondem sem
# login nem captcha); é o que o agendamento semanal coleta. Fora da lista:
# CEFET-MG, UEMA, UESPI e UFPI (certificado TLS inválido), IFAC, IFFAR, IFS,
# UFLA, UFOPA, UFRPE e UNIFESSPA (sem resposta), IFAP, IFTO, UFAC e UFT (DNS),
# IFPR (405), UFOB e UFRR (403), UNIVASF (404), UDESC (erro), IFSC,
# IFSUDESTEMG e UFRB (captcha ou bloqueio de robôs).
# Saíram em 20/10/2026, porque as duas consultas respondem mas não têm nenhum
# projeto, nem buscando sem filtro (pesquisa: "Não foram encontrados
# resultados"; extensão: "Nenhuma ação de extensão localizada"; ver
# jobs/diagnostico_sigaa.py): IFES, IFRJ, UEM, UEPA, UFAPE, UFBA, UFDPAR e UFFS.
ATIVAS: tuple[str, ...] = (
    "UNIR", "IFAL", "IFAM", "IFC", "IFPA", "IFRS", "UEMASUL", "UERN",
    "UFABC", "UFAL", "UFC", "UFCA", "UFCAT", "UFCG", "UFERSA", "UFG",
    "UFJ", "UFMA", "UFPA", "UFPB", "UFPE", "UFRA", "UFRN", "UFRRJ", "UFS", "UFSB", "UFSJ", "UNB",
    "UNEMAT", "UNIFAP", "UNIFEI", "UNILA", "UNILAB",
)


def instituicao_sigaa(sigla: str) -> InstituicaoSigaa:
    try:
        return INSTITUICOES_SIGAA[sigla.strip().upper()]
    except KeyError:
        raise ValueError(f"Instituição SIGAA desconhecida: {sigla!r}. "
                         f"Conhecidas: {', '.join(sorted(INSTITUICOES_SIGAA))}") from None
