# Audit Report — Projeto 1: code-smells-project

> Output das Fases 1 e 2 da skill `refactor-arch`, gerado por execução headless
> imparcial: `claude -p "/refactor-arch" --model sonnet` (claude-sonnet-4-6,
> contexto novo, somente leitura). Sessão: `226d3daf-d211-42f5-9a9e-f52937aec5cc`.

```
================================
PHASE 1: PROJECT ANALYSIS
================================
Language:      Python 3.x (versão não pinada no manifest)
Framework:     Flask 3.1.1
Dependencies:  flask-cors 5.0.1; sqlite3 (stdlib, acesso direto sem ORM)
Domain:        API de E-commerce — gerenciamento de produtos (com busca e
               estoque), usuários, autenticação e pedidos com itens
Architecture:  Camadas parciais — 4 arquivos separados por papel técnico
               (app.py · controllers.py · models.py · database.py), mas com
               violações relevantes: models.py concentra acesso a dados +
               lógica de negócio + formatação para todos os domínios;
               database.py mistura conexão + criação de schema + seed;
               endpoints administrativos com SQL inline em app.py.
               Entry point: app.py | Rotas: app.py:11-30 (add_url_rule) +
               app.py:32-78 (decorators) | Dados: models.py | Negócio:
               models.py + controllers.py | Config: app.py:7-9
Source files:  4 files analyzed
               (app.py, controllers.py, models.py, database.py)
DB tables:     produtos, usuarios, pedidos, itens_pedido
               (schema criado em database.py:get_db() via CREATE TABLE IF
               NOT EXISTS; seed inline na mesma função)
================================
```

---

```
================================
ARCHITECTURE AUDIT REPORT
================================
Project: code-smells-project
Stack:   Python 3.x + Flask 3.1.1
Files:   4 analyzed | ~780 lines of code

## Summary
CRITICAL: 6 | HIGH: 4 | MEDIUM: 4 | LOW: 4

## Findings

### [CRITICAL] SQL Injection (AP-01)
File: models.py:28, models.py:47-50, models.py:57-61, models.py:68,
      models.py:92, models.py:109-111, models.py:126-129, models.py:140,
      models.py:148-151, models.py:155-166, models.py:173, models.py:188,
      models.py:192, models.py:220, models.py:224, models.py:280-281,
      models.py:289-296, app.py:69
Description: Todas as queries SQL são montadas por concatenação direta de
  strings com valores do request ou de parâmetros externos. Exemplos:
  `"SELECT * FROM produtos WHERE id = " + str(id)` (models.py:28),
  `"WHERE email = '" + email + "' AND senha = '" + senha + "'"` no login
  (models.py:109-111), `query += " AND (nome LIKE '%" + termo + "%'..."`
  na busca (models.py:289-296). O caso mais grave é app.py:59-78:
  o endpoint /admin/query aceita o campo `"sql"` do body JSON e executa
  qualquer SQL arbitrário diretamente no banco via `cursor.execute(query)`.
Impact: Leitura/alteração/destruição arbitrária do banco; bypass de
  autenticação via manipulação do login; exfiltração total de dados via
  /admin/query sem qualquer autenticação.
Recommendation: Substituir toda concatenação por placeholders `?`
  (→ PB-01). Remover ou proteger com credencial de ambiente o endpoint
  /admin/query (→ PB-14).

### [CRITICAL] Credenciais e segredos hardcoded (AP-02)
File: app.py:7, app.py:88
Description: `app.config["SECRET_KEY"] = "minha-chave-super-secreta-123"`
  (app.py:7) está literal no código. O mesmo valor vaza via /health
  (ver AP-04). Host, porta e debug=True também estão hardcoded em
  `app.run(host="0.0.0.0", port=5000, debug=True)` (app.py:88).
Impact: Segredo comitado no repositório; rotação exige deploy; a chave
  de sessão Flask pode ser usada para forjar cookies.
Recommendation: Extrair para variáveis de ambiente lidas via módulo de
  config + criar .env.example versionável (→ PB-02).

### [CRITICAL] Armazenamento inseguro de senhas (AP-03)
File: models.py:126-129, models.py:109-111, database.py:75-82
Description: `criar_usuario` persiste a senha em texto plano:
  `"INSERT INTO usuarios ... VALUES ('" + ... + "', '" + senha + "'..."`.
  `login_usuario` compara via SQL equality direto (models.py:109-111),
  tornando o login bypassável por SQL injection (AP-01). Os seeds de
  database.py já inserem usuários com senhas plaintext ("admin123",
  "123456", "senha123").
Impact: Vazamento do banco expõe todas as senhas; senhas reutilizadas por
  usuários ficam descobertas; compliance LGPD comprometido.
Recommendation: Usar `werkzeug.security.generate_password_hash` /
  `check_password_hash` (→ PB-03). Re-seeding após migração do schema.

### [CRITICAL] Exposição de dados sensíveis em respostas (AP-04)
File: models.py:79-87, models.py:94-103, controllers.py:283-291
Description: `get_todos_usuarios()` (models.py:82) e `get_usuario_por_id`
  (models.py:98) incluem `"senha": row["senha"]` no dicionário de
  resposta — portanto `GET /usuarios` e `GET /usuarios/<id>` retornam
  o hash/plaintext da senha de todos os usuários. Mais grave:
  controllers.py:289 inclui `"secret_key": "minha-chave-super-secreta-123"`
  diretamente na resposta pública de `GET /health`, junto com `db_path`,
  `debug: True` e `ambiente: "producao"`.
Impact: Qualquer cliente obtém senhas e a chave secreta do Flask via
  endpoints não autenticados; violação direta de LGPD/PCI.
Recommendation: Remover `senha` dos serializadores de usuário;
  sanitizar /health (→ PB-03, PB-12).

### [CRITICAL] God Module — models.py (AP-05)
File: models.py:1-314
Description: `models.py` acumula 4+ responsabilidades distintas sem
  separação: (1) acesso a dados por SQL para todos os domínios (produtos,
  usuários, pedidos, itens); (2) lógica de negócio — validação de estoque
  e cálculo de total em `criar_pedido` (models.py:133-168); (3) cálculo de
  desconto escalonado em `relatorio_vendas` (models.py:256-263); (4)
  formatação de resposta (row→dict) para todos os recursos.
Impact: Impossível testar unidades em isolamento; qualquer mudança em uma
  área arrisca outra; merge conflicts constantes; violação completa do
  Single Responsibility.
Recommendation: Decompor em models por domínio (ProdutoModel,
  UsuarioModel, PedidoModel) + services para regras de negócio
  (→ PB-04).

### [CRITICAL] Endpoints destrutivos/administrativos sem autenticação (AP-06)
File: app.py:47-57, app.py:59-78, app.py:28
Description: `POST /admin/reset-db` (app.py:47-57) apaga todas as
  tabelas sem verificação de identidade. `POST /admin/query` (app.py:59-78)
  executa SQL arbitrário sem autenticação. `GET /relatorios/vendas`
  (app.py:28) expõe dados financeiros anonimamente. Não existe nenhum
  middleware ou decorator de autenticação no projeto, apesar de haver
  endpoint `/login`.
Impact: Qualquer cliente da rede destrói o banco ou exfiltra todos os
  dados via /admin/query.
Recommendation: Remover /admin/reset-db e /admin/query do código de
  produção; proteger /relatorios com autenticação; implementar middleware
  de auth (→ PB-14).

### [HIGH] Lógica de negócio em controllers (AP-07)
File: controllers.py:43-55, controllers.py:64-93,
      controllers.py:208-210, controllers.py:247-250,
      models.py:256-263
Description: `criar_produto` e `atualizar_produto` executam validação
  de campos inline (preco, estoque, tamanho de nome, lista de categorias)
  — lógica replicada entre os dois handlers. `criar_pedido`
  (controllers.py:208-210) contém notificações simuladas (email, SMS,
  push) como `print` inline. `atualizar_status_pedido` (controllers.py:
  247-250) toma decisões de domínio (preparar envio, devolver estoque)
  no handler HTTP. `relatorio_vendas` em models.py:256-263 calcula
  desconto escalonado com limiares hardcoded dentro do model.
Impact: Regras de negócio impossíveis de testar sem HTTP; duplicação
  explode com novos endpoints; controllers com centenas de linhas.
Recommendation: Mover validação para schemas/services; mover regras de
  notificação e desconto para um service layer (→ PB-05).

### [HIGH] Estado global mutável — conexão singleton (AP-08)
File: database.py:4, database.py:7-12
Description: `db_connection = None` (database.py:4) é uma variável
  global de módulo. `get_db()` usa `global db_connection` e cria a
  conexão com `check_same_thread=False` para contornar o compartilhamento
  entre threads do Werkzeug. Schema e seeds também rodam dentro dessa
  função, acoplando inicialização ao primeiro request.
Impact: Race conditions em ambiente multi-thread; impossibilidade de
  escalar horizontalmente; vazamento de estado entre requests.
Recommendation: Usar `flask.g` + teardown de contexto para conexão por
  request; separar schema/seeds do get_db (→ PB-06).

### [HIGH] Error handling ausente e não centralizado (AP-09)
File: controllers.py:5-12, controllers.py:14-22, controllers.py:24-62,
      controllers.py:64-96, controllers.py:98-109, controllers.py:111-126,
      controllers.py:128-134, controllers.py:136-144, controllers.py:146-165,
      controllers.py:167-186, controllers.py:188-220, controllers.py:222-227,
      controllers.py:229-235, controllers.py:237-255, controllers.py:257-262,
      controllers.py:264-292
Description: Todos os 16 handlers em controllers.py copiam o mesmo
  bloco `try/except Exception as e: return jsonify({"erro": str(e)}), 500`.
  `str(e)` devolve detalhes internos de exceção (nomes de coluna, paths,
  erros de SQL) diretamente ao cliente. Não existe `@app.errorhandler`
  global registrado em app.py.
Impact: Vazamento de detalhes internos; comportamento inconsistente;
  erros 500 com mensagens cruas entregues ao frontend.
Recommendation: Criar handler global via `@app.errorhandler(Exception)` e
  exceções de domínio tipadas; remover try/except dos handlers
  (→ PB-07).

### [HIGH] Configuração insegura de produção (AP-10)
File: app.py:8, app.py:9, app.py:88
Description: `app.config["DEBUG"] = True` hardcoded (app.py:8) habilita
  o debugger interativo do Werkzeug, que permite execução remota de código
  via PIN. `CORS(app)` sem parâmetro `origins` (app.py:9) libera
  qualquer origem. `app.run(debug=True)` reconfirma o debug (app.py:88).
Impact: Execução remota de código via console Werkzeug; CORS irrestrito
  permite CSRF e requests cross-origin de qualquer domínio.
Recommendation: Ler DEBUG e CORS_ORIGINS de variáveis de ambiente com
  default seguro (False / lista explícita) (→ PB-02).

### [MEDIUM] Queries N+1 (AP-11)
File: models.py:186-200, models.py:219-231, models.py:154-166
Description: Em `get_pedidos_usuario` (models.py:186-200) e
  `get_todos_pedidos` (models.py:219-231): para cada pedido há um SELECT
  em `itens_pedido`, e para cada item há um SELECT em `produtos` para
  buscar o nome — resultando em 1 + N + N×M queries. Em `criar_pedido`
  (models.py:154-166) há SELECTs e UPDATEs por item dentro de loop.
Impact: Latência cresce linearmente com volume; banco sobrecarregado em
  listagens com muitos pedidos/itens.
Recommendation: Usar JOIN ou subconsulta para trazer itens e nome do
  produto numa única query por pedido (→ PB-08).

### [MEDIUM] Duplicação de código — DRY (AP-12)
File: models.py:12-21 vs models.py:31-40, models.py:78-86 vs
      models.py:94-103, models.py:178-200 vs models.py:210-231,
      controllers.py:43-55 vs controllers.py:76-95
Description: O mapeamento `row→dict` de produtos é idêntico em
  `get_todos_produtos` e `get_produto_por_id` (mesmos 8 campos). O de
  usuários é idêntico em `get_todos_usuarios` e `get_usuario_por_id`.
  O bloco de montagem de pedido com itens é quase idêntico em
  `get_pedidos_usuario` e `get_todos_pedidos`. A lógica de validação de
  produto (preco, estoque, nome, categoria) está duplicada em
  `criar_produto` e `atualizar_produto`.
Impact: Correção de qualquer campo exige atualização em múltiplos pontos;
  divergência silenciosa já existe.
Recommendation: Extrair funções de serialização canônicas no model e
  função/schema de validação única (→ PB-10).

### [MEDIUM] Validação de entrada incompleta (AP-14)
File: controllers.py:146-165, controllers.py:188-207, controllers.py:237-255
Description: `criar_usuario` (controllers.py:146-165) não valida formato
  de email (aceita "abc" sem @), não verifica unicidade de email no banco
  (permite duplicatas). `criar_pedido` (controllers.py:195) não verifica
  se `usuario_id` existe antes de inserir o pedido. `atualizar_status_pedido`
  (controllers.py:238) acessa `dados.get("status")` sem verificar se o
  body JSON é None (lança AttributeError → 500 em request sem body).
Impact: Dados inconsistentes no banco; 500 em lugar de 400 em inputs
  malformados; email duplicado cria múltiplas contas.
Recommendation: Validar formato de email (stdlib `email.utils`);
  checar unicidade antes do INSERT; garantir body não-nulo
  antes de .get() (→ PB-10).

### [MEDIUM] Integridade referencial ausente (AP-15)
File: database.py:38-52, controllers.py:98-108
Description: As tabelas `pedidos` e `itens_pedido` declaram `usuario_id`,
  `pedido_id`, `produto_id` mas sem cláusula `FOREIGN KEY` nem
  `ON DELETE` (database.py:38-52). `deletar_produto` (controllers.py:
  98-108) remove o produto sem tratar `itens_pedido` que referenciam
  esse produto, deixando registros órfãos.
Impact: Remoção de produto corrompe histórico de pedidos; queries de
  relatório retornam "Desconhecido" para itens órfãos; banco aceita
  usuário_id ou produto_id inexistente em pedidos.
Recommendation: Adicionar FOREIGN KEY + ON DELETE RESTRICT/SET NULL ao
  schema; tratar ou cascatear deleção de itens no model (→ PB-08, PB-04).

### [LOW] print como logging (AP-16)
File: controllers.py:8, 11, 57, 61, 106, 161, 179, 181, 208-210, 219,
      247-250; app.py:56, 83-85
Description: 15+ chamadas a `print()` espalhadas para eventos de
  aplicação (criou produto, deletou, login, erros) e notificações de
  domínio (email/SMS/push simulados). Não há logger com níveis, timestamp
  ou destino configurável.
Impact: Sem níveis de severidade; sem timestamp; ruído indiferenciado
  em produção; `print` para stderr bloqueia em alguns ambientes WSGI.
Recommendation: Substituir por `logging.getLogger(__name__)` com nível
  configurável por variável de ambiente (→ PB-12).

### [LOW] Magic numbers & strings (AP-17)
File: models.py:257-263, controllers.py:52-53, controllers.py:242,
      controllers.py:47-50
Description: Limiares de desconto `10000`, `5000`, `1000` e taxas
  `0.1`, `0.05`, `0.02` soltos em expressões (models.py:257-263). Lista
  de categorias válidas `["informatica", "moveis", ...]` inline no handler
  (controllers.py:52). Lista de status de pedido `["pendente", "aprovado",
  ...]` inline (controllers.py:242). Limites de tamanho de nome `2` e
  `200` sem nome (controllers.py:47-50).
Impact: Significado opaco; mudanças de regra exigem caça por todo o
  código; listas divergem silenciosamente se definidas em mais de um lugar.
Recommendation: Extrair para constantes nomeadas em módulo `constants.py`
  (→ PB-13).

### [LOW] Importações não usadas (AP-19)
File: models.py:2, controllers.py:3
Description: `import sqlite3` em models.py:2 nunca é usado diretamente
  (todo acesso ao banco passa por `database.get_db()`). `from database
  import get_db` em controllers.py:3 é usado apenas em `health_check`;
  se esse handler migrar para um controller dedicado, o import ficará
  órfão.
Impact: Ruído; dependência fantasma; `import sqlite3` sugere falsamente
  que models.py acessa o banco independentemente.
Recommendation: Remover `import sqlite3` de models.py; avaliar relocação
  de health_check (→ PB-15).

================================
Total: 18 findings
================================
```

---

```
Phase 2 complete. Proceed with refactoring (Phase 3)? [y/n]
```
