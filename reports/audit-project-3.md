# Audit Report — Projeto 3: task-manager-api

> Output das Fases 1 e 2 da skill `refactor-arch`, gerado por execução headless
> imparcial: `claude -p "/refactor-arch" --model sonnet` (claude-sonnet-4-6,
> contexto novo, somente leitura). Sessão: `f948522b-f41b-4c26-b51d-823b93764245`.

```
================================
PHASE 1: PROJECT ANALYSIS
================================
Language:      Python 3.x (inferido de Flask 3.0.0 + flask-sqlalchemy 3.1.1)
Framework:     Flask 3.0.0
Dependencies:  flask-sqlalchemy==3.1.1, flask-cors==4.0.0,
               marshmallow==3.20.1, requests==2.31.0,
               python-dotenv==1.0.0
Domain:        Task Manager API — gerenciamento de tarefas com
               usuários, categorias e relatórios de produtividade
Architecture:  Camadas parciais — existem models/, routes/,
               services/ e utils/, mas routes concentram toda a
               lógica de negócio e validação sem controllers;
               report_routes.py mistura domínio de reports e
               CRUD de categories no mesmo Blueprint
Source files:  11 files analyzed
DB tables:     users, tasks, categories
================================
```

---

Prosseguindo para a Fase 2 — auditando todos os arquivos contra o catálogo.

---

```
================================
ARCHITECTURE AUDIT REPORT
================================
Project: task-manager-api
Stack:   Python + Flask 3.0.0
Files:   11 analyzed | ~1160 lines of code

## Summary
CRITICAL: 4 | HIGH: 3 | MEDIUM: 5 | LOW: 3

## Findings

### [CRITICAL] Credenciais e segredos hardcoded (AP-02)
File: app.py:11-13, services/notification_service.py:8-10
Description: app.py define `SECRET_KEY = 'super-secret-key-123'`
  e `SQLALCHEMY_DATABASE_URI = 'sqlite:///tasks.db'` como literais.
  notification_service.py hardcoda `email_user = 'taskmanager@gmail.com'`
  e `email_password = 'senha123'` no __init__ da classe.
Impact: Qualquer pessoa com acesso ao repositório obtém os segredos;
  rotação exige deploy; credenciais de produção vazam com o código.
Recommendation: Extrair toda configuração para módulo config.py lendo
  variáveis de ambiente via python-dotenv (já está no requirements.txt);
  criar .env.example documentando as variáveis sem os valores reais.
  Transformação: PB-02.

### [CRITICAL] Armazenamento inseguro de senhas — MD5 sem salt (AP-03)
File: models/user.py:29, models/user.py:32
Description: set_password() e check_password() usam
  `hashlib.md5(pwd.encode()).hexdigest()` sem salt. MD5 não é
  algoritmo de derivação de senha; é reversível via rainbow tables.
  O seed (seed.py:19,23,28) cria usuários com senhas fracas
  ('1234', 'abcd', 'pass') via esse mesmo mecanismo.
Impact: Vazamento do banco compromete todas as senhas; senhas
  reutilizadas pelos usuários ficam expostas em segundos via lookup.
Recommendation: Substituir por werkzeug.security (já disponível via
  Flask) com generate_password_hash/check_password_hash (algoritmo
  scrypt/pbkdf2 com salt automático). Transformação: PB-03.

### [CRITICAL] Exposição de dados sensíveis em respostas de API (AP-04)
File: models/user.py:17-25, routes/user_routes.py:33,86,128-129,
      routes/user_routes.py:207-210
Description: User.to_dict() inclui o campo `password` (hash MD5)
  na serialização. Todos os endpoints que retornam User chamam
  to_dict(): GET /users/<id>, POST /users, PUT /users/<id>.
  Adicionalmente, POST /login (user_routes.py:207-210) retorna
  `'token': 'fake-jwt-token-' + str(user.id)` — token previsível
  e não validado em nenhum endpoint, dando falsa sensação de
  autenticação.
Impact: Hash de senha é devolvido em toda operação de usuário;
  token fictício é aceitável como prova de autenticação apenas
  na aparência — nenhum endpoint verifica o header Authorization.
Recommendation: Remover `password` de to_dict() (ou criar
  to_public_dict()). Remover o token falso do login ou substituir
  por JWT real. Transformação: PB-03/PB-12.

### [CRITICAL] Todos os endpoints sem autenticação real (AP-06)
File: routes/user_routes.py:134-151, routes/task_routes.py:225-238,
      routes/report_routes.py:12-101, routes/report_routes.py:103-155
Description: Apesar de existir rota POST /login, nenhum decorator
  ou middleware verifica autenticação em qualquer endpoint.
  DELETE /users/<id>, DELETE /tasks/<id>, GET /reports/summary
  e GET /reports/user/<id> (com dados de produtividade de todos
  os usuários) são acessíveis anonimamente.
Impact: Qualquer cliente da rede pode deletar dados ou exfiltrar
  relatórios sem credenciais.
Recommendation: Implementar decorator @require_auth lendo o header
  Authorization, ou integrar flask-jwt-extended/flask-login.
  No mínimo, proteger endpoints destrutivos e de relatório.
  Transformação: PB-14.

### [HIGH] Lógica de negócio concentrada nas rotas (AP-07)
File: routes/task_routes.py:13-63, routes/task_routes.py:85-154,
      routes/task_routes.py:156-223, routes/task_routes.py:273-299,
      routes/user_routes.py:42-90, routes/user_routes.py:92-132,
      routes/report_routes.py:12-101, routes/report_routes.py:103-155
Description: Cada handler HTTP contém validação campo a campo,
  cálculo de overdue, montagem manual de dicts de resposta,
  verificação de existência de FKs e agregações de relatório —
  tudo inline. Exemplo: create_task() (task_routes.py:85-154)
  valida título, status, prioridade, user_id e category_id antes
  de persistir, duplicando regras já existentes em
  Task.validate_status() e utils/helpers.py.
  report_routes.py mistura CRUD de categories com lógica de
  relatórios num único Blueprint.
Impact: Regras de negócio impossíveis de testar sem HTTP;
  duplicação entre create e update; lógica espalhada por 8 handlers.
Recommendation: Extrair validação e regras para controllers/services
  por domínio (TaskService, UserService); routes apenas chamam o
  controller e retornam jsonify(). Mover CRUD de categories para
  um Blueprint próprio. Transformação: PB-05.

### [HIGH] Error handling não centralizado — bare except (AP-09)
File: routes/task_routes.py:62, routes/task_routes.py:138,
      routes/task_routes.py:236, routes/user_routes.py:131,
      routes/user_routes.py:149, routes/report_routes.py:186,
      routes/report_routes.py:208, routes/report_routes.py:222
Description: Oito handlers usam `except:` sem tipo (bare except),
  engolindo qualquer exceção incluindo KeyboardInterrupt e
  SystemExit. Nenhum handler global (@app.errorhandler) existe;
  erros inesperados em rotas sem try/except retornam stack trace
  HTML padrão do Werkzeug (com debug=True ativo, ver AP-10).
Impact: Erros silenciosos; stack traces expostos ao cliente;
  comportamento inconsistente entre endpoints.
Recommendation: Substituir bare except por `except Exception as e:`;
  criar @app.errorhandler(Exception) central com logging e
  resposta JSON padronizada. Transformação: PB-07.

### [HIGH] Configuração insegura de produção (AP-10)
File: app.py:11-15, app.py:34
Description: `app.run(debug=True, host='0.0.0.0', port=5000)`
  hardcoded — debug=True habilita o console interativo do Werkzeug,
  permitindo execução arbitrária de código em qualquer exceção.
  `CORS(app)` sem parâmetro origins aceita requisições de qualquer
  domínio. HOST, PORT e DATABASE_URI são literais sem leitura de
  variáveis de ambiente.
Impact: Console de debug exposto em produção; CORS irrestrito;
  impossibilidade de configurar o serviço por ambiente.
Recommendation: Ler debug/host/port/CORS origins de variáveis de
  ambiente; default debug=False. Transformação: PB-02.

### [MEDIUM] Queries N+1 (AP-11)
File: routes/task_routes.py:42-57, routes/report_routes.py:55-68
Description: Em get_tasks() (task_routes.py:42-57), para cada task
  na lista são executadas até 2 queries extras: `User.query.get(
  t.user_id)` e `Category.query.get(t.category_id)` — 2N queries
  adicionais para N tasks.
  Em summary_report() (report_routes.py:55-68), para cada usuário
  é feita uma query `Task.query.filter_by(user_id=u.id).all()` —
  N queries adicionais para N usuários.
Impact: Para 100 tasks com user e category, get_tasks() dispara
  201 queries; latência cresce linearmente com volume.
Recommendation: Usar joinedload/subqueryload no SQLAlchemy para
  eager loading de relações; usar GROUP BY + COUNT para agregações.
  Transformação: PB-08.

### [MEDIUM] Duplicação de código — DRY violado (AP-12)
File: models/task.py:50-60, routes/task_routes.py:30-39,71-80,
      282-287, routes/user_routes.py:170-181,
      routes/report_routes.py:33-37, routes/report_routes.py:131-135,
      routes/task_routes.py:18-28, routes/user_routes.py:160-168,
      models/task.py:38-43, routes/task_routes.py:110-111,177-178
Description: Lógica de cálculo de overdue reimplementada em 6
  locais (task_routes.py:30-39, :71-80, :282-287;
  user_routes.py:170-181; report_routes.py:33-37, :131-135)
  sendo que Task.is_overdue() já existe mas não é chamado.
  Mapeamento task→dict duplicado entre to_dict() e get_tasks().
  Validação de status reescrita inline em create_task() e
  update_task() ignorando Task.validate_status().
  validate_email() em utils/helpers.py existe mas as routes
  reimplementam o mesmo regex inline.
Impact: Correções devem ser replicadas em todos os pontos;
  divergências silenciosas já presentes (to_dict vs montagem manual).
Recommendation: Centralizar serialização em to_dict() dos models;
  usar Task.is_overdue() nas rotas; usar Task.validate_status()
  e helpers.validate_email() nos controllers. Transformação: PB-10.

### [MEDIUM] APIs deprecated/obsoletas (AP-13)
File: models/user.py:14, models/task.py:15-16, models/category.py:10,
      routes/task_routes.py:31,73,215,285,
      routes/user_routes.py:171, routes/report_routes.py:35,48,51,
      services/notification_service.py:36, utils/helpers.py:39,
      routes/task_routes.py:67,117,124,158,188,195,
      routes/user_routes.py:29,155,
      routes/report_routes.py:105,192,197,214
Description: `datetime.utcnow()` usado em 13 locais — deprecado em
  Python ≥3.12 (deve usar `datetime.now(timezone.utc)`).
  `Model.query.get(id)` usado em 11 locais — Legacy Query API do
  SQLAlchemy deprecado desde 2.0 (deve usar
  `db.session.get(Model, id)`).
Impact: Warnings em runtime com Python 3.12+; quebra em upgrades
  futuros do Python e SQLAlchemy.
Recommendation: Substituir por datetime.now(timezone.utc) e
  db.session.get(). Transformação: PB-09.

### [MEDIUM] Validação de entrada incompleta em query params (AP-14)
File: routes/task_routes.py:260-264
Description: Em search_tasks(), os query params `priority` e
  `user_id` são convertidos com `int(priority)` e `int(user_id)`
  sem try/except — qualquer valor não-numérico (ex: `?priority=abc`)
  gera ValueError e retorna 500 em vez de 400.
Impact: Clientes recebem erro interno ao invés de resposta de
  validação; superficie de DoS simples por input malformado.
Recommendation: Envolver conversões de query params em try/except
  e retornar 400 com mensagem descritiva. Transformação: PB-10.

### [MEDIUM] Integridade referencial ausente — deleções órfãs (AP-15)
File: routes/user_routes.py:140-143, routes/report_routes.py:211-222,
      models/task.py:13-14
Description: DELETE /users/<id> deleta tasks manualmente em loop
  (user_routes.py:140-143) mas fora de transação atômica — falha
  parcial não é tratada. DELETE /categories/<id> não trata as
  tasks com category_id referenciando a categoria deletada; sem
  `cascade` definido no relacionamento Task.category, SQLite
  (sem PRAGMA foreign_keys) deixa tasks com FK inválida.
Impact: Dados órfãos corrompem relatórios de categorias;
  deleção de usuário pode falhar parcialmente sem rollback correto.
Recommendation: Definir cascade="all, delete-orphan" no
  relacionamento ORM ou usar ON DELETE SET NULL/CASCADE no schema;
  garantir delete_user em transação única. Transformação: PB-08/PB-04.

### [LOW] print() como logging — sem níveis ou destino configurável (AP-16)
File: routes/task_routes.py:149,153,219, routes/user_routes.py:83,
      89,147, services/notification_service.py:21,24
Description: Sete chamadas print() espalhadas para eventos de
  aplicação (criação/deleção de tasks e usuários, erros de email)
  sem níveis, timestamp configurável ou destino ajustável.
Impact: Sem níveis (INFO/ERROR), impossível filtrar em produção;
  sem formatter, logs perdem contexto em ambiente containerizado.
Recommendation: Substituir por `logging.getLogger(__name__)` com
  nível configurável via variável de ambiente. Transformação: PB-12.

### [LOW] Magic numbers & strings sem constantes (AP-17)
File: routes/task_routes.py:97,100,113-114,167-169,177-178,
      routes/user_routes.py:64,71, utils/helpers.py:110-116
Description: Listas `['pending','in_progress','done','cancelled']`
  e `['user','admin','manager']` repetidas inline nas rotas,
  apesar de VALID_STATUSES e VALID_ROLES estarem definidos em
  utils/helpers.py:110-115 — mas nunca importados nas rotas.
  Limites MIN_TITLE_LENGTH=3, MAX_TITLE_LENGTH=200,
  MIN_PASSWORD_LENGTH=4 definidos em helpers.py mas não usados.
Impact: Mudança de regra exige caça manual a todas as cópias;
  constantes em helpers.py são dead code.
Recommendation: Importar e usar as constantes já definidas em
  utils/helpers.py (ou movê-las para config.py). Transformação: PB-13.

### [LOW] Dead code e imports não usados (AP-19)
File: app.py:7, routes/task_routes.py:7, routes/user_routes.py:6,
      routes/report_routes.py:8, utils/helpers.py:2-6,57-108,
      models/task.py:2, models/task.py:38-48,
      services/notification_service.py (inteiro)
Description: app.py importa os/sys/json sem uso. task_routes.py
  importa json/os/sys/time sem uso. user_routes.py importa hashlib
  sem uso direto. report_routes.py importa json sem uso.
  utils/helpers.py importa math/hashlib/json/sys sem uso e define
  process_task_data() + todas as constantes (linhas 57-116) nunca
  referenciadas em nenhum arquivo do projeto.
  models/task.py importa json sem uso; validate_status() e
  validate_priority() definidos mas nunca chamados (rotas
  reimplementam inline).
  services/notification_service.py inteiro — nunca importado ou
  instanciado em qualquer rota; contém estado em memória
  (self.notifications = []) que se perderia em restart.
Impact: Ruído que confunde sobre o que está ativo; dead code
  cria falsa sensação de funcionalidade (notification service).
Recommendation: Remover imports não usados; remover process_task_data
  ou integrá-lo às rotas; decidir sobre o notification service
  (remover ou integrar com persistência real). Transformação: PB-15.

================================
Total: 15 findings
================================
```

Phase 2 complete. Proceed with refactoring (Phase 3)? [y/n]
