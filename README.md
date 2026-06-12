# Skill `refactor-arch` — Auditoria e Refatoração Arquitetural Automatizada

Entrega do desafio de **Criação de Skills** (MBA IA — Fullcycle). O enunciado completo está em [`docs/DESAFIO.md`](docs/DESAFIO.md).

Foi construída uma skill de Claude Code (`/refactor-arch`) que, em 3 fases sequenciais, **analisa** a stack de qualquer projeto backend, **audita** o código contra um catálogo de 19 anti-patterns (gerando relatório com severidade e `arquivo:linha`) e — após confirmação humana obrigatória — **refatora** o projeto para o padrão MVC, validando boot e endpoints ao final. A skill foi executada nos 3 projetos do desafio (2× Python/Flask, 1× Node/Express) por um **agente imparcial em contexto limpo**, e os 3 passaram em todos os critérios de aceite.

| | Projeto | Stack | Findings (C/H/M/L) | Pós-refatoração |
|---|---|---|---|---|
| 1 | `code-smells-project` | Python + Flask 3.1.1 | 18 (6/4/4/4) | ✅ 18/18 resolvidos, app validada |
| 2 | `ecommerce-api-legacy` | Node.js + Express 4.18 | 17 (5/4/4/4) | ✅ 17/17 resolvidos, app validada |
| 3 | `task-manager-api` | Python + Flask 3.0.0 | 15 (4/3/5/3) | ✅ 15/15 resolvidos, app validada |

---

## A) Análise Manual

Antes de criar a skill, os 3 projetos foram lidos na íntegra. Abaixo, os principais problemas identificados manualmente (a lista completa detectada pela skill está nos relatórios em [`reports/`](reports/)).

### Projeto 1 — `code-smells-project` (Python/Flask, API de E-commerce)

| Severidade | Problema | Evidência | Por que é relevante |
|---|---|---|---|
| CRITICAL | SQL Injection generalizado | `models.py:28,47-50,109-111,289-297` — queries por concatenação de strings em ~10 funções, incluindo o login | Permite ler/alterar/destruir o banco e burlar autenticação; é a falha de segurança mais explorada em APIs |
| CRITICAL | Console SQL sem autenticação | `app.py:59-78` — `POST /admin/query` executa SQL arbitrário vindo do body | Backdoor completo: qualquer cliente exfiltra ou destrói tudo |
| CRITICAL | Senhas em texto plano expostas pela API | `models.py:79-87,94-103` — `senha` incluída no dict de resposta de `GET /usuarios`; seeds plaintext em `database.py:75-82` | Vazamento direto de credenciais a qualquer cliente; viola LGPD |
| CRITICAL | SECRET_KEY hardcoded e vazada no `/health` | `app.py:7`, `controllers.py:289` | Segredo commitado + endpoint público que o expõe permite forjar sessões |
| HIGH | Conexão global de banco com `check_same_thread=False` | `database.py:4-10` | Estado global mutável compartilhado entre threads: race conditions e impossibilidade de escalar |
| MEDIUM | Queries N+1 triplas | `models.py:171-233` — por pedido, busca itens; por item, busca produto (1+N+N×M) | Latência cresce com o volume; degrada com dados reais |
| MEDIUM | Validações duplicadas em create/update | `controllers.py:28-54` vs `72-90` | Regras divergem silenciosamente quando uma cópia muda |
| LOW | `print()` como logging | `controllers.py` (15+ ocorrências) | Sem níveis/timestamp/destino; inviável operar em produção |
| LOW | Magic numbers no cálculo de desconto | `models.py:256-262` — `10000/5000/1000`, `0.1/0.05/0.02` | Regra de negócio opaca e difícil de manter |

### Projeto 2 — `ecommerce-api-legacy` (Node/Express, LMS com checkout)

| Severidade | Problema | Evidência | Por que é relevante |
|---|---|---|---|
| CRITICAL | Credenciais de produção hardcoded | `src/utils.js:1-7` — `dbPass`, `paymentGatewayKey: "pk_live_..."`, SMTP | Chave live de gateway commitada = fraude financeira imediata para qualquer leitor do repositório |
| CRITICAL | Número de cartão + chave do gateway em log | `src/AppManager.js:45` — `console.log` com `cc` completo | Viola PCI-DSS diretamente; logs vazam dados de pagamento |
| CRITICAL | God Class `AppManager` | `src/AppManager.js:4-141` — schema, seeds, rotas, negócio e dados numa classe | Anula a separação de responsabilidades; nada é testável em isolamento |
| HIGH | "Criptografia" caseira de senha | `src/utils.js:17-23` — `badCrypto` com base64 truncado + senha default `"123456"` (`AppManager.js:68`) | Não é hash: reversível e com default conhecido — todas as contas comprometidas |
| HIGH | Callback hell com erros engolidos | `AppManager.js:28-78` (5 níveis), `:104-106` ignoram `err` | Falhas de banco passam silenciosamente como sucesso |
| MEDIUM | N+1 no relatório financeiro | `AppManager.js:80-129` — 1+C+C×E×2 queries com contadores manuais de "pending" | Performance degrada e o padrão de sincronização manual é frágil |
| MEDIUM | DELETE deixa dados órfãos | `AppManager.js:131-137` — a própria resposta admite: "matrículas e pagamentos ficaram sujos" | Sem FK/cascade o relatório financeiro corrompe (alunos "Unknown") |
| LOW | Nomenclatura críptica | `AppManager.js:29-34` — `u`, `e`, `p`, `cid`, `cc` | Contrato da API e código ilegíveis |
| LOW | Dead code exportado | `utils.js:10` — `totalRevenue` nunca lido/atualizado | Falsa sensação de funcionalidade |

### Projeto 3 — `task-manager-api` (Python/Flask, Task Manager — parcialmente organizado)

| Severidade | Problema | Evidência | Por que é relevante |
|---|---|---|---|
| CRITICAL | MD5 sem salt para senhas | `models/user.py:29,32` | MD5 é quebrado por rainbow table em segundos; não é algoritmo de senha |
| CRITICAL | Hash de senha exposto na API | `models/user.py:21` — `to_dict()` inclui `password`, retornado em GET/POST/PUT `/users` e `/login` | Expõe o material de autenticação de todos os usuários |
| CRITICAL | Token de login fake e nenhuma autenticação real | `routes/user_routes.py:210` — `'fake-jwt-token-' + id`, previsível; nenhum endpoint valida | DELETEs e relatórios de produtividade acessíveis anonimamente |
| HIGH | Lógica de negócio nas rotas + duplicação sêxtupla | cálculo de overdue reimplementado em 6 pontos (`task_routes.py:30-39,71-80,283-287`; `user_routes.py:171-180`; `report_routes.py:33-43,132-135`) enquanto `Task.is_overdue()` existe e não é usado | O projeto "tem camadas" mas não as usa — pior dos dois mundos |
| MEDIUM | APIs deprecated | `datetime.utcnow()` (13 usos — deprecated no Python 3.12+) e `Model.query.get()` (11 usos — legacy na SQLAlchemy 2.x) | Warnings hoje, quebra em upgrades; equivalentes modernos: `datetime.now(timezone.utc)` e `db.session.get()` |
| MEDIUM | N+1 em `get_tasks` e relatórios | `routes/task_routes.py:42-57` — 2 queries extras por task; `report_routes.py:53-68` | 201 queries para listar 100 tasks |
| MEDIUM | Deleções órfãs | `user_routes.py:140-142` deleta tasks em loop manual; `delete_category` ignora as tasks da categoria | Integridade do banco fica por conta da sorte |
| LOW | Constantes existem mas não são usadas | `utils/helpers.py:110-116` define `VALID_STATUSES` etc.; rotas repetem as listas inline | Dead code + duplicação simultâneos |
| LOW | Imports não usados em massa | `app.py:7`, `task_routes.py:7`, `helpers.py:2-7` | Ruído e dependências fantasma |

---

## B) Construção da Skill

### Estrutura

```
.claude/skills/refactor-arch/
├── SKILL.md                            # orquestrador: regras globais + 3 fases
└── references/
    ├── project-analysis.md             # heurísticas de detecção (Fase 1)
    ├── antipattern-catalog.md          # 19 anti-patterns com sinais e severidade (Fase 2)
    ├── report-template.md              # formatos exatos de output das 3 fases
    ├── mvc-guidelines.md               # MVC alvo, regras por camada, validação (Fase 3)
    └── refactoring-playbook.md         # 15 transformações antes/depois (Fase 3)
```

### Decisões de design

1. **SKILL.md é o prompt orquestrador; conhecimento vive nas referências** (progressive disclosure). O SKILL.md diz *o que fazer e quando ler cada referência*; o domínio (heurísticas, catálogo, templates, playbook) fica nos arquivos de apoio. Isso mantém o contexto enxuto e cada fase carrega só o que precisa.
2. **Regras globais explícitas**: Fases 1-2 são 100% read-only (proibido modificar arquivos antes da confirmação), todo achado exige `arquivo:linha` real, contrato de API é preservado, outputs seguem template fixo.
3. **Catálogo com IDs (`AP-xx`) cruzados com o playbook (`PB-xx`)** — cada finding do relatório referencia o anti-pattern do catálogo e a transformação que o corrige, dando rastreabilidade da auditoria à refatoração.
4. **Política de "Security Contract Changes"**: o maior dilema do desafio é que "endpoints originais devem continuar respondendo", mas alguns endpoints/campos *são* a vulnerabilidade. A regra adotada: campos sensíveis saem das respostas; endpoints administrativos passam a exigir `X-Admin-Token` (lido do ambiente; sem a variável → 403, seguro por default); backdoors irrecuperáveis (console SQL) são protegidos e *marcados* para remoção — nunca removidos sem aprovação explícita. Toda mudança aparece numa seção própria do output final.
5. **Validação é parte da skill, não etapa manual**: a Fase 3 só pode declarar sucesso após instalar dependências de forma idiomática (venv/npm), subir a aplicação, exercitar todos os endpoints originais (incluindo um fluxo de escrita e um caso de erro) e encerrar o processo.

### Quais anti-patterns entraram no catálogo e por quê

O catálogo tem **19 anti-patterns** (mínimo exigido: 8) com severidade distribuída — 6 CRITICAL, 4 HIGH, 5 MEDIUM, 4 LOW. Foram derivados da análise manual e **generalizados** para qualquer stack:

- **CRITICAL** (segurança/arquitetura): SQL Injection, segredos hardcoded, armazenamento inseguro de senha, exposição de dados sensíveis em respostas/logs, God Class, endpoints destrutivos sem auth — todos presentes em pelo menos um dos 3 projetos.
- **HIGH** (violações MVC/SOLID): lógica de negócio em rotas, estado global mutável, error handling não centralizado, configuração insegura de produção (debug/CORS).
- **MEDIUM** (qualidade/performance): N+1, duplicação, **APIs deprecated** (requisito explícito — com tabela de equivalentes modernos por ecossistema: `datetime.utcnow()`→`now(timezone.utc)`, `Query.get()`→`session.get()`, callbacks errback→async/await, `new Buffer()`→`Buffer.from()` etc.), validação ausente, integridade referencial.
- **LOW** (legibilidade): print como logging, magic numbers, nomenclatura, dead code.

Cada item traz **sinais de detecção acionáveis** (padrões de grep por stack, ex.: "query montada com `'...' + var`" e não "código ruim") — seguindo a dica do enunciado.

### Como a skill é agnóstica de tecnologia

- **Nada de stack assumida**: a Fase 1 detecta linguagem/framework/banco por evidência (manifests → lockfiles → imports), com tabelas de heurísticas para Python, Node, PHP, Go, Java, Ruby e C#.
- **Sinais de detecção por padrão, não por API**: cada anti-pattern descreve o *padrão* (ex.: "query dentro de loop") com exemplos em mais de uma stack.
- **Playbook transponível**: as 15 transformações mostram o *desenho* da solução com exemplos em Python e Node, e instruem a transpor para a stack detectada (ex.: hash de senha = werkzeug no Flask, `crypto.scrypt` da stdlib no Node — sem dependências novas).
- **Estruturas-alvo idiomáticas por linguagem** (Blueprint↔Router, decorator↔middleware) e **dois modos de aplicação**: reestruturação completa para monolitos vs. **evolução incremental** para projetos já parcialmente organizados (preservar o que está correto, não renomear por renomear).
- **Prova prática**: a mesma skill, copiada byte a byte para os 3 projetos, executou as 3 fases corretamente em Flask "flat", Express com God Class e Flask com camadas parciais.

### Desafios encontrados e como foram resolvidos

| Desafio | Solução |
|---|---|
| Preservar endpoints vs. corrigir vulnerabilidades que *são* endpoints | Política de Security Contract Changes (item 4 acima): proteger por token de ambiente em vez de remover; remoção só com aprovação |
| Pausa obrigatória da Fase 2 em execução não-interativa | O SKILL.md instrui: em modo headless, encerrar o turno na pergunta `[y/n]` sem nunca assumir o "y"; a Fase 3 roda num segundo turno via `claude -p --resume <session> "y"` |
| Projeto 3 já organizado — risco de a skill reescrever tudo | Guidelines com modo incremental explícito; resultado: arquivos existentes foram *modificados* (não recriados) e `routes/`, `models/`, `services/`, `utils/` preservados |
| `datetime.now(timezone.utc)` é timezone-aware; banco tinha datas naive | Playbook (PB-09) avisa da armadilha; o agente criou um helper `utcnow()` que normaliza, evitando quebra nas comparações de overdue |
| Validação no macOS: AirPlay ocupa a porta 5000 e responde 403 | Artefato de ambiente (não do código): validar via `127.0.0.1` (IPv4) e aguardar o log de boot do Flask antes dos curls |

---

## C) Resultados

### Execuções (agente imparcial)

Cada projeto foi auditado e refatorado por uma sessão `claude -p` **separada e com contexto limpo** (modelo `claude-sonnet-4-6`), que descobriu a skill via runtime real do Claude Code. As Fases 1-2 rodaram com allowlist somente leitura; a Fase 3 só rodou após confirmação humana real (resume da sessão com `"y"`).

| Projeto | Fases 1-2 | Fase 3 | Findings | Resolvidos |
|---|---|---|---|---|
| code-smells-project | 227s · $0.41 | 678s · $2.07 | 18 (6C/4H/4M/4L) | 18/18 |
| ecommerce-api-legacy | 241s · $0.36 | 392s · $1.13 | 17 (5C/4H/4M/4L) | 17/17 |
| task-manager-api | 220s · $0.54 | 677s · $2.18 | 15 (4C/3H/5M/3L) | 15/15 |

Relatórios completos (output verbatim da Fase 2): [`reports/audit-project-1.md`](reports/audit-project-1.md) · [`reports/audit-project-2.md`](reports/audit-project-2.md) · [`reports/audit-project-3.md`](reports/audit-project-3.md)

### Antes / Depois

**Projeto 1 — code-smells-project** (reestruturação completa)

```
ANTES                          DEPOIS
app.py  (rotas+admin+config)   app.py (composition root) · config/settings.py
controllers.py (16 handlers    controllers/{produto,usuario,pedido,admin}_controller.py
  com try/except idênticos)    views/routes.py (1 linha por rota)
models.py (God Module: SQL+    models/{produto,usuario,pedido}_model.py (parametrizado)
  negócio+formatação, 4        middlewares/{error_handler,auth}.py
  domínios, 18 pontos de SQLi) database.py (flask.g por request) · .env.example
database.py (conexão global)
```

**Projeto 2 — ecommerce-api-legacy** (decomposição da God Class)

```
ANTES                          DEPOIS
src/app.js                     src/app.js (composition root) · src/config/index.js
src/AppManager.js (God Class:  src/models/{user,course,enrollment,payment,audit}Model.js
  schema+seeds+rotas+negócio,    + models/constants.js (PAYMENT_STATUS)
  callbacks 5 níveis)          src/controllers/{checkout,report,user}Controller.js
src/utils.js (segredos pk_live src/routes/index.js · src/middlewares/{adminAuth,errorHandler}.js
  + badCrypto + globais)       src/database.js (promisificado, FK CASCADE) · .env.example
```

**Projeto 3 — task-manager-api** (evolução incremental — camadas existentes preservadas)

```
ANTES                          DEPOIS (✱ = novo; demais arquivos evoluídos no lugar)
app.py (config inline)         app.py (create_app) · ✱ config/settings.py
models/ (MD5; password no      models/ (werkzeug hash; to_dict sem password; constantes)
  to_dict; utcnow)             ✱ controllers/{task,user,category,report}_controller.py
routes/ (negócio inline,       routes/ (finas; ✱ category_routes.py separado de reports)
  Query.get, bare except)      ✱ middlewares/{auth,error_handler}.py
services/ (dead code, creds)   services/ (integrado ao fluxo; creds via env)
utils/helpers.py (dead code)   utils/helpers.py (enxuto: utcnow() + validate_email())
```

### Checklist de validação (preenchido por projeto)

| Item | P1 | P2 | P3 |
|---|---|---|---|
| **Fase 1** — Linguagem detectada corretamente | ✅ Python | ✅ Node.js | ✅ Python |
| Framework detectado corretamente | ✅ Flask 3.1.1 | ✅ Express 4.18.2 | ✅ Flask 3.0.0 |
| Domínio descrito corretamente | ✅ E-commerce | ✅ LMS + checkout | ✅ Task Manager |
| Nº de arquivos analisados condiz | ✅ 4 | ✅ 3 | ✅ 11 |
| **Fase 2** — Relatório segue o template | ✅ | ✅ | ✅ |
| Cada finding tem arquivo e linhas exatos | ✅ | ✅ | ✅ |
| Findings ordenados por severidade | ✅ | ✅ | ✅ |
| Mínimo de 5 findings | ✅ 18 | ✅ 17 | ✅ 15 |
| Detecção de APIs deprecated (se aplicável) | ✅ checado, n/a | ✅ callbacks errback | ✅ utcnow ×13, Query.get ×11 |
| Pausa e confirmação antes da Fase 3 | ✅ | ✅ | ✅ |
| **Fase 3** — Estrutura segue MVC | ✅ | ✅ | ✅ |
| Config extraída (sem hardcoded) | ✅ | ✅ | ✅ |
| Models abstraem dados | ✅ | ✅ | ✅ |
| Views/Routes separadas | ✅ | ✅ | ✅ |
| Controllers concentram o fluxo | ✅ | ✅ | ✅ |
| Error handling centralizado | ✅ | ✅ | ✅ |
| Entry point claro | ✅ | ✅ | ✅ |
| Aplicação inicia sem erros | ✅ | ✅ | ✅ |
| Endpoints originais respondem | ✅ 18 casos | ✅ 9 casos | ✅ 22 casos |

### Logs das aplicações após a refatoração (validação independente, via curl)

**Projeto 1** (`venv/bin/python app.py`, banco recriado do zero):

```
GET /            -> 200        POST /login ok    -> 200       POST /pedidos -> 201
GET /health      -> 200 (sem   POST /login bad   -> 401       GET  /pedidos -> 200
  secret_key/db_path/debug)    SQLi no login     -> 401 ✓     PUT  /pedidos/1/status -> 200
GET /produtos    -> 200        POST /produtos    -> 201       admin sem token -> 403
GET /produtos/999-> 404        preço negativo    -> 400       relatorio s/ token -> 403
GET /usuarios    -> 200 (sem campo senha ✓)
```

**Projeto 2** (`node src/app.js`):

```
checkout card 4xxx -> 200 {"msg":"Sucesso","enrollment_id":2}   (contrato preservado)
checkout card 5xxx -> 400      financial-report sem token -> 403 / com token -> 200
campos faltando    -> 400      DELETE /users/1 sem token  -> 403 / com token -> 200
curso inexistente  -> 404      relatório pós-delete: receita recalculada sem
                                órfãos (CASCADE ✓ — antes ficavam "sujos no banco")
```

**Projeto 3** (`python seed.py && python app.py` — seed: 3 usuários, 4 categorias, 10 tasks):

```
GET /tasks       -> 200 (10 itens, com overdue via Task.is_overdue)
search priority=abc -> 400 (antes: 500 ✓)     POST /tasks -> 201 | inválido -> 400
GET /users/1     -> 200 (sem password ✓)      PUT /tasks/1 -> 200
POST /login      -> 200 (sem token fake ✓)    reports sem token -> 403 / com -> 200
GET /categories  -> 200 | POST -> 201          DELETE task sem token -> 403 / com -> 200
```

### Observações sobre o comportamento em stacks diferentes

- **Flask "flat" (P1)**: a skill aplicou a estrutura-alvo completa e migrou domínio a domínio; reconheceu corretamente que `werkzeug` já vem com o Flask (zero dependências novas).
- **Express (P2)**: adaptou os mesmos conceitos para o idioma da stack — Router no lugar de Blueprint, middleware `(err, req, res, next)` no lugar de `@errorhandler`, `crypto.scryptSync` da stdlib no lugar de werkzeug — e converteu o estilo errback para async/await promisificado.
- **Flask parcialmente organizado (P3)**: o modo incremental funcionou como projetado — o diff mostra arquivos *modificados* (não deletados/recriados), `routes/` continuou sendo a casa do roteamento e as camadas novas (`controllers/`, `config/`, `middlewares/`) entraram ao lado das existentes. A skill também detectou que constantes/validadores já existiam no projeto e passou a usá-los em vez de criar duplicatas.
- Em todos os casos a Fase 2 **pausou de fato** (encerrou o turno na pergunta `[y/n]`) e nenhum arquivo foi tocado antes da confirmação (verificado com `git status` após cada auditoria).

---

## D) Como Executar

### Pré-requisitos

- [Claude Code](https://docs.anthropic.com/en/docs/claude-code/overview) instalado e autenticado (`claude --version`)
- Python 3.10+ (projetos 1 e 3) e Node.js 18+ (projeto 2)

### Executar a skill em cada projeto

A skill já está dentro dos 3 projetos (`.claude/skills/refactor-arch/`). Modo interativo:

```bash
cd code-smells-project && claude "/refactor-arch"     # Projeto 1
cd ../ecommerce-api-legacy && claude "/refactor-arch" # Projeto 2
cd ../task-manager-api && claude "/refactor-arch"     # Projeto 3
```

A skill imprime a análise (Fase 1) e o relatório de auditoria (Fase 2), e **pergunta antes de modificar qualquer arquivo**: `Proceed with refactoring (Phase 3)? [y/n]`.

Modo headless imparcial (como nesta entrega — a pausa vira um segundo comando):

```bash
cd code-smells-project
claude -p "/refactor-arch" --model sonnet \
  --allowedTools "Skill,Read,Glob,Grep,Bash(ls:*),Bash(find:*),Bash(wc:*),Bash(grep:*)" \
  --output-format json            # Fases 1-2 (read-only); anote o session_id
# revise o relatório e então:
claude -p --resume <session_id> "y" --model sonnet \
  --allowedTools "Skill,Read,Glob,Grep,Write,Edit,Bash"   # Fase 3
```

### Validar que a refatoração funcionou

> No macOS, use `127.0.0.1` (o AirPlay ocupa `localhost:5000` via IPv6 e responde 403).
> Endpoints administrativos exigem `ADMIN_TOKEN` no ambiente — sem ele, respondem 403 (seguro por default).

```bash
# Projeto 1
cd code-smells-project
python -m venv venv && venv/bin/pip install -r requirements.txt
ADMIN_TOKEN=meu-token venv/bin/python app.py
curl http://127.0.0.1:5000/health
curl http://127.0.0.1:5000/produtos
curl -X POST http://127.0.0.1:5000/login -H 'Content-Type: application/json' \
  -d '{"email":"admin@loja.com","senha":"admin123"}'
curl -H 'X-Admin-Token: meu-token' http://127.0.0.1:5000/relatorios/vendas

# Projeto 2
cd ecommerce-api-legacy
npm install && ADMIN_TOKEN=meu-token npm start
curl -X POST http://127.0.0.1:3000/api/checkout -H 'Content-Type: application/json' \
  -d '{"usr":"Gui","eml":"gui@fullcycle.com.br","pwd":"senhaforte","c_id":2,"card":"4111222233334444"}'
curl -H 'X-Admin-Token: meu-token' http://127.0.0.1:3000/api/admin/financial-report

# Projeto 3
cd task-manager-api
python -m venv venv && venv/bin/pip install -r requirements.txt
venv/bin/python seed.py
ADMIN_TOKEN=meu-token venv/bin/python app.py
curl http://127.0.0.1:5000/tasks
curl -H 'X-Admin-Token: meu-token' http://127.0.0.1:5000/reports/summary
```

Cada projeto tem um `.env.example` documentando todas as variáveis de ambiente disponíveis.

### Estrutura do repositório

```
├── README.md                       # esta documentação
├── docs/DESAFIO.md                 # enunciado original do desafio
├── code-smells-project/            # Projeto 1 refatorado + .claude/skills/refactor-arch/
├── ecommerce-api-legacy/           # Projeto 2 refatorado + cópia da skill
├── task-manager-api/               # Projeto 3 refatorado + cópia da skill
└── reports/
    ├── audit-project-1.md          # output da Fase 2 — projeto 1
    ├── audit-project-2.md          # output da Fase 2 — projeto 2
    └── audit-project-3.md          # output da Fase 2 — projeto 3
```
