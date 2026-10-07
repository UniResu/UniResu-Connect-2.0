# UniResu Connect

**Projeto de Extensão e Pesquisa**
<br>
**Projeto: Desenvolvimento de uma Aplicação Interativa Universitária**
<br>
**2025.2**

---

A presente plataforma web, **UniResu Connect**, propõe-se a ser um ecossistema digital para otimizar a conexão entre o corpo discente e as oportunidades de pesquisa e extensão universitária. O sistema permite que docentes e coordenadores de projeto divulguem suas vagas de forma transparente e estruturada, alcançando um público amplo e diversificado de talentos. Simultaneamente, estudantes de todos os períodos podem descobrir e se candidatar a oportunidades alinhadas com seus interesses e perfil acadêmico, quebrando as barreiras de acesso impostas pela informalidade e pela dispersão de informações. Dessa forma, a aplicação busca aliar tecnologia, equidade e gestão acadêmica eficiente, contribuindo para a democratização do acesso ao conhecimento e para a plena valorização do potencial humano da universidade.

### **Integrantes**

* Daniel Pereira Santos da Silva
* Davi Lopes Rodrigues
* José Murilo Almeida do Nascimento
* Juliana Gimenes Müller
* Lucas Eduardo Sanches Cordeiro
* Maria Eduarda Siqueira de Medeiros
* Matheus Gabriel Ramos de Melo
* Pedro de Magalhães Leitão

### **Orientadores**

* Prof. Dr. Carlos Eduardo Raymundo
* Prof. Dr. Thayse Moraes de Moraes

---

### **Instruções de Instalação, Execução e Acesso**

* **Acesso rápido (protótipo)**
    * **URL da aplicação:** `https://uniresu-connect.dev/`
    * **Status:** Protótipo funcional
    * **Ambiente:** Homologação
* **Usuário(s) de teste:**

    * **Perfil Estudante (Graduando):**
        * **Login:** `lucas.alves`
        * **Senha:** `calouro123`
    * **Perfil Professor (Pesquisador):**
        * **Login:** `helena.medeiros`
        * **Senha:** `pesquisa456`

---

### **Projetos do SIGAA/UNIR e dos portais da UNIRIO, e candidatura com carta de intenção**

A aba **Projetos Acadêmicos** lista, além dos projetos cadastrados pelos professores, os projetos de **pesquisa** e **extensão** coletados semanalmente de duas fontes públicas: as consultas do **SIGAA/UNIR** e os **portais da UNIRIO** (Portal da Pesquisa e Portal da Extensão). Os filtros permitem escolher módulo (pesquisa/extensão), instituição (UNIR, UNIRIO) e unidade. O aluno se candidata escrevendo uma **carta de intenção**, que chega no corpo do e-mail do(a) coordenador(a) — com *reply-to* no e-mail do aluno e o Lattes como link no final.

**Como funciona o sync**

* `backend/jobs/sync_sigaa.py` faz o fluxo JSF do SIGAA (GET → `javax.faces.ViewState` → POST com filtros e o botão Buscar), lê a tabela de resultados e abre a página de detalhe de cada item para obter coordenador(a), e-mail e período.
* Pausa mínima de 1 s entre requisições (padrão 1,5 s), timeout e retry com backoff exponencial.
* Grava na collection `projetos` com `origem: "sigaa"` (upsert pela chave natural tipo + ano + título + coordenador). **Projetos cadastrados manualmente nunca são alterados.** Projetos que somem da fonte ficam `ativo: false` — nada é apagado.
* Se um módulo retornar **0 resultados** (ou a busca falhar), nada daquele módulo é desativado: a run é marcada como falha, a equipe recebe alerta por e-mail e o processo sai com código 1.
* Se o detalhe de um item falhar, o item é salvo com os dados da listagem (sem contato → botão "Candidatar-se" desabilitado) e o erro vai para o log da run.
* Cada execução fica registrada em `sigaa_sync_runs` (coletados, novos, atualizados, desativados, erros). A data da última execução bem-sucedida fica disponível em `GET /api/projetos/fontes/status` só para professores e pesquisadores logados (não aparece na aba pública).
* Agendamento: GitHub Actions, toda segunda às 09:00 UTC (`.github/workflows/sync-sigaa.yml`).

**Rodar o job manualmente**

* Pelo GitHub: **Actions → Sync SIGAA → Run workflow** (dá para informar anos e módulos).
* Localmente (usa o `MONGO_URI` do `backend/.env`):

  ```bash
  cd backend
  python -m jobs.sync_sigaa
  # só um módulo / outros anos:
  SIGAA_MODULOS=pesquisa SIGAA_ANOS=2025,2026 python -m jobs.sync_sigaa
  ```

**Sync com a UNIRIO**

* Fontes: [Portal da Pesquisa](https://sistemas.unirio.br/projetos/search/index) e [Portal da Extensão](https://sistemas2.unirio.br/extensao/busca/projetos?cat_termos=titulo&f_ano=0&f_area=0&f_centro=0&f_cor=0&f_lin=0&f_status=1&f_uni=0&termos=) (busca com status "em andamento").
* `backend/jobs/sync_unirio.py` lê a busca de cada portal e abre a página de detalhe de cada projeto (coordenador(a), e-mail, unidade, período, resumo, palavras-chave, área temática, linhas de extensão). Extensão: GET na busca pública e paginação por link (`pag=N`, 5 projetos por página, cerca de 390 projetos em andamento). Pesquisa: o portal (web2py) só lista após um POST no formulário de busca em `default/index`, que redireciona para `search/index` com todos os projetos numa única tabela (cerca de 2.300, desde 1992); se o portal passar a exigir algum filtro, o job busca por ano de referência. O Portal da Pesquisa é lento (30 a 40 segundos por página de detalhe na primeira carga) e tem quedas longas, então a carga completa da pesquisa leva bem mais de um dia; por isso a pesquisa abre os detalhes dos anos mais recentes primeiro, a primeira carga pode ser feita com `UNIRIO_PESQUISA_ANO_MINIMO` e retomada com `UNIRIO_DETALHES=novos`, e a extensão (servidor diferente) leva perto de uma hora; as execuções seguintes são **incrementais** (`UNIRIO_DETALHES=incremental`, padrão): a listagem inteira é percorrida de novo, mas só se abre o detalhe de projetos novos e, na pesquisa, dos que ainda constam como em execução, para perceber quando encerram. Projetos já conhecidos e encerrados ficam como estão, e o que some da listagem fica inativo. Use `completo` para reler todos os detalhes. A plataforma exibe só os projetos em execução; os demais ficam gravados com a situação lida. O parser fica em `backend/services/unirio/parser.py`; o cliente HTTP (pausa, timeout, retry) é o mesmo do SIGAA (`backend/services/http_client.py`).
* Grava na collection `projetos` com `origem: "unirio"`, `instituicao: "UNIRIO"` e `modulo` (`pesquisa`/`extensao`), com chave natural em `chave_unirio`. As regras são as mesmas do SIGAA: projetos manuais nunca são tocados, uma fonte nunca encosta nos documentos da outra, e o que some da fonte fica `ativo: false`.
* Uma listagem que parou antes da última página (teto `UNIRIO_MAX_PAGINAS` ou paginação não reconhecida) é tratada como falha: o que foi lido é gravado, mas **nada é desativado** e o alerta é enviado. O sync real grava em lotes de 50 projetos à medida que lê os detalhes (andamento em `sigaa_sync_runs.progresso`), então, se o processo for morto pelo timeout do Actions, o que já foi lido fica no banco e a run fica `abortada`. Com `UNIRIO_PESQUISA_ANO_MINIMO`, só projetos de pesquisa dentro do recorte podem ser desativados.
* As fixtures `backend/tests/fixtures/unirio_*.html` são o HTML real dos dois portais (anonimizado: nomes e e-mails trocados, resumos encurtados). Se o layout mudar, rode o modo `captura`, baixe o artifact `captura-unirio` e atualize parser e fixtures.
* As execuções ficam em `sigaa_sync_runs` com `fonte: "unirio"` (mesma collection do SIGAA, para reaproveitar o usuário restrito do Atlas). A rota `GET /api/projetos/fontes/status` (professores e pesquisadores logados) devolve a última coleta de cada fonte.
* Agendamento: GitHub Actions, toda segunda às 10:00 UTC (`.github/workflows/sync-unirio.yml`). **Está comentado no workflow** até o parser ser validado com o HTML real; até lá, só execução manual.
* Execução manual (**Actions → Sync UNIRIO → Run workflow**): além do modo, dá para escolher os módulos, o tipo de leitura dos detalhes (`incremental` ou `completo`) e o ano mínimo da pesquisa (ex.: `2022` para uma carga rápida só dos projetos recentes). Execuções de módulos diferentes rodam em paralelo (os portais são servidores distintos); duas do mesmo módulo ficam em fila. Os três modos:
  * `sync`: coleta e grava (o que o agendamento roda);
  * `dry-run`: coleta e imprime estatísticas e amostras, sem gravar nada — use antes do primeiro `sync` e sempre que o layout dos portais mudar;
  * `captura`: salva o HTML bruto da primeira página de cada listagem e dos primeiros detalhes como artifact `captura-unirio` (e, para quem só vê o log, imprime cada página em gzip+base64 nas linhas `CAPTURA-B64`), para atualizar o parser e as fixtures de teste.

  ```bash
  cd backend
  python -m jobs.sync_unirio --dry-run
  UNIRIO_MODULOS=extensao python -m jobs.sync_unirio
  UNIRIO_DETALHES=completo python -m jobs.sync_unirio   # relê todos os detalhes (~2 h)
  ```

**Sync com a UFV**

* Fonte: portal de dados abertos da Universidade Federal de Viçosa ([dados.ufv.br](https://dados.ufv.br/dataset/projetos-e-programas-de-extensao)). `backend/jobs/sync_ufv.py` coleta dois módulos:
  * **Extensão**: conjunto "Projetos e programas de extensão", pela API DataStore do CKAN com SQL, pedindo só o que está em execução hoje (início no passado e término no futuro), em páginas de 200. São duas ou três requisições.
  * **Pesquisa**: conjunto "Projetos de pesquisa". O DataStore desse recurso só tem as linhas até 2010, então o job baixa o CSV completo do recurso (uns 225 MB, uma linha por participante, atualizado todo mês) em uma única requisição e filtra localmente os projetos vigentes: situação `Registrado` (configurável em `UFV_PESQUISA_SITUACOES`), registrados nos últimos quatro anos (`UFV_PESQUISA_ANO_MINIMO`), já iniciados e sem data de término no passado. A coordenação é a pessoa com papel `Líder` (depois `Co-Líder`, depois `Executor`); a equipe inteira fica em `extras.equipe`. O link de detalhe aponta para a página pública do sistema de pesquisa da UFV, quando o projeto tem número de registro.
* Grava com `origem: "ufv"`, `instituicao: "UFV"`, `modulo` `extensao` ou `pesquisa` e chave natural em `chave_ufv`. Os conjuntos não trazem e-mail: para receber candidaturas, cadastre o contato manualmente (abaixo). A área CNPq fica em `area_cnpq` (na pesquisa é a área específica, por exemplo "Ciência do Solo"); na pesquisa, `unidade` é a sigla do departamento.
* Projetos da UFV que saem da coleta (terminaram) ficam `ativo: false`, módulo a módulo. Uma coleta vazia ou com erro em um módulo é falha daquele módulo e não desativa nada dele.
* Agendamento: toda segunda às 10:30 UTC (`.github/workflows/sync-ufv.yml`), com modos `sync` e `dry-run` e a escolha dos módulos na execução manual.

  ```bash
  cd backend
  python -m jobs.sync_ufv --dry-run
  UFV_MODULOS=pesquisa python -m jobs.sync_ufv --dry-run   # imprime também as contagens por situação e ano
  python -m jobs.sync_ufv
  ```

**Projeto sem e-mail de contato**

O e-mail vem da página de detalhe da fonte (SIGAA ou portal da UNIRIO). Os dados abertos da UFV não trazem e-mail: nos projetos de extensão da UFV a plataforma mostra, no lugar do formulário, o contato geral do Registro de Atividades de Extensão (raex@ufv.br), e nos de pesquisa aponta para a página do projeto no sistema da UFV. Quando o e-mail não vier (ou não for o endereço certo), cadastre o contato manualmente: ele tem prioridade e nunca é sobrescrito pelo sync:

```bash
cd backend
python -m jobs.definir_contato --codigo PVC2148-2026 --email coordenador@unir.br   # SIGAA, pesquisa
python -m jobs.definir_contato --sigaa-id 4527 --email coordenador@unir.br         # SIGAA, extensão
python -m jobs.definir_contato --unirio-id 8620 --email coordenador@unirio.br      # UNIRIO (ID_PROJETO do detalhe)
python -m jobs.definir_contato --projeto-id 66f0c1... --email coordenador@unir.br  # qualquer projeto, pelo _id
python -m jobs.definir_contato --codigo PVC2148-2026 --remover
```

**Projetos de teste anteriores ao SIGAA**

Os projetos cadastrados manualmente antes da primeira coleta do SIGAA eram apenas de teste. Eles ficam na mesma collection `projetos` (banco `UniResuDB`) que os milhares de projetos coletados; para vê-los no Atlas, filtre por `{ "origem": { "$exists": false } }`. O script lista primeiro e só apaga com `--confirmar`; ele precisa de um usuário do Atlas com permissão de remoção, não o usuário restrito dos jobs:

```bash
cd backend
python -m jobs.remover_projetos_teste                     # lista o que seria removido
python -m jobs.remover_projetos_teste --confirmar         # remove (e as candidaturas ligadas)
python -m jobs.remover_projetos_teste --todos --confirmar # todo projeto sem origem de coleta, sem data de corte
```

Pelo GitHub Actions: workflow **Manutenção do banco** (`.github/workflows/manutencao.yml`). A tarefa `status` só lê o banco e imprime no log quantos projetos há por fonte e módulo (total, ativos, em execução, com detalhe) e as últimas execuções dos syncs (`python -m jobs.status_banco` faz o mesmo localmente). A tarefa `remover-projetos-teste` remove os projetos de teste. Sem marcar **confirmar** ele só lista. Para apagar, crie antes o secret `MONGO_URI_ADMIN` com a connection string do usuário da API (a mesma do Render) ou de um usuário com `readWrite`; sem ele o job usa `MONGO_URI` e a remoção falha por falta de permissão.

**Filtros da busca**

`GET /api/projetos/filtros` devolve as opções agrupadas por instituição (UNIR, UNIRIO e as instituições de projetos manuais), com as unidades/departamentos e contagens por módulo. A aba Projetos usa isso para mostrar categorias: primeiro a instituição, depois a unidade dentro dela.

**Variáveis de ambiente novas**

| Variável | Onde | Padrão | Descrição |
|---|---|---|---|
| `SIGAA_ANOS` | job | ano corrente | Anos consultados, separados por vírgula |
| `SIGAA_MODULOS` | job | `pesquisa,extensao` | Módulos coletados |
| `SIGAA_PESQUISA_SITUACAO` | job | `EM EXECUÇÃO` | Filtro de situação da pesquisa (vazio = todas) |
| `SIGAA_EXTENSAO_TIPOS` | job | `PROJETO,PROGRAMA` | Tipos de ação de extensão importados |
| `SIGAA_PAUSA_SEGUNDOS` | job | `1.5` | Pausa entre requisições (mínimo 1) |
| `SIGAA_TIMEOUT_SEGUNDOS` | job | `60` | Timeout de cada requisição |
| `SIGAA_MAX_TENTATIVAS` | job | `3` | Tentativas por requisição (backoff 2 s, 4 s, …) |
| `SIGAA_ALERTA_EMAIL` | job | `EMAIL_SUPORTE` | Quem recebe o alerta de falha do sync |
| `UNIRIO_MODULOS` | job | `pesquisa,extensao` | Módulos coletados dos portais da UNIRIO |
| `UNIRIO_EXTENSAO_STATUS` | job | `1` | Filtro `f_status` da busca de extensão (1 = em andamento, 0 = todos) |
| `UNIRIO_PESQUISA_ANOS` | job | todos os anos do formulário | Anos de referência buscados no Portal da Pesquisa quando a busca sem filtro não lista nada |
| `UNIRIO_PESQUISA_ANO_MINIMO` | job | `0` (sem corte) | Ignora projetos de pesquisa com ano de referência anterior a este (a busca lista tudo desde 1992, cerca de 2.300 projetos) |
| `UNIRIO_MAX_PAGINAS` | job | `300` | Teto de páginas percorridas por listagem (ao bater, a listagem conta como incompleta) |
| `UNIRIO_MAX_DETALHES` | job | `0` | Teto de detalhes consultados por módulo, só em `dry-run`/`captura` (o sync real ignora) |
| `UNIRIO_DETALHES` | job | `incremental` | Quais páginas de detalhe abrir no sync real: `incremental` (só projetos novos e, na pesquisa, os ainda em execução; os já conhecidos e encerrados ficam como estão), `novos` (só os que ainda não têm detalhe gravado, para retomar uma carga interrompida) ou `completo` (todos). A listagem é sempre percorrida inteira: é ela que diz o que sumiu dos portais |
| `UNIRIO_ESPERA_PORTAL_MINUTOS` | job | `0` (`60` no workflow) | Se o portal estiver fora do ar (HTTP 500, conexão recusada), espera até esse tempo verificando a cada 10 minutos antes de desistir do módulo |
| `UNIRIO_URL_PESQUISA` | job | URL do Portal da Pesquisa | Substitui a URL da listagem de pesquisa |
| `UNIRIO_URL_EXTENSAO` | job | URL do Portal da Extensão | Substitui a URL da listagem de extensão |
| `UNIRIO_PESQUISA_DETALHE_PREFIXO` | job | diretório da listagem (`/projetos/search/`) | Prefixo de caminho dos links de detalhe da pesquisa aceitos pelo parser |
| `UNIRIO_CAPTURA_DIR` | job | `captura` | Pasta onde o modo `captura` salva o HTML |
| `UNIRIO_PAUSA_SEGUNDOS` | job | `1.5` | Pausa entre requisições (mínimo 1) |
| `UNIRIO_TIMEOUT_SEGUNDOS` | job | `60` | Timeout de cada requisição |
| `UNIRIO_MAX_TENTATIVAS` | job | `3` | Tentativas por requisição (backoff 2 s, 4 s, …) |
| `UNIRIO_ALERTA_EMAIL` | job | `SIGAA_ALERTA_EMAIL` | Quem recebe o alerta de falha do sync da UNIRIO |
| `CANDIDATURA_LIMITE_HORA` | API | `5` | Máximo de candidaturas por aluno por hora |
| `CANDIDATURA_LIMITE_DIA` | API | `20` | Máximo de candidaturas por aluno em 24 h |

O envio de e-mail continua usando `RESEND_API_KEY`, `EMAIL_REMETENTE` e `EMAIL_SUPORTE`, já existentes.

**Configuração obrigatória para o job no GitHub Actions**

1. **Atlas → Network Access:** liberar `0.0.0.0/0`. Os IPs dos runners do GitHub Actions mudam a cada execução, então não dá para usar uma allowlist fixa. A proteção passa a ser o usuário exclusivo abaixo, com senha forte.
2. **Atlas → Database Access:** criar um usuário **exclusivo dos jobs** com uma *custom role* que só permite `find`, `insert` e `update` nas collections `projetos` e `sigaa_sync_runs` do banco `UniResuDB`. Não reutilize o usuário da API. O mesmo usuário serve aos dois syncs (SIGAA e UNIRIO).
3. **GitHub → Settings → Secrets and variables → Actions:**
   * secret `MONGO_URI` com a connection string desse usuário;
   * secret `RESEND_API_KEY` (opcional, para o alerta de falha por e-mail);
   * variáveis opcionais: `MONGO_DB_NAME`, `EMAIL_REMETENTE`, `SIGAA_ANOS`, `SIGAA_MODULOS`, `SIGAA_PESQUISA_SITUACAO`, `SIGAA_EXTENSAO_TIPOS`, `SIGAA_ALERTA_EMAIL`, `UNIRIO_MODULOS`, `UNIRIO_MAX_DETALHES`, `UNIRIO_DETALHES`, `UNIRIO_EXTENSAO_STATUS`, `UNIRIO_PESQUISA_DETALHE_PREFIXO`, `UNIRIO_ALERTA_EMAIL` (se ausente, usa `SIGAA_ALERTA_EMAIL`). As demais variáveis `UNIRIO_*` da tabela só são lidas em execuções locais.
4. O agendamento só vale depois que o workflow estiver na branch `main`.

**Testes e lint**

```bash
cd backend
pip install -r requirements-dev.txt
pytest          # parsers do SIGAA e da UNIRIO (HTML real salvo e anonimizado), upsert, jobs,
                # listagem e filtros, candidatura, registro/perfil por vínculo, fórum
                # (privacidade, seed, usernames)
ruff check .

cd ../frontend
npm run lint
```

---

### **Perfis e registro**

O perfil tem um **vínculo institucional** (`papel` no banco), escolhido pela própria pessoa no registro e alterável depois em **Editar perfil**:

| Valor no banco | Rótulo na interface | Sub-documento | Campos próprios |
| --- | --- | --- | --- |
| `aluno` | Discente | `dados_aluno` | nível (graduação, mestrado, doutorado), semestre, orientador(a), linha de pesquisa |
| `professor` | Docente | `dados_professor` | titulação, cargo, linhas de pesquisa, laboratório |
| `pesquisador` | Pesquisador(a) | `dados_pesquisador` | titulação, vínculo (pós-doc, colaborador(a), visitante), linhas e grupo de pesquisa |
| `tecnico` | Técnico(a)-administrativo(a) | `dados_tecnico` | setor, cargo |
| `egresso` | Egresso(a) | `dados_egresso` | ano de conclusão, atuação atual |

Os três primeiros valores existem desde a primeira versão e mantêm o nome interno antigo. Só docentes e pesquisadores(as) cadastram projetos e recebem candidaturas (`PAPEIS_PERMITIDOS` em `backend/routes/projeto_routes.py`). Os rótulos e as opções da interface ficam em `frontend/src/lib/perfis.ts`.

**Registro por e-mail** (`POST /api/usuarios/registrar`, página `/registrar`, baseada no protótipo do Figma): nome, e-mail institucional, vínculo, campos do vínculo escolhido, senha e os dois aceites (`aceite_regras`, `aceite_dados`), ambos obrigatórios. O backend grava `aceites_em` e cria apenas o sub-documento do vínculo escolhido. A lista de domínios aceitos é compartilhada entre `backend/services/emails_institucionais.py` e o frontend.

**Login via ORCID**: o ORCID não informa se a pessoa é discente, docente ou pesquisador(a), então a conta nasce com `perfil_completo: false` e e-mail provisório (`<orcid>@orcid.placeholder`). O frontend redireciona para `/perfil/completar`, onde a pessoa escolhe o vínculo, informa o e-mail institucional e marca os aceites. O e-mail fica em `email_pendente` até ser confirmado pelo link enviado (mesmo fluxo de verificação do registro); enquanto isso a conta continua funcionando pelo ORCID, e a página de perfil mostra o aviso com as opções de reenviar o link ou informar outro e-mail. Se o e-mail informado já pertence a uma conta por senha, confirmar o link vincula o ORCID a essa conta (as candidaturas e os tópicos da conta provisória passam para ela) e a provisória é desativada. O token de sessão carrega o id da conta (`uid`), então a sessão sobrevive à troca de e-mail. `perfil_completo` é decidido pelo servidor (vínculo, aceites e e-mail informado) e as rotas que compartilham dados com terceiros (candidatar-se, publicar no fórum, cadastrar projetos) exigem o perfil concluído (`get_usuario_com_perfil_completo`, HTTP 403 caso contrário).

---

### **Fórum**

A aba **Fórum** é uma lista de perguntas em estilo thread (sem comentários nem respostas, por regra de negócio): título, resumo, uma linha de meta (`@username`, há quanto tempo, visualizações, votos) e, ao abrir, o texto completo com os botões de voto. Busca e ordenação (**Recentes** / **Mais votadas**) acontecem no navegador sobre a lista carregada.

**Username no lugar do e-mail**

* A API do fórum **nunca devolve e-mail**: cada tópico traz `autor_username` e `autor_nome` (nome social ou nome), resolvidos a partir de `autor_id` com uma única consulta em lote em `usuarios`. Tópicos antigos sem autor identificável aparecem como `@usuario`.
* O campo `username` da collection `usuarios` é gerado a partir do **nome** (nunca do e-mail): minúsculas, 3 a 30 caracteres de `[a-z0-9._-]`, único (`matheus-gabriel`, `matheus-gabriel-2`...). É criado no registro, no primeiro login via ORCID e, para contas antigas, pelo backfill que roda no startup da API (`migrar_dados`, em `backend/database/indexes.py`). O índice único `uniq_username` é *sparse*, para não quebrar antes do backfill. A lógica fica em `backend/services/usernames.py`.
* `GET /api/forum/topicos/{id}` devolve um tópico e soma uma visualização (`$inc`).

**Seed de perguntas**

`backend/jobs/seed_forum.py` publica 15 perguntas frequentes da vida acadêmica (iniciação científica, carta de intenção, Lattes, ORCID, bolsas, comitê de ética, revistas predatórias...), cada uma com um texto que funciona como entrada de FAQ. O autor é o usuário de sistema **Equipe UniResu** (`@uniresu`, `forum@uniresu.org`, `sistema: true`, sem `senha_hash`, logo sem login), criado pelo próprio seed. É idempotente (os tópicos levam `seed: "forum_v1"` e uma `seed_chave`; só entram os que faltam) e roda automaticamente no startup da API, dentro de `migrar_dados`, então a produção é populada no próximo deploy sem acesso manual ao banco. Para rodar à mão (usa o `MONGO_URI` do `backend/.env`):

```bash
cd backend
python -m jobs.seed_forum
```

---

### **Documentação**

* [Documentação de Contexto](https://github.com/UniResu/UniResu-Connect-2.0/blob/main/docs/01-Documenta%C3%A7%C3%A3o%20de%20Contexto.md)
* [Especificação do Projeto](https://github.com/UniResu/UniResu-Connect-2.0/blob/main/docs/02-Especifica%C3%A7%C3%A3o%20do%20Projeto.md)
* [Metodologia (Scrum)](https://github.com/UniResu/UniResu-Connect-2.0/blob/main/docs/03-Metodologia.md)
* [Projeto de Interface (UI/UX)](https://github.com/UniResu/UniResu-Connect-2.0/blob/main/docs/04-Projeto%20de%20Interface.md)
* [Arquitetura da Solução](https://github.com/UniResu/UniResu-Connect-2.0/blob/main/docs/05-Arquitetura%20da%20Solu%C3%A7%C3%A3o.md)
* [Template Padrão da Aplicação](https://github.com/UniResu/UniResu-Connect-2.0/blob/main/docs/06-Template%20Padr%C3%A3o%20da%20Aplica%C3%A7%C3%A3o.md)
* [Programação de Funcionalidades](https://github.com/UniResu/UniResu-Connect-2.0/blob/main/docs/07-Programa%C3%A7%C3%A3o%20de%20Funcionalidades.md)
* [Plano de Testes de Software](https://github.com/UniResu/UniResu-Connect-2.0/blob/main/docs/08-Plano%20de%20Testes%20de%20Software.md)
* [Registro de Testes de Software](https://github.com/UniResu/UniResu-Connect-2.0/blob/main/docs/09-Registro%20de%20Testes%20de%20Software.md)
* [Plano de Testes de Usabilidade](https://github.com/UniResu/UniResu-Connect-2.0/blob/main/docs/10-Plano%20de%20Testes%20de%20Usabilidade.md)
* [Registro de Testes de Usabilidade](https://github.com/UniResu/UniResu-Connect-2.0/blob/main/docs/11-Registro%20de%20Testes%20de%20Usabilidade.md)
* [Apresentação do Projeto](https://github.com/UniResu/UniResu-Connect-2.0/blob/main/docs/12-Apresenta%C3%A7%C3%A3o%20do%20Projeto.md)
* [Referências](https://github.com/UniResu/UniResu-Connect-2.0/blob/main/docs/13-Refer%C3%AAncias.md)

### **Código**

* [Código Fonte (GitHub)](https://github.com/seu-usuario/uniresu-connect)

### **Apresentação**

* [Apresentação do Projeto (Slides)](./link-para-apresentacao.pdf)

# 📝 Licença

Distribuído sob a Licença MIT. Veja [LICENSE](https://github.com/UniResu/UniResu-Connect-2.0/blob/main/LICENSE) para mais informações.
