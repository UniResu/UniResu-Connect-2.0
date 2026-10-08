"""
Seed do fórum: perguntas frequentes da vida acadêmica, publicadas pelo
usuário de sistema "Equipe UniResu" (@uniresu).

Cada pergunta traz no próprio corpo um texto que funciona como entrada de
FAQ: o estudante que chega com a mesma dúvida já sai com a resposta, sem
depender das respostas que a comunidade publicar depois.

Idempotente: cada tópico leva `seed: "forum_v1"` e uma `seed_chave` estável;
só entram os que ainda não existem. Tópicos já gravados nunca são
sobrescritos (edições feitas pela equipe ficam). Um tópico do seed apagado
do banco volta no próximo startup; para removê-lo de vez, tire-o também de
`PERGUNTAS`.

Roda no startup da API (`migrar_dados`, em database/indexes.py) e pode ser
executado manualmente, a partir de backend/:

    python -m jobs.seed_forum
"""

import asyncio
import sys
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

from dotenv import load_dotenv
from pymongo.errors import DuplicateKeyError

SEED_VERSAO = "forum_v1"

# Conta que assina as perguntas. Sem `senha_hash` não há login por senha, e a
# recuperação de senha ignora contas sem hash; `sistema: True` marca a conta
# para qualquer tela administrativa futura.
USUARIO_SISTEMA: Dict[str, Any] = {
    "email": "forum@uniresu.org",
    "username": "uniresu",
    "nome": "Equipe UniResu",
    "papel": "professor",
    "sistema": True,
    "ativo": True,
    "instituicao": "UniResu Connect",
    "bio": "Conta oficial da equipe. Publica no fórum perguntas frequentes sobre pesquisa e extensão.",
    "interesses": [],
    "habilidades": [],
    "dados_professor": {"linhas_pesquisa": []},
}

# `dias_atras`/`hora`: deslocamentos fixos em relação ao momento da execução,
# espalhando as perguntas pelos últimos 60 dias (a mais antiga primeiro).
PERGUNTAS: List[Dict[str, Any]] = [
    {
        "seed_chave": "encontrar-projeto-iniciacao-cientifica",
        "dias_atras": 58, "hora": 9,
        "titulo": "Como encontro um projeto de pesquisa para participar (iniciação científica)?",
        "conteudo": (
            "Comece pela aba Projetos Acadêmicos aqui na plataforma: ela reúne os projetos de pesquisa e "
            "extensão em andamento coletados dos portais públicos das universidades, além dos cadastrados pelos "
            "próprios professores. Filtre por módulo (pesquisa), instituição, campus e unidade, leia o resumo e "
            "veja quem coordena. Se o projeto tiver contato, dá para se candidatar ali mesmo com uma carta de "
            "intenção.\n\n"
            "Fora da plataforma, os caminhos clássicos são: perguntar aos professores das disciplinas de que você "
            "mais gosta se eles orientam iniciação científica, olhar o Currículo Lattes deles (a seção de projetos "
            "mostra o que está ativo), consultar o Diretório dos Grupos de Pesquisa do CNPq pela sua instituição e "
            "acompanhar os editais de PIBIC/PIBITI da pró-reitoria de pesquisa, que normalmente saem uma vez por ano.\n\n"
            "Não precisa esperar bolsa para começar. Muitos projetos aceitam estudantes voluntários (a chamada "
            "iniciação científica voluntária), e a experiência conta no currículo do mesmo jeito: "
            "você recebe orientação, participa das reuniões do grupo e pode apresentar resultados em eventos.\n\n"
            "Dica prática: procure projetos ligados a disciplinas em que você foi bem e que tenham a ver com o que "
            "quer fazer depois da graduação. Um professor nota rapidamente quem leu o resumo do projeto antes de "
            "procurá-lo."
        ),
    },
    {
        "seed_chave": "carta-de-intencao",
        "dias_atras": 55, "hora": 14,
        "titulo": "Como escrever uma carta de intenção para o(a) coordenador(a) de um projeto?",
        "conteudo": (
            "Uma boa carta de intenção é curta (três parágrafos bastam, algo entre 300 e 600 palavras) e responde "
            "a três perguntas, nesta ordem: quem é você, por que este projeto e qual é a sua disponibilidade.\n\n"
            "No primeiro parágrafo, diga curso, período e o que você já estudou ou fez que tenha relação com o tema: "
            "uma disciplina, um trabalho, uma monitoria, um curso livre. No segundo, mostre que leu sobre o projeto: "
            "cite o que chamou sua atenção no resumo e como você pode contribuir (uma habilidade concreta vale mais "
            "que adjetivos). No terceiro, informe quantas horas por semana pode dedicar, em quais turnos e a partir "
            "de quando.\n\n"
            "Evite textos genéricos que serviriam para qualquer projeto, superlativos e pedidos de desculpas pela "
            "falta de experiência: todo mundo começa sem experiência, é exatamente por isso que existe a iniciação "
            "científica. Revise ortografia e concordância antes de enviar e, se tiver, inclua o link do seu Lattes.\n\n"
            "Na UniResu, o formulário de candidatura já segue essa estrutura: a carta vai no corpo do e-mail que "
            "o(a) coordenador(a) recebe, com o seu e-mail no campo de resposta e o Lattes como link no final."
        ),
    },
    {
        "seed_chave": "pesquisa-vs-extensao-curricularizacao",
        "dias_atras": 51, "hora": 11,
        "titulo": "Qual é a diferença entre pesquisa e extensão, e por que a extensão agora conta no currículo?",
        "conteudo": (
            "Pesquisa é a produção de conhecimento novo: um projeto parte de uma pergunta, aplica um método e chega "
            "a resultados que podem ser publicados. Extensão é a relação da universidade com a sociedade: cursos, "
            "oficinas, atendimentos, assessorias e eventos que levam o conhecimento acadêmico para fora dos muros (e "
            "trazem de volta demandas reais). Ensino, pesquisa e extensão são os três pilares da universidade "
            "brasileira, e a Constituição exige que sejam indissociáveis.\n\n"
            "A novidade dos últimos anos é a chamada curricularização da extensão. A Resolução CNE/CES nº 7, de 2018, "
            "determina que pelo menos 10% da carga horária total de cada curso de graduação seja cumprida em "
            "atividades de extensão, com o estudante como protagonista. Por isso os projetos de extensão aparecem com "
            "destaque na UniResu: participar deles não é mais só atividade complementar, é parte obrigatória da "
            "formação na maioria dos currículos novos.\n\n"
            "Na prática: verifique no projeto pedagógico do seu curso como as horas de extensão são registradas "
            "(algumas instituições criam componentes curriculares específicos, outras aceitam certificados de "
            "projetos cadastrados na pró-reitoria). Guarde os certificados e declarações de participação, com carga "
            "horária e período, e confirme com a coordenação do curso o que precisa ser entregue."
        ),
    },
    {
        "seed_chave": "curriculo-lattes",
        "dias_atras": 47, "hora": 16,
        "titulo": "O que é o Currículo Lattes e como mantê-lo atualizado?",
        "conteudo": (
            "O Currículo Lattes é o currículo acadêmico padrão do Brasil, mantido pelo CNPq na Plataforma Lattes "
            "(lattes.cnpq.br). É gratuito, público e praticamente obrigatório: editais de bolsa, seleções de "
            "pós-graduação, eventos e muitos processos seletivos pedem o link do seu Lattes, e o professor que recebe "
            "sua candidatura costuma abri-lo antes de responder.\n\n"
            "Para criar, acesse a plataforma, faça o cadastro com CPF e preencha pelo menos: dados pessoais, formação "
            "(graduação em andamento, com previsão de conclusão), idiomas e atuação profissional, se houver. Depois "
            "vão entrando os itens que fazem diferença: participação em projetos de pesquisa e extensão (com o nome "
            "do(a) coordenador(a) e o período), monitoria, resumos apresentados em eventos, cursos de curta duração, "
            "prêmios e organização de eventos.\n\n"
            "Atualize assim que algo acontecer, não na véspera de um edital. Um bom hábito é abrir o Lattes no fim de "
            "cada semestre e conferir se tudo que você fez no período está lá. Depois de editar, clique em Enviar ao "
            "CNPq, senão as mudanças ficam só no rascunho. Não invente nem infle itens: o Lattes é público e as "
            "informações são checadas em seleções.\n\n"
            "Vincule também o seu ORCID ao Lattes (há um campo para isso em Dados pessoais). As duas plataformas se "
            "complementam, e cada vez mais editais pedem os dois identificadores."
        ),
    },
    {
        "seed_chave": "o-que-e-orcid",
        "dias_atras": 44, "hora": 10,
        "titulo": "O que é ORCID e por que vale a pena criar o meu ainda na graduação?",
        "conteudo": (
            "ORCID (Open Researcher and Contributor ID) é um identificador único e permanente de pesquisador, no "
            "formato 0000-0002-1825-0097, mantido por uma organização sem fins lucrativos. Ele resolve um problema "
            "simples: nomes se repetem, mudam com casamento e são abreviados de formas diferentes em cada revista. "
            "Com o ORCID, suas publicações, projetos e vínculos ficam ligados a você, e não a uma grafia do seu nome.\n\n"
            "Criar leva poucos minutos em orcid.org e é gratuito. Preencha nome, instituição e, se quiser, uma "
            "biografia curta. Você controla a visibilidade de cada item (público, só para instituições de confiança "
            "ou privado). Revistas científicas, agências de fomento e repositórios pedem o ORCID na submissão de "
            "artigos e em relatórios, e muitos preenchem o seu registro automaticamente quando o trabalho é "
            "publicado.\n\n"
            "Para quem está começando, o ORCID funciona como um portfólio acadêmico internacional que cresce com "
            "você. Vincule-o ao seu Currículo Lattes e, aqui na UniResu, você pode entrar com o ORCID e importar suas "
            "publicações para o perfil público."
        ),
    },
    {
        "seed_chave": "bolsas-iniciacao-cientifica",
        "dias_atras": 40, "hora": 8,
        "titulo": "Como funcionam as bolsas de iniciação científica (CNPq, FAPs e editais internos)?",
        "conteudo": (
            "A maior parte das bolsas de iniciação científica vem de programas do CNPq, que distribui cotas anuais "
            "às universidades: PIBIC (pesquisa), PIBITI (desenvolvimento tecnológico e inovação) e PIBIC-Af (ações "
            "afirmativas). As fundações estaduais de amparo à pesquisa, as FAPs (cada estado tem a sua), também "
            "financiam cotas, e as próprias instituições costumam manter bolsas com recursos próprios.\n\n"
            "Quem distribui essas cotas é a pró-reitoria de pesquisa da sua universidade (PROPESQ, PRPPG ou nome "
            "equivalente), por meio de um edital interno, normalmente anual e publicado no primeiro semestre. Quem "
            "se inscreve é o(a) professor(a) orientador(a), com um plano de trabalho para o estudante; por isso o "
            "primeiro passo é ter um orientador e um projeto. O edital define os requisitos do bolsista: estar "
            "regularmente matriculado, ter Lattes atualizado, não acumular outra bolsa (auxílios de permanência em "
            "geral são permitidos, confira) e cumprir a dedicação prevista.\n\n"
            "O valor da bolsa é definido pela agência e reajustado de tempos em tempos; consulte a tabela vigente do "
            "CNPq ou da FAP. A vigência costuma ser de 12 meses, com relatório parcial e relatório final obrigatórios "
            "e apresentação dos resultados no seminário ou congresso de iniciação científica da instituição. Não "
            "entregar o relatório pode bloquear futuras bolsas para você e para o orientador.\n\n"
            "Se o seu plano não for contemplado, ele normalmente pode seguir como iniciação científica voluntária, "
            "com o mesmo acompanhamento e certificação, e pode concorrer de novo no edital seguinte."
        ),
    },
    {
        "seed_chave": "comite-de-etica-plataforma-brasil",
        "dias_atras": 36, "hora": 15,
        "titulo": "Minha pesquisa envolve pessoas. O que são o Comitê de Ética e a Plataforma Brasil?",
        "conteudo": (
            "Toda pesquisa que envolve seres humanos, direta ou indiretamente (entrevistas, questionários, "
            "observação, dados de prontuário, material biológico), precisa ser aprovada por um Comitê de Ética em "
            "Pesquisa (CEP) antes de começar a coleta de dados. Os CEPs integram o sistema CEP/CONEP do Conselho "
            "Nacional de Saúde, e as regras principais estão na Resolução CNS nº 466/2012 (área da saúde) e na "
            "Resolução CNS nº 510/2016 (ciências humanas e sociais).\n\n"
            "A Plataforma Brasil (plataformabrasil.saude.gov.br) é o sistema em que o projeto é cadastrado e "
            "acompanhado. Quem submete é o(a) pesquisador(a) responsável, em geral o orientador, mas o estudante "
            "costuma preparar os documentos: projeto detalhado, folha de rosto assinada, Termo de Consentimento Livre "
            "e Esclarecido (TCLE) em linguagem acessível, instrumentos de coleta (roteiro, questionário), cronograma, "
            "orçamento e termo de anuência da instituição onde a pesquisa acontece.\n\n"
            "Conte com prazo. Entre a submissão e o parecer final costumam passar várias semanas, e é comum o CEP "
            "pedir ajustes (pendências) antes de aprovar. Quando aprovado, o projeto recebe um número de CAAE, que "
            "deve constar nos artigos e resumos. Dados coletados antes da aprovação não podem ser usados e podem "
            "levar à recusa do trabalho por revistas e eventos.\n\n"
            "Pesquisas só com dados públicos, agregados e sem identificação (bases do IBGE, por exemplo) e revisões "
            "de literatura em geral não precisam passar pelo CEP, mas a resolução lista as exceções: na dúvida, "
            "pergunte ao CEP da sua instituição antes de começar."
        ),
    },
    {
        "seed_chave": "como-ler-artigo-cientifico",
        "dias_atras": 31, "hora": 20,
        "titulo": "Como ler um artigo científico sem levar um dia inteiro?",
        "conteudo": (
            "Artigo científico não se lê como texto corrido, do começo ao fim. A leitura eficiente é em passadas: "
            "primeiro título, resumo e palavras-chave, para decidir se vale continuar; depois figuras, tabelas e a "
            "conclusão, que concentram o resultado; só então a introdução (para entender a pergunta e o que já se "
            "sabia) e, por último, o método e a discussão, quando você realmente precisa saber como chegaram ali.\n\n"
            "Leia com uma pergunta na cabeça: o que este artigo precisa me dizer para o meu trabalho? Anote em uma ou "
            "duas frases a pergunta do estudo, o método, o principal resultado e uma limitação. Esse fichamento curto "
            "vale muito mais do que marcar o PDF inteiro de amarelo, e vira o rascunho da sua revisão de literatura.\n\n"
            "Use um gerenciador de referências desde o primeiro artigo (Zotero e Mendeley são gratuitos): ele guarda "
            "o PDF, as anotações e gera as citações no formato pedido. Para encontrar textos, além do Google "
            "Acadêmico, use o Portal de Periódicos da CAPES pelo acesso da sua instituição, a SciELO e as bases da "
            "sua área.\n\n"
            "Boa parte da literatura está em inglês. Ler devagar no começo é normal; o vocabulário técnico de uma "
            "área se repete e em poucos meses a leitura acelera. Peça ao orientador os três artigos mais importantes "
            "do tema e comece por eles."
        ),
    },
    {
        "seed_chave": "como-escolher-orientador",
        "dias_atras": 27, "hora": 12,
        "titulo": "Como escolher um(a) orientador(a)?",
        "conteudo": (
            "Orientador bom não é o mais famoso, é o que combina com você em três pontos: tema, disponibilidade e "
            "estilo de trabalho. Comece pelo tema: leia o Lattes dos professores do seu curso e veja o que eles "
            "pesquisam de fato hoje (projetos em andamento, publicações recentes), não só o título da disciplina que "
            "dão.\n\n"
            "Depois, converse com quem já é orientado por eles. Pergunte com que frequência há reuniões, se o "
            "professor lê e devolve os textos com comentários, como lida com prazos e se os estudantes apresentam "
            "trabalhos em eventos. Um grupo de pesquisa ativo, com reuniões regulares, costuma ser melhor para quem "
            "está começando do que uma orientação individual com encontros raros.\n\n"
            "Na primeira conversa, vá com objetividade: diga o que te interessa, o que já estudou e quanto tempo tem "
            "por semana, e pergunte que tipo de trabalho um aluno de iniciação faria no grupo. Está tudo bem ouvir "
            "não (o professor pode estar sem vagas ou sem bolsa) e está tudo bem você decidir que não é o lugar "
            "certo. Mudar de orientador depois é possível, mas é melhor acertar antes.\n\n"
            "Um sinal de bom orientador é explicar com clareza o que espera de você e o que você pode esperar dele. "
            "Combine isso por escrito, nem que seja um e-mail: horas, reuniões, entregas."
        ),
    },
    {
        "seed_chave": "monitoria-ou-iniciacao-cientifica",
        "dias_atras": 22, "hora": 9,
        "titulo": "Monitoria ou iniciação científica: qual escolher?",
        "conteudo": (
            "São atividades diferentes, com objetivos diferentes. A monitoria é ligada ao ensino: você auxilia o "
            "professor em uma disciplina que já cursou, tira dúvidas dos colegas, ajuda em laboratório e em correções "
            "simples. A iniciação científica é ligada à pesquisa: você entra em um projeto, aprende um método, coleta "
            "e analisa dados e escreve resultados sob orientação.\n\n"
            "Se você pensa em dar aula ou gosta de explicar, a monitoria é um ótimo começo e ajuda a consolidar o "
            "conteúdo. Se pensa em pós-graduação (mestrado e doutorado) ou em trabalhar com pesquisa e "
            "desenvolvimento, a iniciação científica pesa mais: é ela que gera resumos em eventos, artigos e a carta "
            "de recomendação de um orientador que conhece o seu trabalho.\n\n"
            "Dá para fazer as duas, em semestres diferentes ou até ao mesmo tempo, desde que a carga horária total "
            "caiba na sua semana (veja se as duas bolsas podem ser acumuladas; em geral, não podem). As duas contam "
            "como atividades complementares e entram no Lattes. O que não vale a pena é assumir tudo e fazer mal "
            "feito: os professores conversam entre si, e a reputação de quem cumpre o combinado vale mais do que uma "
            "linha a mais no currículo."
        ),
    },
    {
        "seed_chave": "submeter-resumo-evento-cientifico",
        "dias_atras": 18, "hora": 17,
        "titulo": "Como submeter um resumo para um evento científico?",
        "conteudo": (
            "O primeiro evento de quase todo estudante é o seminário ou congresso de iniciação científica da própria "
            "universidade, que costuma ser obrigatório para bolsistas e aberto a voluntários. Depois vêm os eventos "
            "regionais e nacionais da sua área (congressos de sociedades científicas, a Reunião Anual da SBPC, "
            "jornadas acadêmicas), divulgados pelas sociedades, pelos grupos de pesquisa e pelos próprios "
            "professores.\n\n"
            "Leia a chamada de trabalhos com atenção: ela define o prazo, o número máximo de palavras, a estrutura "
            "exigida e o formato de apresentação (pôster ou comunicação oral). Um resumo típico tem introdução (o "
            "problema e por que importa), objetivo, método, resultados (mesmo parciais, com números quando houver) e "
            "conclusão, mais três a cinco palavras-chave. Não prometa resultados que ainda não tem; resumo com "
            "resultados preliminares é normal em iniciação científica.\n\n"
            "O texto é escrito com o orientador, que entra como coautor e aprova a versão final antes do envio. "
            "Confira as regras de autoria do evento e da sua instituição e, se a pesquisa envolve pessoas, inclua o "
            "número do CAAE. Depois do aceite, prepare a apresentação com antecedência e ensaie: quem avalia pôsteres "
            "gosta de quem explica o trabalho em dois minutos e responde com honestidade ao que não sabe.\n\n"
            "Guarde o certificado de apresentação e o resumo publicado nos anais: ambos entram no Lattes e contam "
            "como atividade complementar."
        ),
    },
    {
        "seed_chave": "primeiro-artigo-revistas-predatorias",
        "dias_atras": 13, "hora": 11,
        "titulo": "Vou publicar meu primeiro artigo. Como escolho a revista e evito as predatórias?",
        "conteudo": (
            "Escolha a revista pelo escopo, não pelo nome: leia a seção de foco e escopo e veja se os artigos "
            "publicados ali nos últimos anos se parecem com o seu em tema e método. Depois confira a avaliação da "
            "revista na sua área pelo Qualis Periódicos, na Plataforma Sucupira da CAPES, e se ela está indexada em "
            "bases reconhecidas (SciELO, Scopus, Web of Science, DOAJ para revistas de acesso aberto). Converse com o "
            "orientador: ele conhece as revistas em que o grupo publica e quais têm revisão séria.\n\n"
            "Revistas predatórias cobram para publicar sem oferecer revisão por pares de verdade. Sinais de alerta: "
            "convites insistentes por e-mail elogiando um trabalho que você apresentou, promessa de aceite em poucos "
            "dias, taxas que só aparecem depois do aceite, fator de impacto inventado ou de empresas desconhecidas, "
            "escopo que mistura todas as áreas, site com erros grosseiros e conselho editorial sem instituições "
            "verificáveis. A iniciativa Think. Check. Submit. (thinkchecksubmit.org) tem uma lista de verificação "
            "simples para isso.\n\n"
            "Publicar em uma revista predatória pode custar caro, no sentido literal e no acadêmico: o artigo não "
            "conta em avaliações e fica difícil republicar o mesmo resultado em uma revista séria. Se a pesquisa "
            "ainda é pequena, um resumo expandido nos anais de um bom evento ou uma revista de iniciação científica "
            "da sua instituição são caminhos melhores para começar.\n\n"
            "Antes de submeter, siga as normas para autores da revista à risca (formato, número de palavras, estilo "
            "de citação) e prepare uma carta de apresentação curta. E lembre: a revisão por pares demora meses e "
            "quase sempre pede ajustes; isso é sinal de que a revista está funcionando."
        ),
    },
    {
        "seed_chave": "conciliar-horas-do-projeto-com-aulas",
        "dias_atras": 9, "hora": 19,
        "titulo": "Como conciliar as horas do projeto com as aulas e o resto da vida?",
        "conteudo": (
            "Antes de aceitar um projeto, faça as contas com honestidade: some as horas de aula, deslocamento, estudo "
            "e trabalho (se houver) e veja quanto sobra de verdade. Os editais de iniciação científica costumam "
            "prever uma carga semanal de dedicação; confira a do seu e não prometa mais do que isso só para "
            "impressionar.\n\n"
            "Fixe blocos na agenda para o projeto, de preferência nos mesmos dias e horários toda semana, e trate-os "
            "como aula. Dividir o trabalho em tarefas pequenas com entregas semanais (ler dois artigos, transcrever "
            "uma entrevista, rodar uma análise) funciona melhor do que reservar um dia inteiro que nunca chega.\n\n"
            "Semana de provas existe para todo mundo. O erro não é diminuir o ritmo, é sumir sem avisar: mande uma "
            "mensagem ao orientador antes, diga o que vai atrasar e proponha uma nova data. Orientadores lidam bem com "
            "transparência e muito mal com silêncio.\n\n"
            "Se, depois de alguns meses, a conta nunca fecha, converse abertamente: pode ser possível reduzir a carga, "
            "ajustar o plano de trabalho ou pausar. Interromper um semestre de iniciação científica para não reprovar "
            "em disciplina é uma decisão madura, não uma derrota."
        ),
    },
    {
        "seed_chave": "grupos-de-pesquisa-cnpq",
        "dias_atras": 5, "hora": 10,
        "titulo": "O que são os grupos de pesquisa (Diretório do CNPq) e como entro em um?",
        "conteudo": (
            "Um grupo de pesquisa reúne professores, pós-graduandos e estudantes de graduação em torno de linhas de "
            "pesquisa comuns, com reuniões periódicas, projetos e produção conjunta. O CNPq mantém o Diretório dos "
            "Grupos de Pesquisa no Brasil (dgp.cnpq.br), um cadastro público em que você pode buscar grupos por "
            "palavra-chave, área, instituição e líder, e ver as linhas de pesquisa e os integrantes de cada um.\n\n"
            "Para entrar, o caminho normal é por um projeto ou pelo líder do grupo: procure o professor, mostre "
            "interesse em uma linha específica e pergunte se há espaço para um aluno de iniciação. Muitos grupos "
            "aceitam ouvintes nas reuniões antes de formalizar a entrada, o que é uma boa maneira de conhecer o ritmo "
            "e as pessoas. Uma vez integrante, o líder cadastra você no Diretório, e o vínculo passa a aparecer no "
            "seu Lattes.\n\n"
            "Participar de um grupo tem vantagens que uma orientação isolada não tem: você aprende com estudantes "
            "mais avançados, participa de leituras dirigidas, vê de perto como se escreve um projeto e como se "
            "responde a um parecer, e costuma ter mais oportunidades de coautoria em resumos e artigos. É também o "
            "melhor lugar para descobrir, cedo, se a vida de pesquisa é mesmo para você."
        ),
    },
    {
        "seed_chave": "iniciacao-cientifica-voluntaria",
        "dias_atras": 2, "hora": 13,
        "titulo": "Não consegui bolsa. Vale a pena fazer iniciação científica como voluntário(a)?",
        "conteudo": (
            "Vale, e muito. A iniciação científica voluntária (cada instituição dá um nome ao programa) "
            "segue o mesmo plano de trabalho, tem o mesmo orientador, exige os mesmos relatórios e dá o mesmo "
            "certificado da modalidade com bolsa. Para quem avalia um currículo depois, um resumo apresentado em "
            "evento ou um artigo publicado valem igual, com ou sem bolsa.\n\n"
            "Formalize a participação: o orientador cadastra o plano de trabalho voluntário na pró-reitoria de "
            "pesquisa (há edital ou fluxo contínuo para isso). Sem o cadastro, você não tem certificado, não pode "
            "apresentar no seminário de iniciação científica da instituição e o vínculo não aparece no Lattes.\n\n"
            "Quem já está no projeto como voluntário costuma ter prioridade quando surge uma cota de bolsa no edital "
            "seguinte, e muitos orientadores só indicam para bolsa quem já demonstrou compromisso. Se a falta da "
            "bolsa inviabiliza a sua permanência na universidade, procure a pró-reitoria de assuntos estudantis: "
            "auxílios de permanência em geral podem ser acumulados com a iniciação científica voluntária e, em "
            "muitos casos, também com a bolsa."
        ),
    },
]


# Primeira postagem do fórum, assinada por um dos fundadores com a conta
# pessoal dele (identificada pelo e-mail). Entra com data anterior a tudo o
# que já existe no fórum, para abrir a linha do tempo; se a conta não existir
# no banco, a postagem não é criada (nunca sai em nome de outra pessoa).
POST_FUNDADOR: Dict[str, Any] = {
    "seed_chave": "boas-vindas-fundador",
    "autor_email": "matheusmggabriel@gmail.com",
    "titulo": "Bem-vindas e bem-vindos ao fórum do UniResu Connect",
    "conteudo": (
        "Este fórum nasceu de uma dificuldade que todo estudante conhece: descobrir onde estão os projetos de "
        "pesquisa e extensão da própria universidade, quem os coordena e como entrar em um deles. A plataforma "
        "reúne os projetos em andamento num lugar só, e este espaço existe para o que a lista não resolve "
        "sozinha: as dúvidas, as trocas de experiência e os avisos entre quem está começando e quem já passou "
        "por isso.\n\n"
        "Use o fórum para perguntar o que não encontrou nos editais, contar como foi a sua seleção, indicar "
        "eventos e oportunidades e pedir opinião sobre uma carta de intenção ou um primeiro resumo. Responda "
        "quando souber ajudar: uma resposta curta e concreta vale mais do que um texto longo cheio de "
        "generalidades.\n\n"
        "Três combinados mantêm o espaço útil para todo mundo. Respeito sempre, inclusive na discordância. "
        "Nada de dados pessoais de terceiros nem de conteúdo que não seja seu. E, antes de abrir uma pergunta, "
        "vale uma busca rápida: muitas já têm resposta na lista. O código de conduta completo aparece no "
        "registro e vale para todas as interações aqui.\n\n"
        "Sejam bem-vindas e bem-vindos. A plataforma é feita por estudantes e cresce com o que a comunidade "
        "traz para cá."
    ),
}


async def garantir_usuario_sistema(db) -> Dict[str, Any]:
    """Devolve o usuário de sistema, criando-o se não existir.

    Procura pelo e-mail (chave de negócio da conta). A criação é um upsert
    com `$setOnInsert`, decidido no servidor: dois processos iniciando ao
    mesmo tempo não criam duas contas. Uma conta antiga sem
    `username`/`sistema` ganha os dois campos, sem tocar no resto.
    """
    agora = datetime.now(timezone.utc)
    await db.usuarios.update_one(
        {"email": USUARIO_SISTEMA["email"]},
        {"$setOnInsert": {**USUARIO_SISTEMA, "criado_em": agora, "atualizado_em": agora}},
        upsert=True,
    )
    usuario = await db.usuarios.find_one({"email": USUARIO_SISTEMA["email"]})

    faltando = {
        campo: valor
        for campo, valor in (("username", USUARIO_SISTEMA["username"]), ("sistema", True))
        if usuario.get(campo) != valor
    }
    if faltando:
        await db.usuarios.update_one({"_id": usuario["_id"]}, {"$set": faltando})
        usuario.update(faltando)
    return usuario


def montar_topico(pergunta: Dict[str, Any], autor_id: str, agora: datetime) -> Dict[str, Any]:
    data = (agora - timedelta(days=pergunta["dias_atras"])).replace(
        hour=pergunta["hora"], minute=0, second=0, microsecond=0,
    )
    # Só `autor_id`: o fórum resolve o autor na leitura e nunca grava e-mail.
    return {
        "titulo": pergunta["titulo"],
        "conteudo_original": pergunta["conteudo"],
        "autor_id": autor_id,
        "data_criacao": data,
        "visualizacoes": 0,
        "likes": [],
        "dislikes": [],
        "total_respostas": 0,
        "seed": SEED_VERSAO,
        "seed_chave": pergunta["seed_chave"],
    }


async def seed_forum(db, agora: Optional[datetime] = None) -> int:
    """Insere as perguntas do seed que ainda não existem. Devolve quantas entraram.

    Cada pergunta é um upsert por (`seed`, `seed_chave`) com `$setOnInsert`,
    protegido por um índice único parcial: a decisão de inserir é do servidor,
    então dois startups simultâneos não duplicam as perguntas.
    """
    chaves = [p["seed_chave"] for p in PERGUNTAS]
    assert len(set(chaves)) == len(chaves), "seed_chave repetida em PERGUNTAS"

    await db.topicos_forum.create_index(
        [("seed", 1), ("seed_chave", 1)],
        name="uniq_seed_chave",
        unique=True,
        partialFilterExpression={"seed": {"$exists": True}},
    )

    usuario = await garantir_usuario_sistema(db)
    autor_id = str(usuario["_id"])
    agora = agora or datetime.now(timezone.utc)

    inseridos = 0
    for pergunta in PERGUNTAS:
        try:
            resultado = await db.topicos_forum.update_one(
                {"seed": SEED_VERSAO, "seed_chave": pergunta["seed_chave"]},
                {"$setOnInsert": montar_topico(pergunta, autor_id, agora)},
                upsert=True,
            )
        except DuplicateKeyError:
            continue  # outro processo inseriu a mesma pergunta neste instante
        if resultado.upserted_id is not None:
            inseridos += 1
    inseridos += await seed_post_fundador(db, agora)
    return inseridos


async def seed_post_fundador(db, agora: datetime) -> int:
    """Insere a postagem de boas-vindas do fundador, datada um dia antes da
    postagem mais antiga do fórum (ou 90 dias atrás, se o fórum estiver vazio).
    Só entra se a conta do autor existir; devolve 1 se inseriu, senão 0."""
    if await db.topicos_forum.find_one({"seed": SEED_VERSAO, "seed_chave": POST_FUNDADOR["seed_chave"]}):
        return 0
    autor = await db.usuarios.find_one({"email": POST_FUNDADOR["autor_email"]}, {"_id": 1})
    if not autor:
        return 0
    mais_antigo = await db.topicos_forum.find_one({}, {"data_criacao": 1}, sort=[("data_criacao", 1)])
    if mais_antigo and mais_antigo.get("data_criacao"):
        referencia = mais_antigo["data_criacao"]
        if referencia.tzinfo is None:
            referencia = referencia.replace(tzinfo=timezone.utc)
        data = (referencia - timedelta(days=1)).replace(hour=10, minute=0, second=0, microsecond=0)
    else:
        data = (agora - timedelta(days=90)).replace(hour=10, minute=0, second=0, microsecond=0)
    topico = montar_topico({**POST_FUNDADOR, "dias_atras": 0, "hora": 10}, str(autor["_id"]), agora)
    topico["data_criacao"] = data
    try:
        resultado = await db.topicos_forum.update_one(
            {"seed": SEED_VERSAO, "seed_chave": POST_FUNDADOR["seed_chave"]},
            {"$setOnInsert": topico},
            upsert=True,
        )
    except DuplicateKeyError:
        return 0
    return 1 if resultado.upserted_id is not None else 0


async def main() -> int:
    load_dotenv()
    from database.connection import Database

    await Database.connect()
    try:
        inseridos = await seed_forum(Database.get_db())
    finally:
        await Database.disconnect()

    print(f"Seed do fórum: {inseridos} pergunta(s) inserida(s), {len(PERGUNTAS) - inseridos} já existia(m).")
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
