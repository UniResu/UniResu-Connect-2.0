"""
Grandes áreas do conhecimento (tabela do CNPq) e a classificação de cada
projeto em uma delas, para o filtro "Área do conhecimento" da busca.

A classificação é heurística e segue uma ordem fixa de confiança:

1. um campo que já traga a grande área: `area_cnpq` (dados abertos da UFV)
   ou, quando o valor é um nome da tabela, `area_tematica` (o Portal da
   Pesquisa da UNIRIO publica ali a classificação do CNPq) e `area_estudo`
   (projetos manuais);
2. o nome da unidade ou departamento (Medicina, Engenharia, Letras...);
3. palavras-chave no título, na área temática, nas palavras-chave, na área
   de estudo e no grupo de pesquisa, com peso dobrado em relação às da
   descrição; vence a área com mais pontos;
4. "Multidisciplinar", quando nada acima decide.

Tudo é comparado sem acentos e em caixa alta (ver `normalizar`), porque os
portais publicam ora "Departamento de Botânica", ora "Departamento de
Botanica".
"""

import re
from typing import Any, Iterable, Optional

from services.sigaa.parser import normalizar

EXATAS = "Ciências Exatas e da Terra"
BIOLOGICAS = "Ciências Biológicas"
ENGENHARIAS = "Engenharias"
SAUDE = "Ciências da Saúde"
AGRARIAS = "Ciências Agrárias"
SOCIAIS_APLICADAS = "Ciências Sociais Aplicadas"
HUMANAS = "Ciências Humanas"
LINGUISTICA = "Linguística, Letras e Artes"
MULTIDISCIPLINAR = "Multidisciplinar"

# Ordem fixa de exibição (a mesma da tabela do CNPq).
AREAS_CONHECIMENTO = (
    EXATAS,
    BIOLOGICAS,
    ENGENHARIAS,
    SAUDE,
    AGRARIAS,
    SOCIAIS_APLICADAS,
    HUMANAS,
    LINGUISTICA,
    MULTIDISCIPLINAR,
)

# Campos do documento lidos pela classificação (também a projeção da migração).
CAMPOS_CLASSIFICACAO = ("titulo", "descricao", "unidade", "area_cnpq", "area_tematica", "area_estudo",
                        "palavras_chave", "grupo_pesquisa")


def _chave(texto: Any) -> str:
    """Texto sem acentos, em caixa alta e só com letras, dígitos e espaços simples."""
    return re.sub(r"[^A-Z0-9]+", " ", normalizar(str(texto))).strip()


_POR_CHAVE = {_chave(area): area for area in AREAS_CONHECIMENTO}


def area_valida(valor: Any) -> Optional[str]:
    """Nome canônico da grande área correspondente a `valor`, ignorando acentos,
    caixa e pontuação ("ciencias exatas e da terra" vale), ou None se o valor
    não está na tabela."""
    if not valor or not isinstance(valor, str):
        return None
    return _POR_CHAVE.get(_chave(valor))


# ─────────────────────────────────────────────
#  Regras por unidade/departamento
# ─────────────────────────────────────────────

# A primeira regra que casa vence, por isso os nomes compostos vêm antes das
# palavras soltas que eles contêm ("Educação Física" antes de "Educação" e de
# "Física"; "Engenharia Florestal" antes de "Engenharia").
_REGRAS_UNIDADE = [
    (r"EDUCACAO FISICA", SAUDE),
    (r"ENGENHARIA (AGRICOLA|AGRONOMICA|FLORESTAL|DE ALIMENTOS|DE PESCA|DE AQUICULTURA)", AGRARIAS),
    (r"ENGENHARIA DE SOFTWARE", EXATAS),
    (r"CIENCIAS? SOCIAIS APLICADAS", SOCIAIS_APLICADAS),
    (r"\b(MEDICINA|ENFERMAGEM|ODONTOLOGIA|FARMACIA|NUTRICAO|FISIOTERAPIA|FONOAUDIOLOGIA|BIOMEDICINA|"
     r"TERAPIA OCUPACIONAL|SAUDE COLETIVA|SAUDE)\b", SAUDE),
    (r"\bENGENHARIAS?\b", ENGENHARIAS),
    (r"\b(LETRAS|ARTES|MUSICA|LINGUAS|TEATR\w*|CENOGRAFIA|DANCA|REGENCIA|LINGUISTICA|LITERATURA)\b", LINGUISTICA),
    (r"\b(DIREITO|JURIDIC\w*|ADMINISTRACAO|ECONOMIA|ECONOMICAS|CONTABEIS|CONTABILIDADE|COMUNICACAO|JORNALISMO|"
     r"SERVICO SOCIAL|ARQUITETURA|URBANISMO|TURISMO|BIBLIOTECONOMIA|ARQUIVOLOGIA|MUSEOLOGIA)\b", SOCIAIS_APLICADAS),
    (r"\b(HISTORIA|GEOGRAFIA|FILOSOFIA|PSICOLOGIA|EDUCACAO|PEDAGOGIA|DIDATICA|SOCIOLOGIA|ANTROPOLOGIA|"
     r"ARQUEOLOGIA|CIENCIA POLITICA|TEOLOGIA|CIENCIAS SOCIAIS)\b", HUMANAS),
    (r"\b(AGRONOMIA|VETERINARIA|ZOOTECNIA|FLORESTAL|FLORESTAIS|ALIMENTOS|PESCA|AGRARIAS|AQUICULTURA|AGRICOLA|"
     r"AGRICULTURA|AGROECOLOGIA)\b", AGRARIAS),
    (r"\b(BIOLOGIA|BIOLOGICAS|BIOCIENCIAS|BIOQUIMICA|GENETICA|ECOLOGIA|MICROBIOLOGIA|FARMACOLOGIA|FISIOLOGIA|"
     r"FISIOLOGICAS|BOTANICA|ZOOLOGIA|IMUNOLOGIA|PARASITOLOGIA|MORFOLOGIA)\b", BIOLOGICAS),
    (r"\b(MATEMATICA|FISICA|QUIMICA|COMPUTACAO|INFORMATICA|SISTEMAS DE INFORMACAO|ESTATISTICA|GEOCIENCIAS|"
     r"GEOLOGIA|GEOFISICA|OCEANOGRAFIA|ASTRONOMIA|METEOROLOGIA)\b", EXATAS),
]
_REGRAS_UNIDADE = [(re.compile(p), area) for p, area in _REGRAS_UNIDADE]


def _area_por_unidade(unidade: Any) -> Optional[str]:
    texto = _chave(unidade)
    if not texto:
        return None
    for padrao, area in _REGRAS_UNIDADE:
        if padrao.search(texto):
            return area
    return None


# ─────────────────────────────────────────────
#  Palavras-chave
# ─────────────────────────────────────────────

# Cada entrada é (regex sobre o texto normalizado, área, peso). Os padrões
# começam em início de palavra e, salvo quando terminam em `\b`, aceitam as
# flexões que vierem depois ("EDUCA" cobre educação, educacional, educadoras).
# Palavras de escola e de ensino valem 1 ponto porque aparecem em projetos de
# todas as áreas ("ensino de química" é química); os assuntos valem 2.
_ASSUNTO = 2
_GENERICO = 1

_PALAVRAS = [
    # Ciências da Saúde
    (r"\bSAUDE\b", SAUDE), (r"\bSAUDAVE", SAUDE), (r"\bMEDIC", SAUDE), (r"\bENFERM", SAUDE), (r"\bODONTO", SAUDE),
    (r"\bFARMACIA\b", SAUDE), (r"\bFARMACEUT", SAUDE), (r"\bNUTRI", SAUDE), (r"\bFISIOTERAP", SAUDE),
    (r"\bFONOAUDIOLOG", SAUDE), (r"\bTERAPIA OCUPACIONAL", SAUDE), (r"\bPSIQUIATR", SAUDE), (r"\bHOSPITAL", SAUDE),
    (r"\bPACIENTE", SAUDE), (r"\bCLINIC", SAUDE), (r"\bDOENCA", SAUDE), (r"\bEPIDEMI", SAUDE), (r"\bENDEMI", SAUDE),
    (r"\bSUS\b", SAUDE), (r"\bATENCAO (BASICA|PRIMARIA)", SAUDE), (r"\bOBESIDADE", SAUDE), (r"\bDIABETES", SAUDE),
    (r"\bHIPERTENS", SAUDE), (r"\bCANCER", SAUDE), (r"\bTUBERCULOSE", SAUDE), (r"\bMALARIA", SAUDE),
    (r"\bDENGUE", SAUDE), (r"\bVACIN", SAUDE), (r"\bHANSEN", SAUDE), (r"\bHIV\b", SAUDE), (r"\bCOVID", SAUDE),
    (r"\bEDUCACAO FISICA", SAUDE), (r"\bESPORT", SAUDE), (r"\bATIVIDADE FISICA", SAUDE), (r"\bEXERCICIO", SAUDE),
    (r"\bREABILITA", SAUDE), (r"\bCIRURG", SAUDE), (r"\bGESTANTE", SAUDE), (r"\bMATERN", SAUDE),
    (r"\bNEONAT", SAUDE), (r"\bPEDIATR", SAUDE), (r"\bGERIATR", SAUDE), (r"\bBIOMEDIC", SAUDE),
    (r"\bTERAPEUT", SAUDE), (r"\bAMAMENTA", SAUDE),
    # Engenharias
    (r"\bENGENHARIA(?! (AGRICOLA|AGRONOMICA|FLORESTAL|DE ALIMENTOS|DE PESCA|DE SOFTWARE))", ENGENHARIAS),
    (r"\bENGENHEIR", ENGENHARIAS), (r"\bELETRIC", ENGENHARIAS), (r"\bELETRON", ENGENHARIAS),
    (r"\bMECANIC", ENGENHARIAS), (r"\bMECATRON", ENGENHARIAS), (r"\bROBOTIC", ENGENHARIAS),
    (r"\bAUTOMACAO", ENGENHARIAS), (r"\bAUTOMATIZ", ENGENHARIAS), (r"\bCONSTRUCAO CIVIL", ENGENHARIAS),
    (r"\bEDIFICA", ENGENHARIAS), (r"\bSANEAMENTO", ENGENHARIAS), (r"\bESGOTO", ENGENHARIAS),
    (r"\bRESIDUOS?\b", ENGENHARIAS), (r"\bHIDRAUL", ENGENHARIAS), (r"\bGEOTECN", ENGENHARIAS),
    (r"\bPAVIMENT", ENGENHARIAS), (r"\bMETALURG", ENGENHARIAS), (r"\bSOLDAGEM", ENGENHARIAS),
    (r"\bUSINAGEM", ENGENHARIAS), (r"\bMINERAC", ENGENHARIAS), (r"\bPETROL", ENGENHARIAS),
    (r"\bAERONAUT", ENGENHARIAS), (r"\bNAVAL\b", ENGENHARIAS), (r"\bTELECOMUNICA", ENGENHARIAS),
    (r"\bENERGI", ENGENHARIAS), (r"\bFOTOVOLTAIC", ENGENHARIAS), (r"\bMICROCONTROL", ENGENHARIAS),
    (r"\bARDUINO", ENGENHARIAS), (r"\bDRONE", ENGENHARIAS), (r"\bCIRCUITO", ENGENHARIAS), (r"\bSENSOR", ENGENHARIAS),
    (r"\bIMPRESS(AO|ORA) 3D", ENGENHARIAS), (r"\bPROTOTIP", ENGENHARIAS), (r"\bCONCRETO", ENGENHARIAS),
    # Linguística, Letras e Artes
    (r"\bLETRAS\b", LINGUISTICA), (r"\bLITERA", LINGUISTICA), (r"\bLINGUIST", LINGUISTICA),
    (r"\bLINGUAS?\b", LINGUISTICA), (r"\bLIBRAS\b", LINGUISTICA), (r"\bTRADUC", LINGUISTICA),
    (r"\bGRAMATIC", LINGUISTICA), (r"\bFONETIC", LINGUISTICA), (r"\bFONOLOG", LINGUISTICA),
    (r"\bARTES?\b", LINGUISTICA), (r"\bARTISTIC", LINGUISTICA), (r"\bMUSIC", LINGUISTICA), (r"\bTEATR", LINGUISTICA),
    (r"\bDANCA", LINGUISTICA), (r"\bCINEMA", LINGUISTICA), (r"\bCENIC", LINGUISTICA), (r"\bCENOGRAF", LINGUISTICA),
    (r"\bPOESIA", LINGUISTICA), (r"\bPOETIC", LINGUISTICA), (r"\bPOEMA", LINGUISTICA),
    (r"\bAUDIOVISUAL", LINGUISTICA), (r"\bFOTOGRAF", LINGUISTICA), (r"\bPINTURA", LINGUISTICA),
    (r"\bESCULTURA", LINGUISTICA), (r"\bESPETACUL", LINGUISTICA), (r"\bORQUESTR", LINGUISTICA),
    (r"\bVIOLAO", LINGUISTICA), (r"\bVIOLINO", LINGUISTICA), (r"\bPIANO\b", LINGUISTICA),
    (r"\bCANTO CORAL", LINGUISTICA), (r"\bDRAMATURG", LINGUISTICA), (r"\bESCRITA CRIATIVA", LINGUISTICA),
    # Ciências Sociais Aplicadas
    (r"\bDIREITOS?\b", SOCIAIS_APLICADAS), (r"\bJURIDIC", SOCIAIS_APLICADAS), (r"\bADVOCA", SOCIAIS_APLICADAS),
    (r"\bLEGISLA", SOCIAIS_APLICADAS), (r"\bPENAL\b", SOCIAIS_APLICADAS), (r"\bTRIBUT", SOCIAIS_APLICADAS),
    (r"\bADMINISTRA", SOCIAIS_APLICADAS), (r"\bEMPREENDEDOR", SOCIAIS_APLICADAS), (r"\bNEGOCIO", SOCIAIS_APLICADAS),
    (r"\bEMPRES", SOCIAIS_APLICADAS), (r"\bMARKETING", SOCIAIS_APLICADAS), (r"\bFINANCAS?\b", SOCIAIS_APLICADAS),
    (r"\bFINANCEIR", SOCIAIS_APLICADAS), (r"\bCONTAB", SOCIAIS_APLICADAS), (r"\bECONOM", SOCIAIS_APLICADAS),
    (r"\bMERCADO", SOCIAIS_APLICADAS), (r"\bCOOPERATIV", SOCIAIS_APLICADAS), (r"\bLOGISTIC", SOCIAIS_APLICADAS),
    (r"\bCOMUNICACAO\b", SOCIAIS_APLICADAS), (r"\bJORNALIS", SOCIAIS_APLICADAS), (r"\bPUBLICIDADE", SOCIAIS_APLICADAS),
    (r"\bPROPAGANDA", SOCIAIS_APLICADAS), (r"\bMIDIA", SOCIAIS_APLICADAS), (r"\bRADIO\b", SOCIAIS_APLICADAS),
    (r"\bPODCAST", SOCIAIS_APLICADAS), (r"\bARQUITET", SOCIAIS_APLICADAS), (r"\bURBANIS", SOCIAIS_APLICADAS),
    (r"\bURBANIZA", SOCIAIS_APLICADAS), (r"\bPLANEJAMENTO URBANO", SOCIAIS_APLICADAS), (r"\bTURISM", SOCIAIS_APLICADAS),
    (r"\bBIBLIOTEC", SOCIAIS_APLICADAS), (r"\bARQUIVOL", SOCIAIS_APLICADAS), (r"\bMUSEOLOG", SOCIAIS_APLICADAS),
    (r"\bSERVICO SOCIAL", SOCIAIS_APLICADAS), (r"\bASSISTEN(CIA|TE) SOCIAL", SOCIAIS_APLICADAS),
    (r"\bCONSUMIDOR", SOCIAIS_APLICADAS), (r"\bCIENCIA DA INFORMACAO", SOCIAIS_APLICADAS),
    # Ciências Humanas
    (r"\bHISTORIA\b", HUMANAS), (r"\bHISTORIOGRAF", HUMANAS), (r"\bGEOGRAF", HUMANAS), (r"\bFILOSOF", HUMANAS),
    (r"\bPSIC", HUMANAS), (r"\bPEDAGOG", HUMANAS), (r"\bSOCIOLOG", HUMANAS), (r"\bANTROPOLOG", HUMANAS),
    (r"\bARQUEOLOG", HUMANAS), (r"\bETNOGRAF", HUMANAS), (r"\bETNIC", HUMANAS), (r"\bINDIGEN", HUMANAS),
    (r"\bQUILOMB", HUMANAS), (r"\bDECOLONIAL", HUMANAS), (r"\bPOS[- ]COLONIAL", HUMANAS), (r"\bTEOLOG", HUMANAS),
    (r"\bRELIGI", HUMANAS), (r"\bCOGNI", HUMANAS), (r"\bPATRIMONIO (HISTORICO|CULTURAL)", HUMANAS),
    (r"\bFEMINIS", HUMANAS), (r"\bRACIAL", HUMANAS), (r"\bRACISMO", HUMANAS), (r"\bCIDADANIA", HUMANAS),
    (r"\bGEOPOLITIC", HUMANAS), (r"\bMOVIMENTOS SOCIAIS", HUMANAS),
    (r"\bEDUCA", HUMANAS, _GENERICO), (r"\bENSINO", HUMANAS, _GENERICO), (r"\bAPRENDIZAGEM", HUMANAS, _GENERICO),
    (r"\bESCOLA", HUMANAS, _GENERICO), (r"\bDOCEN", HUMANAS, _GENERICO), (r"\bPROFESSOR", HUMANAS, _GENERICO),
    (r"\bALFABETIZ", HUMANAS, _GENERICO), (r"\bLETRAMENTO", HUMANAS, _GENERICO), (r"\bCURRICUL", HUMANAS, _GENERICO),
    (r"\bDIDATIC", HUMANAS, _GENERICO), (r"\bLICENCIATURA", HUMANAS, _GENERICO), (r"\bPIBID\b", HUMANAS, _GENERICO),
    (r"\bMAGISTERIO", HUMANAS, _GENERICO),
    # Ciências Agrárias
    (r"\bAGR(I|O|ARI)", AGRARIAS), (r"\bVETERINAR", AGRARIAS), (r"\bZOOTECN", AGRARIAS), (r"\bFLOREST", AGRARIAS),
    (r"\bSILVICULT", AGRARIAS), (r"\bMADEIR", AGRARIAS), (r"\bALIMENTOS?\b", AGRARIAS), (r"\bPESCA\b", AGRARIAS),
    (r"\bPESQUEIR", AGRARIAS), (r"\bAQUICULT", AGRARIAS), (r"\bPISCICULT", AGRARIAS), (r"\bPECUARI", AGRARIAS),
    (r"\bBOVIN", AGRARIAS), (r"\bSUIN", AGRARIAS), (r"\bAVICULT", AGRARIAS), (r"\bGADO\b", AGRARIAS),
    (r"\bPOMAR", AGRARIAS), (r"\bHORTA", AGRARIAS), (r"\bHORTICULT", AGRARIAS), (r"\bFRUTICULT", AGRARIAS),
    (r"\bOLERICULT", AGRARIAS), (r"\bCULTIVO", AGRARIAS), (r"\bCULTIVAR", AGRARIAS), (r"\bPLANTIO", AGRARIAS),
    (r"\bSEMENTE", AGRARIAS), (r"\bSOLOS?\b", AGRARIAS), (r"\bIRRIGA", AGRARIAS), (r"\bADUBA", AGRARIAS),
    (r"\bFERTILIZ", AGRARIAS), (r"\bPRAGAS?\b", AGRARIAS), (r"\bCACAU", AGRARIAS), (r"\bSOJA\b", AGRARIAS),
    (r"\bMILHO", AGRARIAS), (r"\bMANDIOCA", AGRARIAS), (r"\bFEIJAO", AGRARIAS), (r"\bCAFEICULT", AGRARIAS),
    (r"\bAPICULT", AGRARIAS), (r"\bRURA(L|IS)\b", AGRARIAS), (r"\bPASTAGE", AGRARIAS), (r"\bREBANHO", AGRARIAS),
    (r"\bLATICIN", AGRARIAS), (r"\bCOLHEITA", AGRARIAS), (r"\bSAFRA", AGRARIAS),
    # Ciências Biológicas
    (r"\bBIOLOG", BIOLOGICAS), (r"\bBIOQUIM", BIOLOGICAS), (r"\bGENETIC", BIOLOGICAS), (r"\bGENOM", BIOLOGICAS),
    (r"\bECOLOG", BIOLOGICAS), (r"\bECOSSISTEM", BIOLOGICAS), (r"\bMICROBIO", BIOLOGICAS), (r"\bBACTERI", BIOLOGICAS),
    (r"\bVIRUS\b", BIOLOGICAS), (r"\bVIROLOG", BIOLOGICAS), (r"\bFUNGO", BIOLOGICAS), (r"\bMICOLOG", BIOLOGICAS),
    (r"\bPARASIT", BIOLOGICAS), (r"\bFARMACOLOG", BIOLOGICAS), (r"\bFISIOLOG", BIOLOGICAS), (r"\bBOTANIC", BIOLOGICAS),
    (r"\bZOOLOG", BIOLOGICAS), (r"\bFAUNA", BIOLOGICAS), (r"\bFLORA\b", BIOLOGICAS), (r"\bBIODIVERS", BIOLOGICAS),
    (r"\bESPECIES?\b", BIOLOGICAS), (r"\bENTOMOLOG", BIOLOGICAS), (r"\bINSETO", BIOLOGICAS), (r"\bAVES\b", BIOLOGICAS),
    (r"\bPRIMATA", BIOLOGICAS), (r"\bMAMIFER", BIOLOGICAS), (r"\bANFIBI", BIOLOGICAS), (r"\bREPTEIS", BIOLOGICAS),
    (r"\bSERPENTE", BIOLOGICAS), (r"\bMOLECULAR", BIOLOGICAS), (r"\bCELULAS?\b", BIOLOGICAS), (r"\bPROTEIN", BIOLOGICAS),
    (r"\bENZIM", BIOLOGICAS), (r"\bDNA\b", BIOLOGICAS), (r"\bIMUNOLOG", BIOLOGICAS), (r"\bANATOM", BIOLOGICAS),
    (r"\bHISTOLOG", BIOLOGICAS), (r"\bEMBRIOLOG", BIOLOGICAS), (r"\bEVOLUTIV", BIOLOGICAS), (r"\bHERBARIO", BIOLOGICAS),
    (r"\bMANGUE", BIOLOGICAS), (r"\bUNIDADES? DE CONSERVACAO", BIOLOGICAS), (r"\bPLANCTON", BIOLOGICAS),
    (r"\bMICROR?ORGANISM", BIOLOGICAS), (r"\bNEUROCIENC", BIOLOGICAS),
    # Ciências Exatas e da Terra
    (r"\bMATEMATIC", EXATAS), (r"(?<!EDUCACAO )(?<!ATIVIDADE )(?<!APTIDAO )\bFISICA\b", EXATAS),
    (r"\bASTROFISIC", EXATAS), (r"\bGEOFISIC", EXATAS), (r"\bQUIMIC", EXATAS), (r"\bCOMPUTAC", EXATAS),
    (r"\bCOMPUTADOR", EXATAS), (r"\bINFORMATIC", EXATAS), (r"\bSOFTWARE", EXATAS), (r"\bPROGRAMACAO", EXATAS),
    (r"\bALGORITM", EXATAS), (r"\bINTELIGENCIA ARTIFICIAL", EXATAS), (r"\bAPRENDIZADO DE MAQUINA", EXATAS),
    (r"\bCIENCIA DE DADOS", EXATAS), (r"\bBANCO DE DADOS", EXATAS), (r"\bSISTEMAS? DE INFORMACAO", EXATAS),
    (r"\bTECNOLOGIA DA INFORMACAO", EXATAS), (r"\bAPLICATIVO", EXATAS), (r"\bCRIPTOGRAF", EXATAS),
    (r"\bESTATISTIC", EXATAS), (r"\bPROBABILI", EXATAS), (r"\bGEOCIENC", EXATAS), (r"\bGEOLOG", EXATAS),
    (r"\bOCEANOGRAF", EXATAS), (r"\bASTRONOM", EXATAS), (r"\bMETEOROLOG", EXATAS), (r"\bCLIMAT", EXATAS),
    (r"\bATMOSFER", EXATAS), (r"\bEOLIC", EXATAS), (r"\bMINERAL", EXATAS), (r"\bHIDROLOG", EXATAS),
    (r"\bGEOPROCESS", EXATAS), (r"\bGEOTECNOLOG", EXATAS), (r"\bSENSORIAMENTO REMOTO", EXATAS),
    (r"\bCARTOGRAF", EXATAS), (r"\bCALCULO\b", EXATAS), (r"\bGEOMETRI", EXATAS), (r"\bALGEBR", EXATAS),
    (r"\bEQUACO", EXATAS), (r"\bPALEONTOLOG", EXATAS), (r"\bSISMO", EXATAS),
    # Multidisciplinar (quando o próprio texto se declara assim)
    (r"\bINTERDISCIPLINAR", MULTIDISCIPLINAR), (r"\bMULTIDISCIPLINAR", MULTIDISCIPLINAR),
    (r"\bTRANSDISCIPLINAR", MULTIDISCIPLINAR), (r"\bBIOTECNOLOG", MULTIDISCIPLINAR),
    (r"\bNANOTECNOLOG", MULTIDISCIPLINAR), (r"\bDIVULGACAO CIENTIFICA", MULTIDISCIPLINAR),
    (r"\bCIENCIAS AMBIENTAIS", MULTIDISCIPLINAR), (r"\bDESENVOLVIMENTO SUSTENTAVEL", MULTIDISCIPLINAR),
]
_PALAVRAS = [(re.compile(e[0]), e[1], e[2] if len(e) > 2 else _ASSUNTO) for e in _PALAVRAS]

_POSICAO_AREA = {area: i for i, area in enumerate(AREAS_CONHECIMENTO)}


def _texto(*partes: Any) -> str:
    """Junta campos (texto ou lista de textos) num único texto normalizado."""
    pedacos: list[str] = []
    for parte in partes:
        if isinstance(parte, (list, tuple)):
            pedacos.extend(str(p) for p in parte if p)
        elif parte:
            pedacos.append(str(parte))
    return normalizar(" | ".join(pedacos))


def _pontuar(textos: Iterable[tuple[str, int]]) -> Optional[str]:
    """Área com mais pontos nos textos dados (cada um com seu multiplicador).
    Cada palavra-chave conta uma vez, pelo maior peso em que apareceu. Em
    empate vence a que aparece primeiro no texto e, persistindo, a primeira
    na ordem da tabela."""
    pontos: dict[str, int] = {}
    primeira: dict[str, int] = {}
    deslocamento = 0
    for texto, multiplicador in textos:
        if not texto:
            continue
        for padrao, area, peso in _PALAVRAS:
            m = padrao.search(texto)
            if m is None:
                continue
            pontos[area] = pontos.get(area, 0) + peso * multiplicador
            posicao = deslocamento + m.start()
            primeira[area] = min(primeira.get(area, posicao), posicao)
        deslocamento += len(texto) + 1
    if not pontos:
        return None
    return min(pontos, key=lambda a: (-pontos[a], primeira[a], _POSICAO_AREA[a]))


def classificar_area(doc: dict) -> str:
    """Grande área do CNPq de um documento da collection `projetos` (ou de um
    registro com os mesmos nomes de campo). Nunca devolve None: na falta de
    pistas, "Multidisciplinar"."""
    for campo in ("area_cnpq", "area_tematica", "area_estudo"):
        area = area_valida(doc.get(campo))
        if area:
            return area

    area = _area_por_unidade(doc.get("unidade"))
    if area:
        return area

    fortes = _texto(doc.get("titulo"), doc.get("area_tematica"), doc.get("palavras_chave"),
                    doc.get("area_estudo"), doc.get("grupo_pesquisa"))
    descricao = _texto(doc.get("descricao"))
    return _pontuar([(fortes, 2), (descricao, 1)]) or MULTIDISCIPLINAR


# ─────────────────────────────────────────────
#  Migração
# ─────────────────────────────────────────────

async def garantir_area_conhecimento(db, tamanho_lote: int = 500) -> int:
    """Preenche `area_conhecimento` nos projetos que ainda não têm o campo
    (ou o têm nulo), em lotes, sem carregar a collection inteira na memória.
    Idempotente: na segunda execução não há o que preencher. Roda no startup
    da API (`migrar_dados`). Devolve quantos documentos foram preenchidos."""
    filtro = {"area_conhecimento": None}  # casa o campo ausente e o campo nulo
    projecao = {campo: 1 for campo in CAMPOS_CLASSIFICACAO}
    total = 0
    while True:
        lote = await db.projetos.find(filtro, projecao).limit(tamanho_lote).to_list(tamanho_lote)
        if not lote:
            return total
        por_area: dict[str, list] = {}
        for doc in lote:
            por_area.setdefault(classificar_area(doc), []).append(doc["_id"])
        modificados = 0
        for area, ids in por_area.items():
            resultado = await db.projetos.update_many({"_id": {"$in": ids}}, {"$set": {"area_conhecimento": area}})
            modificados += resultado.modified_count
        total += modificados
        if modificados == 0:
            # Nada mudou neste lote: sair evita um laço sem fim caso o banco recuse a escrita.
            return total
