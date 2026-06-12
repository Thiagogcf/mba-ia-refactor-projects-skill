# Audit Report — Projeto 2: ecommerce-api-legacy

> Output das Fases 1 e 2 da skill `refactor-arch`, gerado por execução headless
> imparcial: `claude -p "/refactor-arch" --model sonnet` (claude-sonnet-4-6,
> contexto novo, somente leitura). Sessão: `c1819c26-a3bd-4019-b503-e88013ab7693`.

```
================================
PHASE 1: PROJECT ANALYSIS
================================
Language:      Node.js (JavaScript) — evidência: package.json, src/*.js
Framework:     Express ^4.18.2 — evidência: dependência em package.json, require em app.js e AppManager.js
Dependencies:  sqlite3 ^5.1.6 (acesso direto, sem ORM)
Domain:        LMS com checkout de cursos — recursos: cursos, usuários, matrículas, pagamentos, log de auditoria
Architecture:  Monolítica multi-file, sem camadas — entry point em src/app.js instancia AppManager, que é uma
               God Class contendo: inicialização do schema, seeds, registro de todas as rotas, lógica de negócio
               e acesso a dados. src/utils.js mistura configuração, cache global e criptografia caseira.
Source files:  3 files analyzed (src/app.js, src/AppManager.js, src/utils.js)
DB tables:     users, courses, enrollments, payments, audit_logs
               (SQLite in-memory; schema + seeds criados no boot via AppManager.initDb())
================================
```

---

```
================================
ARCHITECTURE AUDIT REPORT
================================
Project: ecommerce-api-legacy
Stack:   Node.js + Express 4.18.2
Files:   3 analyzed | ~181 lines of code

## Summary
CRITICAL: 5 | HIGH: 4 | MEDIUM: 4 | LOW: 4

## Findings

### [CRITICAL] Credenciais e segredos hardcoded (AP-02)
File: src/utils.js:1-7
Description: O objeto `config` contém em texto literal: senha de banco (`dbPass: "senha_super_secreta_prod_123"`),
  chave de produção do gateway de pagamento (`paymentGatewayKey: "pk_live_1234567890abcdef"`), usuário SMTP e
  usuário de banco. Qualquer pessoa com acesso ao repositório obtém credenciais de produção sem restrição.
Impact: Rotação de credenciais exige rebuild e deploy; chave `pk_live_*` pode ser usada imediatamente para
  transações fraudulentas; violação direta da LGPD e das diretrizes PCI-DSS.
Recommendation: Mover toda a configuração para variáveis de ambiente lidas via `process.env`; adicionar
  `.env.example` com os nomes das variáveis (sem valores reais); nunca commitar `.env`. → PB-02

### [CRITICAL] Armazenamento inseguro de senhas (AP-03)
File: src/utils.js:17-23, src/AppManager.js:18, src/AppManager.js:68
Description: (1) `utils.js:17-23` define `badCrypto`: um loop de 10.000 iterações concatenando 2 chars de
  base64 — não é um algoritmo de hash de senha; é reversível e trivialmente quebrável. (2) `AppManager.js:68`
  aplica `badCrypto(p || "123456")`: senha padrão "123456" embutida caso o campo seja omitido. (3)
  `AppManager.js:18` seed de usuário com senha `'123'` em texto plano diretamente no banco.
Impact: Vazamento do banco compromete todas as contas; qualquer leitor do código sabe a senha padrão de novos
  usuários criados sem fornecer credencial.
Recommendation: Substituir `badCrypto` por `bcrypt` (ou `crypto.scrypt` da stdlib) com salt gerado
  aleatoriamente; remover senha default e exigir campo obrigatório; rehashear o seed. → PB-03

### [CRITICAL] Exposição de dados sensíveis em logs (AP-04)
File: src/AppManager.js:44-45
Description: O handler de checkout registra em console: número completo do cartão (`cc`) e a chave de
  produção do gateway (`config.paymentGatewayKey`) — `console.log(\`Processando cartão ${cc} na chave
  ${config.paymentGatewayKey}\`)`. Dados PCI-DSS de categoria 1 aparecem em texto plano nos logs.
Impact: Qualquer acesso aos logs de aplicação (console, stdout, agregador de logs) expõe PANs e chaves de API.
  Infração direta das regras PCI-DSS, que proíbem armazenar/logar o número completo do cartão.
Recommendation: Remover o log ou mascarar o PAN (exibir apenas os 4 últimos dígitos) e nunca logar a chave do
  gateway; configurar um logger com redação de campos sensíveis. → PB-12

### [CRITICAL] God Class — AppManager concentra todas as responsabilidades (AP-05)
File: src/AppManager.js:4-141
Description: A classe `AppManager` acumula 5 responsabilidades distintas: (1) gestão da conexão SQLite
  (`constructor`, linha 7); (2) criação de schema e seeds (`initDb`, linhas 10-23); (3) registro de todas as
  rotas HTTP (`setupRoutes`, linha 25); (4) lógica de negócio — aprovação de pagamento por prefixo de cartão
  (linha 46), fluxo de matrícula, criação condicional de usuário (linhas 43-75); (5) todas as queries de
  acesso a dados (linhas 37-133).
Impact: Impossível testar qualquer responsabilidade em isolamento; qualquer alteração irradia risco por toda a
  classe; alta probabilidade de conflitos de merge em time.
Recommendation: Decompor em camadas MVC: `config/`, `models/` (User, Course, Enrollment, Payment), `controllers/`
  (CheckoutController, ReportController, UserController), `routes/` finas. → PB-04

### [CRITICAL] Endpoints administrativos e destrutivos sem autenticação (AP-06)
File: src/AppManager.js:80-129, src/AppManager.js:131-137
Description: Dois endpoints críticos não têm nenhuma verificação de identidade: (1)
  `GET /api/admin/financial-report` (linhas 80-129) expõe receita por curso e dados de alunos para qualquer
  cliente; (2) `DELETE /api/users/:id` (linhas 131-137) apaga qualquer usuário sem autenticação. Nenhum
  middleware de autenticação existe no projeto.
Impact: Qualquer pessoa na rede pode exfiltrar o relatório financeiro completo ou deletar usuários
  arbitrariamente, incluindo o próprio banco de dados em memória.
Recommendation: Adicionar middleware de autenticação (token JWT ou API key via header) para todas as rotas
  administrativas e destrutivas. Proteger rotas com guard antes de qualquer lógica de negócio. → PB-14

### [HIGH] Lógica de negócio embutida nos handlers de rota (AP-07)
File: src/AppManager.js:43-75, src/AppManager.js:88-127
Description: Os handlers contêm regras de domínio inline: (1) aprovação de pagamento decidida por prefixo do
  número do cartão (`cc.startsWith("4")`, linha 46) — regra de negócio crítica sem abstração; (2) fluxo de
  criação de usuário durante checkout (linhas 66-75) misturado com lógica de pagamento; (3) cálculo de
  receita e montagem do relatório financeiro (linhas 89-127) feito inteiramente no handler.
Impact: Regras de negócio não podem ser testadas sem iniciar um servidor HTTP; duplicação inevitável ao
  adicionar novos endpoints com fluxos similares.
Recommendation: Mover regras de domínio para a camada de models/services; controllers devem apenas
  orquestrar chamadas e retornar respostas. → PB-05

### [HIGH] Estado global mutável (AP-08)
File: src/utils.js:9-10, src/AppManager.js:2
Description: `utils.js:9-10` declara `let globalCache = {}` e `let totalRevenue = 0` como variáveis de
  módulo mutáveis e as exporta. `AppManager.js:2` importa `totalRevenue` — que nunca é modificada nem lida
  funcionalmente, indicando vestigio de estado compartilhado. O `globalCache` é escrito a cada checkout
  (`logAndCache`), acumulando em memória sem limite e sem TTL.
Impact: Race conditions em cenários concorrentes; cache que cresce indefinidamente causa memory leak; estado
  perdido em qualquer restart; impossibilidade de escalar horizontalmente.
Recommendation: Eliminar globais mutáveis; usar cache de request-scope ou solução de cache externa (Redis) se
  necessário; remover `totalRevenue` não usado. → PB-06

### [HIGH] Error handling ausente ou não centralizado (AP-09)
File: src/AppManager.js:41, 51, 55, 69, 104, 106, 133
Description: Erros são tratados de forma ad-hoc e frequentemente ignorados: (1) linhas 41, 51, 55, 69
  devolvem mensagens de erro cruas como strings (sem JSON estruturado); (2) callbacks internos em linhas 104 e
  106 (`SELECT users`, `SELECT payments` no relatório) ignoram o parâmetro `err` completamente — falhas de DB
  são silenciosas; (3) linha 57 (INSERT audit_log) e linha 133 (DELETE users) ignoram `err` e sempre enviam
  resposta de sucesso. Não existe middleware de erro global (`(err, req, res, next)`).
Impact: Erros de banco passam silenciosamente para o cliente como sucesso; exceções não capturadas podem
  derrubar o processo; comportamento inconsistente entre endpoints.
Recommendation: Adicionar handler de erro global do Express; usar wrappers async com next(err); estruturar
  respostas de erro em JSON com código e mensagem. → PB-07

### [HIGH] Configuração de porta sem leitura de variável de ambiente (AP-10)
File: src/utils.js:6, src/app.js:12
Description: A porta do servidor está hardcoded como `3000` no objeto `config` em `utils.js:6`, sem leitura
  de `process.env.PORT`. Nenhuma variável do objeto `config` lê `process.env`. Junto com AP-02, isso significa
  que toda a configuração da aplicação é estática e embutida no código.
Impact: Impossível configurar por ambiente (dev/staging/prod) sem alterar o código; conflito de porta em
  ambientes de CI ou containers.
Recommendation: Substituir por `process.env.PORT || 3000`; centralizar toda leitura de env em módulo de config
  único com validação de presença para variáveis obrigatórias. → PB-02

### [MEDIUM] Queries N+1 no relatório financeiro (AP-11)
File: src/AppManager.js:82-127
Description: O handler `GET /api/admin/financial-report` executa queries em cascata: 1 query para todos os
  cursos (linha 83) → para cada curso, 1 query de matrículas (linha 92) → para cada matrícula, 1 query de
  usuário (linha 104) e 1 query de pagamento (linha 106). Com C cursos e E matrículas por curso, o total
  é `1 + C + C*E*2` queries. O código controla a convergência via contadores manuais `coursesPending` e
  `enrPending`, pattern frágil e difícil de depurar.
Impact: Latência cresce com o volume de dados; banco sobrecarregado; contadores manuais de callbacks são
  propensos a bugs de sincronização.
Recommendation: Substituir por um JOIN que traga todos os dados em uma única query; eliminar os contadores
  manuais via async/await. → PB-08

### [MEDIUM] Callbacks aninhados — API errback deprecated (AP-13)
File: src/AppManager.js:37-127
Description: Todo o código de acesso a dados usa o estilo errback com callbacks aninhados (pyramid of doom):
  5 níveis de aninhamento no checkout (linhas 37-75), 4 níveis no relatório financeiro (linhas 82-127). O
  catálogo AP-13 lista "callbacks aninhados estilo errback como padrão da base" como deprecated em Node.js
  moderno em favor de `async/await`.
Impact: Legibilidade extremamente comprometida; difícil de depurar; propenso a callback hell e a omissão de
  verificações de erro.
Recommendation: Migrar para `async/await` usando `sqlite3` com `promisify` (util.promisify) ou trocar pelo
  driver `better-sqlite3` (síncrono) ou `sqlite` (wrapper Promise). → PB-09

### [MEDIUM] Validação de entrada ausente ou incompleta (AP-14)
File: src/AppManager.js:29-35
Description: O checkout valida apenas presença de 4 campos (`!u || !e || !cid || !cc`, linha 35), mas omite:
  validação de formato de email; validação de que `cid` é um número inteiro positivo; validação de formato de
  cartão; campo `pwd` (`p`) é opcional com fallback para senha default "123456" (duplo problema com AP-03);
  sem verificação de duplicidade de email ao criar usuário. Nomes de campos crípticos no contrato de request
  (`usr`, `eml`, `c_id`, `card`) dificultam uso da API.
Impact: Banco pode receber dados malformados; 500 em vez de 400 para tipos inválidos; email duplicado cria
  múltiplas contas para o mesmo endereço.
Recommendation: Adicionar validação explícita de tipos, formato e unicidade em camada de validação separada
  antes do acesso ao banco. → PB-10

### [MEDIUM] Integridade referencial ausente — deleções órfãs (AP-15)
File: src/AppManager.js:131-137, src/AppManager.js:11-16
Description: O schema criado em `initDb` (linhas 11-16) não define `FOREIGN KEY` entre tabelas. O handler
  `DELETE /api/users/:id` (linhas 131-137) apaga o usuário sem remover suas matrículas e pagamentos —
  o próprio código anuncia isso na mensagem de resposta: *"as matrículas e pagamentos ficaram sujos no banco"*.
  Dados órfãos corrompem o relatório financeiro (nomes "Unknown" já previstos na linha 112).
Impact: Relatórios financeiros com dados inconsistentes; integridade do banco comprometida permanentemente.
Recommendation: Adicionar `FOREIGN KEY` com `ON DELETE CASCADE` no schema, ou tratar deleção em transação
  removendo filhos antes do pai. → PB-04/PB-08

### [LOW] console.log como mecanismo de logging (AP-16)
File: src/utils.js:13, src/AppManager.js:44, src/app.js:13
Description: Logging via `console.log` simples: `utils.js:13` (cache), `AppManager.js:44` (dados PCI —
  agravado em AP-04), `app.js:13` (startup). Sem níveis, sem timestamp estruturado, sem destino configurável.
Impact: Impossível filtrar por severidade; inútil em produção com agregadores de log (Datadog, CloudWatch).
Recommendation: Substituir por logger com níveis (ex.: `pino` ou `winston`) com saída JSON. → PB-12

### [LOW] Magic numbers e strings de status (AP-17)
File: src/utils.js:19, src/AppManager.js:46-48, src/AppManager.js:108
Description: `utils.js:19`: `10000` como número de iterações em `badCrypto` sem constante nomeada.
  `AppManager.js:46-48`: strings `"PAID"` e `"DENIED"` repetidas inline sem enum/constante
  (`status === "PAID"` na linha 108 e na lógica de checkout). Significado opaco no ponto de uso.
Impact: Mudança de valor de status exige busca manual em múltiplos pontos; inconsistência silenciosa
  se uma cópia for alterada e outra não.
Recommendation: Definir constantes `PAYMENT_STATUS = { PAID: 'PAID', DENIED: 'DENIED' }` em módulo de
  constantes. → PB-13

### [LOW] Nomenclatura ruim e inconsistente (AP-18)
File: src/AppManager.js:29-34, src/AppManager.js:87, src/utils.js:1
Description: Variáveis de 1-2 letras no handler de checkout: `u` (name), `e` (email), `p` (password), `cid`
  (course_id), `cc` (card) — linhas 29-34. Loop com `c` para course (linha 89). O módulo `utils.js` contém
  lógica de negócio (`badCrypto`) e não apenas utilitários. O nome `AppManager` não revela sua verdadeira
  natureza (God Class).
Impact: Custo de leitura alto; contratos de API implicitamente obscuros.
Recommendation: Renomear variáveis internas para nomes descritivos; separar responsabilidades de `utils.js`
  em módulos específicos (`config.js`, `crypto.js`). → PB-18 (renomear internamente sem quebrar contrato)

### [LOW] Dead code — variável não utilizada (AP-19)
File: src/utils.js:10, src/AppManager.js:2
Description: `totalRevenue = 0` é declarada e exportada em `utils.js:10`, importada em `AppManager.js:2`
  via destructuring, mas nunca lida nem modificada em nenhum ponto do código. Além disso, `dbUser` e
  `dbPass` em `config` são declarados mas o SQLite in-memory não usa autenticação — são credenciais
  hardcoded sem uso funcional (agravado em AP-02).
Impact: Ruído no código; falsa impressão de que revenue é rastreada; credenciais expostas sem serventia.
Recommendation: Remover `totalRevenue` e credenciais de banco desnecessárias; verificar outros exports não
  utilizados. → PB-15

================================
Total: 17 findings
================================
```

Phase 2 complete. Proceed with refactoring (Phase 3)? [y/n]
