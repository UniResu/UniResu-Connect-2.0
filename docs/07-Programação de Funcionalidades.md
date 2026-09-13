# Programação de Funcionalidades

<span style="color:red">Pré-requisitos: <a href="02-Especificação do Projeto.md">Especificação do Projeto</a>, <a href="04-Metodologia.md">Metodologia</a>, <a href="03-Projeto de Interface.md">Projeto de Interface</a>, <a href="05-Arquitetura da Solução.md">Arquitetura da Solução</a></span>

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

| ID (Doc 02) | Descrição do Requisito | Artefatos produzidos | Aluno(a) responsável |
|----|-------------------------|----------------------|----------------------|
| RF-001, RF-002 e RF-004 | Autenticar usuários com email institucional e senha, com sessão via JWT e fluxo de recuperação de senha | `backend/auth/autenticacao.py`, `backend/routes/auth_routes.py`, `frontend/src/app/login/`, `frontend/src/app/registrar/`, `frontend/src/contexts/AuthContext.tsx` | Daniel Pereira Santos da Silva e Davi Lopes Rodrigues |
| RF-003 e RF-006 | Autenticar pesquisadores via ORCID (OAuth 2.0) e sincronizar perfil | `backend/controllers/orcid_controller.py`, `backend/routes/auth_routes.py`, `frontend/src/app/callback/orcid/`, `frontend/src/app/u/[orcidId]/` | Juliana Gimenes Müller |
| RF-005 | Gerenciar perfis de usuários (visualização e edição) | `backend/controllers/perfil_controller.py`, `backend/routes/perfil_routes.py`, `frontend/src/app/perfil/`, `frontend/src/app/perfil/editar/` | Maria Eduarda Siqueira de Medeiros |
| RF-007, RF-008, RF-009 e RF-018 | CRUD de projetos com filtros e paginação | `backend/controllers/projeto_controller.py`, `backend/routes/projeto_routes.py`, `backend/models/projeto_model.py`, `frontend/src/app/projetos/`, `frontend/src/app/projetos/gerenciar/` | Lucas Eduardo Sanches Cordeiro |
| RF-010, RF-017 e RF-019 | Candidatar-se a projetos com envio de currículo, prevenção de duplicidade e consulta do histórico de candidaturas | `backend/controllers/candidatura_controller.py`, `backend/routes/candidatura_routes.py`, `backend/models/candidatura_model.py`, `frontend/src/app/candidaturas/` | Pedro de Magalhães Leitão |
| RF-011, RF-012, RF-013 e RF-021 | Fórum de discussão com criação de tópicos, respostas, busca e reações | `backend/routes/forum_routes.py`, `backend/models/forum_model.py`, `frontend/src/app/forum/` | José Murilo Almeida do Nascimento |
| RF-020 | Notificar professores por email ao receber candidaturas | `backend/controllers/candidatura_controller.py`, integração Resend | Matheus Gabriel Ramos de Melo |

## Evidências visuais das funcionalidades implementadas

> Prints reutilizados do documento [04 - Projeto de Interface](04-Projeto%20de%20Interface.md), como evidência das telas implementadas.

### RF-001, RF-002 e RF-004 (cadastro/login/recuperação)
<img width="900" alt="Login" src="https://github.com/user-attachments/assets/45050462-a705-4efd-9bbf-e8eb78370599" />

### RF-003 e RF-006 (ORCID e sincronização de perfil)
<img width="900" alt="Perfil ORCID" src="https://github.com/user-attachments/assets/058c04d8-8343-4d11-a305-96ad876d4ba0" />

### RF-005 (perfil e edição)
<img width="900" alt="Edição de perfil" src="https://github.com/user-attachments/assets/5278099d-7302-4c32-bfb6-5408421d4972" />

### RF-007, RF-008, RF-009 e RF-018 (projetos)
<img width="900" alt="Projetos com busca e filtros" src="https://github.com/user-attachments/assets/bf76ed4a-dc58-4ea0-a51a-615bb59d374a" />

### RF-010, RF-017 e RF-019 (candidaturas)
<img width="900" alt="Página de projetos para candidatura" src="https://github.com/user-attachments/assets/d1d02fa4-cbae-440d-8169-37fc6194b6f5" />

### RF-011, RF-012, RF-013 e RF-021 (fórum)
<img width="900" alt="Página de fórum" src="https://github.com/user-attachments/assets/40be6f4c-6682-4a9c-82ac-47a157e14e45" />

### RF-020 (notificação por email)
<img width="900" alt="Fluxo de candidatura que dispara notificação" src="https://github.com/user-attachments/assets/5b0d748a-1ed8-452f-82bc-dbad8d286e82" />

## Instruções de acesso e verificação

- **Aplicação (produção)**: https://uniresu.org  
- **API (Swagger/OpenAPI)**: https://api.uniresu.org/docs  
- **Status da checagem em 2026-09-13**: ambos os domínios não responderam por resolução DNS no ambiente de validação (`Could not resolve host`), sendo necessária revalidação em rede externa.
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
