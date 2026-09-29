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

### **Projetos do SIGAA/UNIR e candidatura com carta de intenção**

A aba **Projetos Acadêmicos** lista, além dos projetos cadastrados pelos professores, os projetos de **pesquisa** e **extensão** coletados semanalmente das consultas públicas do SIGAA/UNIR. O aluno se candidata escrevendo uma **carta de intenção**, que chega no corpo do e-mail do(a) coordenador(a) — com *reply-to* no e-mail do aluno e o Lattes como link no final.

**Como funciona o sync**

* `backend/jobs/sync_sigaa.py` faz o fluxo JSF do SIGAA (GET → `javax.faces.ViewState` → POST com filtros e o botão Buscar), lê a tabela de resultados e abre a página de detalhe de cada item para obter coordenador(a), e-mail e período.
* Pausa mínima de 1 s entre requisições (padrão 1,5 s), timeout e retry com backoff exponencial.
* Grava na collection `projetos` com `origem: "sigaa"` (upsert pela chave natural tipo + ano + título + coordenador). **Projetos cadastrados manualmente nunca são alterados.** Projetos que somem da fonte ficam `ativo: false` — nada é apagado.
* Se um módulo retornar **0 resultados** (ou a busca falhar), nada daquele módulo é desativado: a run é marcada como falha, a equipe recebe alerta por e-mail e o processo sai com código 1.
* Se o detalhe de um item falhar, o item é salvo com os dados da listagem (sem contato → botão "Candidatar-se" desabilitado) e o erro vai para o log da run.
* Cada execução fica registrada em `sigaa_sync_runs` (coletados, novos, atualizados, desativados, erros). A data da última execução bem-sucedida aparece na aba de projetos.
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

**Projeto sem e-mail de contato**

O e-mail vem da página de detalhe do SIGAA. Quando não vier (ou não for o endereço certo), cadastre o contato manualmente — ele tem prioridade e nunca é sobrescrito pelo sync:

```bash
cd backend
python -m jobs.definir_contato --codigo PVC2148-2026 --email coordenador@unir.br   # pesquisa
python -m jobs.definir_contato --sigaa-id 4527 --email coordenador@unir.br         # extensão
python -m jobs.definir_contato --codigo PVC2148-2026 --remover
```

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
| `CANDIDATURA_LIMITE_HORA` | API | `5` | Máximo de candidaturas por aluno por hora |
| `CANDIDATURA_LIMITE_DIA` | API | `20` | Máximo de candidaturas por aluno em 24 h |

O envio de e-mail continua usando `RESEND_API_KEY`, `EMAIL_REMETENTE` e `EMAIL_SUPORTE`, já existentes.

**Configuração obrigatória para o job no GitHub Actions**

1. **Atlas → Network Access:** liberar `0.0.0.0/0`. Os IPs dos runners do GitHub Actions mudam a cada execução, então não dá para usar uma allowlist fixa. A proteção passa a ser o usuário exclusivo abaixo, com senha forte.
2. **Atlas → Database Access:** criar um usuário **exclusivo do job** com uma *custom role* que só permite `find`, `insert` e `update` nas collections `projetos` e `sigaa_sync_runs` do banco `UniResuDB`. Não reutilize o usuário da API.
3. **GitHub → Settings → Secrets and variables → Actions:**
   * secret `MONGO_URI` com a connection string desse usuário;
   * secret `RESEND_API_KEY` (opcional, para o alerta de falha por e-mail);
   * variáveis opcionais: `MONGO_DB_NAME`, `SIGAA_ANOS`, `SIGAA_MODULOS`, `SIGAA_PESQUISA_SITUACAO`, `SIGAA_EXTENSAO_TIPOS`, `SIGAA_ALERTA_EMAIL`.
4. O agendamento só vale depois que o workflow estiver na branch `main`.

**Testes e lint**

```bash
cd backend
pip install -r requirements-dev.txt
pytest          # parser (HTML real do SIGAA salvo), upsert, job, listagem, candidatura
ruff check .

cd ../frontend
npm run lint
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
