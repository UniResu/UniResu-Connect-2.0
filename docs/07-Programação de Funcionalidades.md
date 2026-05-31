# Programação de Funcionalidades

<span style="color:red">Pré-requisitos: <a href="02-Especificação do Projeto.md">Especificação do Projeto</a>, <a href="04-Metodologia.md">Metodologia</a>, <a href="03-Projeto de Interface.md">Projeto de Interface</a>, <a href="05-Arquitetura da Solução.md">Arquitetura da Solução</a>

Esta seção descreve a implementação do **UniResu Connect 2.0** e relaciona os requisitos atendidos com os artefatos de código. A aplicação está estruturada em duas camadas principais: **frontend (Next.js)** e **backend (FastAPI)**, com persistência em **MongoDB Atlas** e integrações externas (ORCID e Resend).

## Visão geral da implementação

- **Frontend (Next.js + React 19)**: rotas em App Router, páginas de login, cadastro, recuperação de senha, listagem/gestão de projetos, candidaturas, fórum e perfis públicos.
- **Backend (FastAPI)**: API REST com autenticação JWT, módulos de usuários, projetos, candidaturas, fórum e perfis.
- **Integrações**: OAuth 2.0 via ORCID e envio de emails via Resend.
- **Infraestrutura**: deploy em Render.com, CDN Cloudflare e suporte opcional a Redis.

## Stack utilizada

| Camada         | Tecnologias                                                        |
| -------------- | ------------------------------------------------------------------ |
| Frontend       | Next.js 16.2.2, React 19.2.4, TypeScript 5.x, CSS Modules          |
| Backend        | FastAPI, Uvicorn, Gunicorn, Motor (MongoDB), Pydantic, python-jose |
| Banco de Dados | MongoDB Atlas                                                      |
| Integrações    | ORCID OAuth 2.0, Resend (email)                                    |
| Infraestrutura | Docker, Docker Compose, Render.com, Cloudflare                     |

## Mapeamento de requisitos, artefatos e responsáveis

| ID | Descrição do Requisito | Artefatos produzidos | Aluno(a) responsável |
|----|-------------------------|----------------------|----------------------|
| RF-01 | Autenticar usuários com email institucional e senha, com sessão via JWT | `backend/auth/autenticacao.py`, `backend/routes/auth_routes.py`, `frontend/src/app/login/`, `frontend/src/app/registrar/`, `frontend/src/contexts/AuthContext.tsx` | Equipe |
| RF-02 | Autenticar pesquisadores via ORCID (OAuth 2.0) e sincronizar perfil | `backend/controllers/orcid_controller.py`, `backend/routes/auth_routes.py`, `frontend/src/app/callback/orcid/`, `frontend/src/app/u/[orcidId]/` | Equipe |
| RF-03 | Gerenciar perfis de usuários (visualização e edição) | `backend/controllers/perfil_controller.py`, `backend/routes/perfil_routes.py`, `frontend/src/app/perfil/`, `frontend/src/app/perfil/editar/` | Equipe |
| RF-04 | CRUD de projetos com filtros e paginação | `backend/controllers/projeto_controller.py`, `backend/routes/projeto_routes.py`, `backend/models/projeto_model.py`, `frontend/src/app/projetos/`, `frontend/src/app/projetos/gerenciar/` | Equipe |
| RF-05 | Candidatar-se a projetos com envio de currículo e prevenção de duplicidade | `backend/controllers/candidatura_controller.py`, `backend/routes/candidatura_routes.py`, `backend/models/candidatura_model.py`, `frontend/src/app/candidaturas/` | Equipe |
| RF-06 | Fórum de discussão com criação e busca de tópicos | `backend/routes/forum_routes.py`, `backend/models/forum_model.py`, `frontend/src/app/forum/` | Equipe |
| RF-07 | Notificar professores por email ao receber candidaturas | `backend/controllers/candidatura_controller.py`, integração Resend | Equipe |

## Instruções de acesso e verificação

- **Aplicação (produção)**: https://uniresu.org  
- **API (Swagger/OpenAPI)**: https://api.uniresu.org/docs  
- **Usuário de teste**: não há credenciais públicas; utilizar cadastro.

### Comandos locais (verificação da implementação)

```bash
# Backend
cd backend
pip install -r requirements.txt
uvicorn main:app --reload --host 127.0.0.1 --port 8000

# Frontend
cd frontend
npm install
npm run dev
```
