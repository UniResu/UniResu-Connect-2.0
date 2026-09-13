# Arquitetura da Solução

## Diagrama de Classes

![Diagrama de classes](https://raw.githubusercontent.com/UniResu/UniResu-Connect-2.0/29ce2bdf916914f74e922aff7347f0967fb6590b/docs/diagrama-de-classes-png.png)

## Modelo ER (Projeto Conceitual)

<img width="4054" height="2261" alt="Diagrama em branco" src="https://github.com/user-attachments/assets/9114865d-18b3-4b6a-b9d8-fff28513e6f9" />

## Projeto da Base de Dados

<img width="605" height="954" alt="mermaid_diag" src="https://github.com/user-attachments/assets/7c0fb1f7-1c0a-4f34-9557-f9f4b3249f6f" />

## ATENÇÃO!!!

Os três artefatos — **Diagrama de Classes, Modelo ER e Projeto da Base de Dados** — devem ser desenvolvidos de forma sequencial e integrada, garantindo total coerência e compatibilidade entre eles. O diagrama de classes orienta a estrutura e o comportamento do software; o modelo ER traduz essa estrutura para o nível conceitual dos dados; e o projeto da base de dados materializa essas definições no formato físico (tabelas, colunas, chaves e restrições). A construção isolada ou desconexa desses elementos pode gerar inconsistências, dificultar a implementação e comprometer a qualidade do sistema.

## Tecnologias Utilizadas

| Camada         | Tecnologias                                      |
| -------------- | ------------------------------------------------ |
| Frontend       | Next.js 16, React 19                             |
| Backend        | FastAPI                                          |
| Banco de Dados | MongoDB Atlas                                    |
| Infraestrutura | Docker, Render, Cloudflare                       |

```mermaid
flowchart LR
    U[Usuário] --> CF[Cloudflare]
    CF --> FE[Frontend<br/>Next.js 16 + React 19<br/>uniresu.org]
    FE --> API[Backend<br/>FastAPI<br/>api.uniresu.org]
    API --> DB[(MongoDB Atlas)]
    DB --> API
    API --> FE
    FE --> U
```

## Hospedagem

- **Aplicação (produção)**: [https://uniresu.org/](https://uniresu.org/)
- **API (Swagger/OpenAPI)**: [https://api.uniresu.org/docs](https://api.uniresu.org/docs)
