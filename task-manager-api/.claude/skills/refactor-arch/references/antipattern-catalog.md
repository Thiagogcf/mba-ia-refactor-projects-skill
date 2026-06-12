# Catálogo de Anti-Patterns (Fase 2)

Verifique **cada arquivo-fonte contra cada item** deste catálogo. Os sinais de detecção são padrões concretos e acionáveis — use busca textual (grep) para localizar candidatos e confirme lendo o trecho. Cada item aponta a transformação correspondente no playbook (`PB-xx`).

**Escala de severidade:**

- **CRITICAL** — falha grave de segurança ou arquitetura: expõe dados sensíveis, permite ataque, ou anula completamente a separação de responsabilidades.
- **HIGH** — forte violação de MVC/SOLID que compromete manutenção e testes.
- **MEDIUM** — padronização, duplicação, performance moderada, validações ausentes.
- **LOW** — legibilidade, nomenclatura, magic numbers.

Se uma ocorrência concreta agravar o impacto (ex.: validação ausente que permite burlar pagamento), suba a severidade e justifique no finding.

---

## CRITICAL

### AP-01 — SQL Injection — **CRITICAL**
**Sinais de detecção:**
- Query montada com concatenação/interpolação de valores externos: `"SELECT ... WHERE x = '" + var + "'"`, f-strings/template literals com variáveis dentro do SQL.
- Ausência de placeholders (`?`, `%s`, `$1`) em chamadas `execute`/`run`/`query` que recebem dados do request.
- Endpoint que recebe SQL pronto do cliente (`request.get_json()["sql"]`, `req.body.query`) — caso extremo: console SQL exposto.
**Impacto:** leitura/alteração/destruição arbitrária do banco; bypass de login.
**Correção:** → PB-01 (queries parametrizadas) e PB-14 (remover/proteger console SQL).

### AP-02 — Credenciais e segredos hardcoded — **CRITICAL**
**Sinais de detecção:**
- Atribuições literais para `SECRET_KEY`, `*_PASSWORD`, `*_KEY`, `token`, `dbPass`, chaves de gateway (`pk_live_...`, `sk_...`), credenciais SMTP.
- Connection strings com usuário/senha embutidos; configs `{ dbUser: "...", dbPass: "..." }` commitadas.
**Impacto:** segredo vaza com o repositório; rotação exige deploy; chave de produção utilizável por qualquer leitor do código.
**Correção:** → PB-02 (módulo de config + variáveis de ambiente + `.env.example`).

### AP-03 — Armazenamento inseguro de senhas — **CRITICAL**
**Sinais de detecção:**
- Senha persistida em texto plano (INSERT direto do valor recebido) ou comparada com igualdade simples no login.
- Hash quebrado/ingênuo: `md5(...)`, `sha1(...)` sem salt, "crypto caseiro" (base64, substring, loops de concatenação).
- Senha default embutida (`pwd || "123456"`).
**Impacto:** vazamento do banco compromete todas as contas; senhas reutilizadas pelos usuários ficam expostas.
**Correção:** → PB-03 (hash com algoritmo de senha real: werkzeug/bcrypt/scrypt + salt).

### AP-04 — Exposição de dados sensíveis em respostas e logs — **CRITICAL**
**Sinais de detecção:**
- Serializadores (`to_dict`, SELECT *) que incluem `senha`/`password`/hash em respostas de API.
- Logs com dados de cartão, tokens, chaves (`console.log`/`print` de `card`, `paymentGatewayKey`).
- Endpoints de diagnóstico (`/health`, `/debug`) revelando `SECRET_KEY`, paths, flags de debug, config interna.
**Impacto:** vazamento direto de credenciais e dados regulados (PCI/LGPD) para clientes e logs.
**Correção:** → PB-03 (serialização sem campos sensíveis) e PB-12 (logging com redação).

### AP-05 — God Class / God Module — **CRITICAL**
**Sinais de detecção:**
- Um arquivo/classe concentrando 3+ responsabilidades: criação de schema, seeds, registro de rotas, regras de negócio, integração externa.
- Métodos que recebem o `app` e registram todas as rotas com handlers inline (`setupRoutes(app)`).
- "models" com SQL + validação + formatação + cálculo para vários domínios diferentes no mesmo arquivo.
**Impacto:** impossível testar em isolamento; qualquer mudança arrisca tudo; merge conflicts constantes.
**Correção:** → PB-04 (decompor em config/models/controllers/routes por domínio).

### AP-06 — Endpoints destrutivos/administrativos sem autenticação — **CRITICAL**
**Sinais de detecção:**
- Rotas que apagam/resetam dados (`/admin/reset-db`, DELETE em massa) sem verificação de identidade/permissão.
- Rotas administrativas (relatórios financeiros, execução de query) acessíveis anonimamente.
- Inexistência de middleware/decorator de autenticação no projeto inteiro apesar de haver login.
**Impacto:** qualquer cliente da rede destrói ou exfiltra os dados.
**Correção:** → PB-14 (proteção por credencial de ambiente; remoção apenas com aprovação explícita).

---

## HIGH

### AP-07 — Lógica de negócio em rotas/controllers — **HIGH**
**Sinais de detecção:**
- Handlers HTTP com blocos longos de validação campo a campo, cálculos (totais, descontos, status), regras condicionais de domínio e efeitos colaterais (notificações) inline.
- Rotas que montam dicts/objetos de resposta campo a campo em vez de delegar à serialização do model.
- Decisões de negócio tomadas no handler (ex.: aprovar pagamento por prefixo do cartão).
**Impacto:** regras impossíveis de testar sem HTTP; duplicação entre endpoints; controllers gigantes.
**Correção:** → PB-05 (mover regra para models/services; controller só orquestra).

### AP-08 — Estado global mutável — **HIGH**
**Sinais de detecção:**
- Conexão de banco em variável global de módulo (`db_connection = None` + `global`), caches em dicionário global (`globalCache = {}`), acumuladores globais (`totalRevenue`).
- `check_same_thread=False` para contornar compartilhamento de conexão SQLite entre threads.
- Estado de aplicação guardado em memória de processo (listas de notificações etc.) que se perde no restart.
**Impacto:** race conditions, vazamento de estado entre requests, impossibilidade de escalar horizontalmente.
**Correção:** → PB-06 (conexão por request/app context; injeção de dependência; remover acumuladores globais).

### AP-09 — Error handling ausente ou não centralizado — **HIGH**
**Sinais de detecção:**
- O mesmo `try/except`/`try/catch` copiado em todos os handlers, devolvendo `str(e)` cru ao cliente.
- `except:` sem tipo (bare except) engolindo qualquer exceção; callbacks que ignoram `err` silenciosamente.
- Ausência de error handler global (`@app.errorhandler` / middleware `(err, req, res, next)`).
**Impacto:** vazamento de detalhes internos, erros silenciosos, comportamento inconsistente entre endpoints.
**Correção:** → PB-07 (handler central + exceções de domínio).

### AP-10 — Configuração insegura de produção — **HIGH**
**Sinais de detecção:**
- `debug=True` / `DEBUG = True` hardcoded no entry point (habilita até execução de código via debugger do Werkzeug).
- CORS liberado para qualquer origem sem configuração (`CORS(app)` sem origins, `app.use(cors())`).
- Host/porta/ambiente fixos no código, sem leitura de variável de ambiente.
**Impacto:** consoles de debug expostos, requisições cross-origin irrestritas, impossibilidade de configurar por ambiente.
**Correção:** → PB-02 (config por ambiente com defaults seguros).

---

## MEDIUM

### AP-11 — Queries N+1 — **MEDIUM**
**Sinais de detecção:**
- Query dentro de loop sobre resultado de outra query (`for row in rows: cursor.execute(...)`, `Model.query.get(...)` dentro de `for`).
- Em Node: `db.all` externo com `db.get` aninhado por item, controlado por contadores manuais de "pending".
- Listagens que fazem 1 consulta extra por item para buscar nome/contagem relacionada.
**Impacto:** latência cresce linearmente (ou pior) com o volume de dados; banco sobrecarregado.
**Correção:** → PB-08 (JOIN/eager loading/agregação no SQL).

### AP-12 — Duplicação de código (violação DRY) — **MEDIUM**
**Sinais de detecção:**
- O mesmo mapeamento linha→dict ou objeto→JSON repetido em N funções (compare campo a campo).
- A mesma sequência de validações copiada entre create/update; a mesma regra (ex.: cálculo de atraso) reimplementada em vários arquivos.
- Utilitários/constantes que existem no projeto mas não são usados nos pontos que duplicam sua lógica.
**Impacto:** correções precisam ser replicadas manualmente; divergência silenciosa entre cópias.
**Correção:** → PB-10 (serialização/validação canônicas no model ou módulo único).

### AP-13 — APIs deprecated/obsoletas — **MEDIUM**
Compare o código com a tabela abaixo; reporte cada uso com o equivalente moderno. Suba para HIGH/CRITICAL quando a API obsoleta for de segurança (ex.: MD5 para senha já é coberto por AP-03).

| Ecossistema | Deprecated/obsoleto | Equivalente moderno |
|---|---|---|
| Python ≥3.12 | `datetime.utcnow()` / `datetime.utcfromtimestamp()` | `datetime.now(timezone.utc)` |
| SQLAlchemy ≥2.0 | `Model.query.get(id)` (Legacy Query API) | `db.session.get(Model, id)` |
| Flask ≥2.3 | `@app.before_first_request` | inicialização explícita no factory/entry point |
| Python | `os.system()` para comandos | `subprocess.run()` |
| Node.js | `new Buffer(...)` | `Buffer.from(...)` / `Buffer.alloc(...)` |
| Node.js | `url.parse()` | WHATWG `new URL()` |
| Node.js | callbacks aninhados estilo errback como padrão da base | `async/await` (promisify ou driver com Promises) |
| JS | `var` | `const`/`let` |
| Express <4 legado | `bodyParser.json()` dependência separada | `express.json()` embutido |
| Crypto | `md5`/`sha1` para qualquer fim de segurança | bcrypt/scrypt/argon2 (senhas), SHA-256+ (integridade) |
**Impacto:** quebra em upgrades futuros, warnings em runtime, práticas reconhecidamente inseguras.
**Correção:** → PB-09.

### AP-14 — Validação de entrada ausente ou incompleta — **MEDIUM**
**Sinais de detecção:**
- Campos usados direto do request sem checar presença/tipo/intervalo (`data['x']`, conversões `int(...)`/`float(...)` sem tratamento → 500).
- Ausência de validação de formato (email sem regex/validador; datas aceitas em formato livre).
- Campos crípticos sem contrato claro (`usr`, `eml`, `c_id`) aceitos sem normalização; unicidade não verificada (email duplicado).
**Impacto:** 500 em vez de 400, dados inconsistentes no banco, vetores de abuso.
**Correção:** → PB-10 (camada de validação única por recurso).

### AP-15 — Integridade referencial ausente / deleções órfãs — **MEDIUM**
**Sinais de detecção:**
- DELETE de entidade pai sem tratar filhos (matrículas/pagamentos/tarefas órfãos) — às vezes admitido na própria mensagem de resposta.
- Schema sem `FOREIGN KEY`/`ON DELETE`; relacionamentos de ORM sem cascade definido onde o domínio exige.
- Loops manuais deletando filhos um a um no handler.
**Impacto:** dados órfãos corrompem relatórios e quebram joins; deleções parciais sem transação.
**Correção:** → PB-08/PB-04 (constraints no schema, cascade no ORM, operação transacional no model).

---

## LOW

### AP-16 — `print`/`console.log` como logging — **LOW**
**Sinais de detecção:** `print(...)`/`console.log(...)` espalhados para eventos de aplicação (criou, deletou, erro) em vez de um logger com níveis; mensagens de erro logadas sem stack/contexto.
**Impacto:** sem níveis, sem timestamp, sem destino configurável; ruído em produção.
**Correção:** → PB-12 (logger da stdlib/stack com níveis).

### AP-17 — Magic numbers & strings — **LOW**
**Sinais de detecção:** limiares e taxas soltos em expressões (`> 10000`, `* 0.1`), listas de status/categorias/roles repetidas inline em vez de constantes/enums, portas e versões duplicadas em strings.
**Impacto:** significado opaco; mudanças exigem caça a todas as cópias.
**Correção:** → PB-13 (constantes nomeadas em módulo único).

### AP-18 — Nomenclatura ruim ou inconsistente — **LOW**
**Sinais de detecção:** variáveis de 1-2 letras fora de índices (`u`, `e`, `p`, `cid`, `cc`), abreviações crípticas em payloads, mistura de idiomas no mesmo código (`listar_produtos` + `getUsers`), nomes que mentem (`utils` com regra de negócio).
**Impacto:** custo de leitura alto; contratos de API confusos.
**Correção:** → PB-04/PB-10 (renomear internamente — sem quebrar o contrato externo de payloads existentes; melhorias de contrato apenas documentadas).

### AP-19 — Dead code e imports não usados — **LOW**
**Sinais de detecção:** imports nunca referenciados no arquivo (`import os, sys, json` sem uso), funções/serviços inteiros nunca chamados, variáveis exportadas e nunca lidas, condicionais redundantes (`if x: return True else: return False`).
**Impacto:** ruído, falsa sensação de funcionalidade, dependências fantasma.
**Correção:** → PB-15 (remoção segura após confirmar ausência de referências).
