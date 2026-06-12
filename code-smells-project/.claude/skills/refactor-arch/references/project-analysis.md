# Análise de Projeto — Heurísticas de Detecção (Fase 1)

Detecte tudo por **evidência em arquivo**, nesta ordem de prioridade: manifests → lockfiles → imports no código → extensões de arquivo. Nunca chute.

## 1. Linguagem

| Evidência | Linguagem |
|---|---|
| `requirements.txt`, `pyproject.toml`, `setup.py`, `Pipfile`, arquivos `.py` | Python |
| `package.json`, arquivos `.js`/`.ts`/`.mjs` | Node.js (ou TypeScript se `tsconfig.json`) |
| `composer.json`, arquivos `.php` | PHP |
| `go.mod`, arquivos `.go` | Go |
| `pom.xml`, `build.gradle`, arquivos `.java`/`.kt` | Java / Kotlin |
| `Gemfile`, arquivos `.rb` | Ruby |
| `*.csproj`, arquivos `.cs` | C# / .NET |

Se houver mais de uma linguagem, identifique a principal (a do servidor HTTP) e cite as demais.

## 2. Framework e versões

Procure nas dependências do manifest e confirme nos imports do código:

| Linguagem | Dependência → Framework |
|---|---|
| Python | `flask` → Flask; `django` → Django; `fastapi` → FastAPI |
| Node.js | `express` → Express; `fastify` → Fastify; `koa` → Koa; `@nestjs/core` → NestJS |
| PHP | `laravel/framework` → Laravel; `symfony/*` → Symfony |
| Ruby | `rails` → Rails; `sinatra` → Sinatra |
| Go | `gin-gonic/gin` → Gin; `labstack/echo` → Echo; só stdlib → net/http |

- **Versão:** use a versão pinada do manifest (`flask==3.1.1`) ou o range (`^4.18.2`); se houver lockfile, prefira a versão resolvida nele.
- Liste também as dependências secundárias relevantes (CORS, ORM, clients HTTP).

## 3. Banco de dados

Procure por driver/ORM nas dependências e por uso no código:

| Evidência | Banco/Camada |
|---|---|
| `import sqlite3` (Python) / `require('sqlite3')` ou `better-sqlite3` (Node) | SQLite acesso direto |
| `flask-sqlalchemy`, `sqlalchemy` | SQLite/Postgres/MySQL via ORM (veja a connection string) |
| `psycopg2`, `pg` | PostgreSQL |
| `mysql2`, `pymysql` | MySQL |
| `mongoose`, `pymongo` | MongoDB |
| `sequelize`, `prisma`, `typeorm` | ORM Node (veja o dialect configurado) |

**Tabelas/entidades:** localize `CREATE TABLE ...` (acesso direto), classes `db.Model` / `__tablename__` (SQLAlchemy), schemas (Mongoose/Prisma). Liste os nomes exatos das tabelas no resumo. Note também onde o schema é criado (boot? script de seed? migration?) — isso importa na Fase 3 para não quebrar a inicialização.

## 4. Domínio da aplicação

Infira pelo vocabulário das entidades + rotas, por exemplo:

- produtos, pedidos, itens_pedido, usuarios → **API de E-commerce**
- courses, enrollments, payments → **LMS (plataforma de cursos) com checkout**
- tasks, categories, users → **Task Manager**

Formule em uma linha: tipo de sistema + principais recursos. Em caso de ambiguidade, descreva o que as rotas efetivamente fazem.

## 5. Mapeamento da arquitetura atual

Levante, com `arquivo:linha` quando relevante:

1. **Entry point** — onde o servidor é criado e iniciado.
2. **Roteamento** — onde as rotas são registradas (decorators, `add_url_rule`, `app.get/post`, Blueprints, Routers).
3. **Acesso a dados** — onde vivem as queries/chamadas de ORM.
4. **Regras de negócio** — onde vivem validações, cálculos e fluxos.
5. **Configuração** — onde ficam portas, chaves, credenciais.

Classifique a arquitetura com estes critérios objetivos:

| Classificação | Critério |
|---|---|
| **Monolítica single-file** | Tudo (rotas + negócio + dados) em 1 arquivo |
| **Monolítica multi-file, sem camadas** | Poucos arquivos por tipo técnico, mas responsabilidades misturadas dentro deles (ex.: "models" com SQL + negócio + formatação; rotas com lógica) |
| **Camadas parciais** | Existem diretórios de camadas (`models/`, `routes/`, `services/`...), porém com violações (lógica nas rotas, camadas que se atravessam, módulos não usados) |
| **MVC** | Models, Views/Routes e Controllers separados, dependências na direção correta, config isolada |

Uma classe única que concentra DB + rotas + negócio é "God Class" — registre o nome dela aqui e o finding correspondente na Fase 2.

## 6. Contagem de arquivos analisados

`Source files` = arquivos de código-fonte da aplicação (`.py`, `.js`, ...), **excluindo**: vendor/build (`node_modules/`, `venv/`, `__pycache__/`, `dist/`), `.git/`, `.claude/`, lockfiles, bancos `.db`, documentação (`README.md`, `*.http`) e arquivos vazios de marcação de pacote (`__init__.py` vazios — conte-os apenas se contiverem código). Manifests (`requirements.txt`, `package.json`) contam como analisados, mas não como source files; cite-os em `Dependencies`.

## 7. Output da Fase 1

Preencha o bloco `PHASE 1: PROJECT ANALYSIS` definido em `references/report-template.md`, com uma linha por campo. Não invente campos que não foram detectados — use `n/a` com uma observação curta.
