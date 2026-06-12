# Playbook de Refatoração (Fase 3)

Transformações concretas para cada anti-pattern do catálogo. Os exemplos usam Python/Flask e Node.js/Express, mas o **padrão** de cada transformação é agnóstico — transponha o mesmo desenho para a stack detectada. Aplique na ordem do relatório (CRITICAL → LOW); várias transformações se compõem (ex.: PB-04 cria os lugares para onde PB-05 move código).

---

## PB-01 — Parametrizar queries SQL (corrige AP-01)

Toda interpolação/concatenação de valor externo em SQL vira placeholder + tupla de parâmetros.

**Antes (Python):**
```python
cursor.execute("SELECT * FROM produtos WHERE id = " + str(id))
cursor.execute(
    "INSERT INTO usuarios (nome, email) VALUES ('" + nome + "', '" + email + "')"
)
query = "SELECT * FROM produtos WHERE 1=1"
if termo:
    query += " AND nome LIKE '%" + termo + "%'"
```

**Depois (Python):**
```python
cursor.execute("SELECT * FROM produtos WHERE id = ?", (id,))
cursor.execute(
    "INSERT INTO usuarios (nome, email) VALUES (?, ?)", (nome, email)
)
query, params = "SELECT * FROM produtos WHERE 1=1", []
if termo:
    query += " AND nome LIKE ?"
    params.append(f"%{termo}%")
cursor.execute(query, params)
```

**Node:** `db.get("SELECT ... WHERE id = ?", [id], cb)` — o driver escapa. Filtros dinâmicos acumulam `clauses`/`params` em arrays e nunca interpolam o valor. Placeholders variam por driver (`?` sqlite/mysql, `%s` psycopg2, `$1` pg) — use o da stack.

---

## PB-02 — Extrair configuração para módulo + variáveis de ambiente (corrige AP-02, AP-10)

Um único módulo de config lê o ambiente com defaults seguros; o resto do código importa dele. Crie `.env.example` documentando as variáveis (sem valores reais) e garanta `.env` no `.gitignore`.

**Antes (Python):**
```python
app.config["SECRET_KEY"] = "minha-chave-super-secreta-123"
app.config["DEBUG"] = True
app.run(host="0.0.0.0", port=5000, debug=True)
```

**Depois (Python — `config/settings.py`):**
```python
import os

SECRET_KEY = os.environ.get("SECRET_KEY", "dev-only-change-me")
DEBUG = os.environ.get("FLASK_DEBUG", "0") == "1"          # default seguro: off
HOST = os.environ.get("HOST", "127.0.0.1")
PORT = int(os.environ.get("PORT", "5000"))
DATABASE_PATH = os.environ.get("DATABASE_PATH", "loja.db")
CORS_ORIGINS = os.environ.get("CORS_ORIGINS", "*")          # restrinja em produção
```

**Antes (Node):** `const config = { dbPass: "senha_super_secreta_prod_123", paymentGatewayKey: "pk_live_..." }`

**Depois (Node — `config/index.js`):**
```js
module.exports = {
    port: parseInt(process.env.PORT || '3000', 10),
    paymentGatewayKey: process.env.PAYMENT_GATEWAY_KEY || '',
    adminToken: process.env.ADMIN_TOKEN || '',
};
```

Segredos que estavam commitados devem ser tratados como **vazados**: a recomendação de rotacioná-los entra no output final.

---

## PB-03 — Senhas com hash real + serialização sem campos sensíveis (corrige AP-03, AP-04)

Use o utilitário de senha idiomático da stack (nada de MD5/SHA1/base64 caseiro) e remova campos sensíveis de toda serialização.

**Antes (Python):**
```python
self.password = hashlib.md5(pwd.encode()).hexdigest()
def to_dict(self):
    return {"id": self.id, "email": self.email, "password": self.password}
```

**Depois (Python — werkzeug já vem com Flask):**
```python
from werkzeug.security import generate_password_hash, check_password_hash

def set_password(self, pwd):
    self.password = generate_password_hash(pwd)

def check_password(self, pwd):
    return check_password_hash(self.password, pwd)

def to_dict(self):
    return {"id": self.id, "email": self.email}   # nunca expor password/hash
```

**Depois (Node — stdlib `crypto.scrypt`, sem dependência nova):**
```js
const crypto = require('crypto');
function hashPassword(pwd) {
    const salt = crypto.randomBytes(16).toString('hex');
    return `${salt}:${crypto.scryptSync(pwd, salt, 64).toString('hex')}`;
}
function verifyPassword(pwd, stored) {
    const [salt, hash] = stored.split(':');
    return crypto.timingSafeEqual(Buffer.from(hash, 'hex'), crypto.scryptSync(pwd, salt, 64));
}
```

**Migração de dados existentes:** senhas legadas (texto plano/MD5) não são recuperáveis com segurança — re-hash no seed; em banco real, forçar reset. Documente a escolha. Login nunca compara senha com `==` em SQL.

---

## PB-04 — Decompor God Class/Module em camadas MVC (corrige AP-05)

Migre por responsabilidade, nesta ordem: (1) config → `config/`; (2) schema/seed/conexão → `database.*`; (3) acesso a dados por entidade → `models/`; (4) fluxo de cada endpoint → `controllers/`; (5) registro de rotas → `routes|views/`; (6) entry point vira composition root. Remova a classe original ao final.

**Antes (Node — esqueleto):**
```js
class AppManager {
    constructor() { this.db = new sqlite3.Database(':memory:'); }
    initDb() { /* CREATE TABLE + seeds */ }
    setupRoutes(app) {
        app.post('/api/checkout', (req, res) => { /* validação + pagamento + 3 INSERTs */ });
    }
}
```

**Depois (Node — esqueleto):**
```js
// database.js  → cria conexão, schema e seeds; exporta helpers promisificados
// models/enrollmentModel.js → create(userId, courseId), ...
// controllers/checkoutController.js → valida, chama models/services, monta resposta
// routes/index.js:
router.post('/api/checkout', checkoutController.checkout);
// app.js (composition root):
const app = express();
app.use(express.json());
initDb();
app.use(routes);
app.use(errorHandler);
app.listen(config.port);
```

A mesma receita vale para "models" monolíticos em Python: um arquivo por entidade em `models/`, fluxos em `controllers/<entidade>_controller.py`, mapeamento de rotas em `views/routes.py`.

---

## PB-05 — Afinar controllers: regra de negócio para models/services (corrige AP-07)

O controller valida entrada, chama o model/service e decide o status HTTP — só.

**Antes (Python — tudo no handler):**
```python
def criar_pedido():
    dados = request.get_json()
    # 30 linhas: valida itens, busca produto a produto, soma total,
    # checa estoque, insere pedido + itens, dá baixa, "envia" notificações
```

**Depois (Python):**
```python
# controllers/pedido_controller.py
def criar_pedido():
    dados = request.get_json(silent=True) or {}
    usuario_id, itens = dados.get("usuario_id"), dados.get("itens", [])
    if not usuario_id or not itens:
        raise ValidationError("usuario_id e itens são obrigatórios")
    pedido = pedido_model.criar(usuario_id, itens)       # transação + regras no model
    notification_service.pedido_criado(pedido)           # efeito colateral isolado
    return jsonify({"dados": pedido, "sucesso": True}), 201
```

Cálculos puros (total, desconto, atraso) viram métodos do model — testáveis sem HTTP. Decisão de pagamento/integração externa vai para um service injetável, nunca decidida inline no handler.

---

## PB-06 — Eliminar estado global mutável (corrige AP-08)

**Antes (Python):**
```python
db_connection = None
def get_db():
    global db_connection
    if db_connection is None:
        db_connection = sqlite3.connect(db_path, check_same_thread=False)
    return db_connection
```

**Depois (Python/Flask — conexão por request via `g`):**
```python
from flask import g
def get_db():
    if "db" not in g:
        g.db = sqlite3.connect(settings.DATABASE_PATH)
        g.db.row_factory = sqlite3.Row
    return g.db

def close_db(_exc=None):
    if (db := g.pop("db", None)) is not None:
        db.close()
# no composition root: app.teardown_appcontext(close_db)
```

Caches/acumuladores globais de módulo: se forem dead code, remova (PB-15); se forem necessários, viram serviço explícito recebido por parâmetro (injeção), nunca import de variável mutável.

---

## PB-07 — Error handling centralizado (corrige AP-09)

Exceções de domínio + um handler global; os handlers de rota param de repetir try/catch.

**Depois (Python — `middlewares/error_handler.py`):**
```python
class AppError(Exception):
    status_code = 500
class ValidationError(AppError):
    status_code = 400
class NotFoundError(AppError):
    status_code = 404

def register_error_handlers(app):
    @app.errorhandler(AppError)
    def handle_app_error(e):
        return jsonify({"erro": str(e), "sucesso": False}), e.status_code

    @app.errorhandler(Exception)
    def handle_unexpected(e):
        logger.exception("Erro não tratado")
        return jsonify({"erro": "Erro interno do servidor"}), 500   # sem str(e) ao cliente
```

**Depois (Node — último middleware do `app.js`):**
```js
function errorHandler(err, req, res, next) {
    const status = err.statusCode || 500;
    if (status >= 500) console.error(err);
    res.status(status).json({ error: status >= 500 ? 'Erro interno' : err.message });
}
```

Controllers lançam (`raise NotFoundError(...)` / `next(err)`); nunca devolvem `str(e)` cru. Remova os `except:`/`catch` genéricos que isso torna redundantes.

---

## PB-08 — Eliminar N+1 e garantir transação/integridade (corrige AP-11, AP-15)

**Antes (Python — 1 + N + N×M queries):**
```python
for row in cursor.execute("SELECT * FROM pedidos"):
    itens = cursor2.execute("SELECT * FROM itens_pedido WHERE pedido_id = ?", (row["id"],))
    for item in itens:
        nome = cursor3.execute("SELECT nome FROM produtos WHERE id = ?", (item["produto_id"],))
```

**Depois (Python — 2 queries com JOIN + montagem em memória):**
```python
pedidos = {r["id"]: dict(r, itens=[]) for r in cursor.execute("SELECT * FROM pedidos")}
itens = cursor.execute("""
    SELECT ip.pedido_id, ip.quantidade, ip.preco_unitario, p.nome AS produto_nome
    FROM itens_pedido ip JOIN produtos p ON p.id = ip.produto_id
""")
for item in itens:
    pedidos[item["pedido_id"]]["itens"].append(dict(item))
```

Com ORM: eager loading (`selectinload`/`joinedload`) ou agregação no banco (`GROUP BY` + `COUNT`) em vez de contar/filtrar em loop Python. Em Node, o mesmo JOIN substitui pirâmides de `db.get` com contadores manuais.

**Integridade:** declare `FOREIGN KEY ... ON DELETE` no schema (ou cascade no relacionamento do ORM); operações multi-tabela (criar pedido + itens + baixa de estoque; deletar pai + filhos) rodam em **uma transação** dentro do model — `BEGIN ... COMMIT/ROLLBACK`, nunca loops de DELETE no handler.

---

## PB-09 — Modernizar APIs deprecated (corrige AP-13)

Aplique a tabela do AP-13. Exemplos mais comuns:

```python
# Antes                                  # Depois
datetime.utcnow()                        datetime.now(timezone.utc)
Model.query.get(id)                      db.session.get(Model, id)
@app.before_first_request                inicialização explícita no create_app()
```

```js
// Antes                                 // Depois
new Buffer(data)                         Buffer.from(data)
url.parse(href)                          new URL(href)
db.get(sql, cb) aninhados                await dbGet(sql, params)   // ver PB-11
```

Atenção a contratos: `datetime.now(timezone.utc)` é timezone-aware — ao comparar com datas naive vindas do banco, normalize (compare ambos em UTC naive ou converta na leitura). Rode a aplicação após a troca para confirmar zero `DeprecationWarning`/`LegacyAPIWarning` no log.

---

## PB-10 — Unificar serialização e validação (corrige AP-12, AP-14, AP-18)

Uma única fonte de verdade por entidade: serialização no model (`to_dict`), validação num validador reaproveitado por create/update, constantes compartilhadas.

**Antes:** o mesmo dict montado campo a campo em 3 rotas; a mesma lista `['pending', 'in_progress', ...]` repetida inline; regex de email duplicado.

**Depois (Python):**
```python
# models/task_model.py
VALID_STATUSES = ("pending", "in_progress", "done", "cancelled")

def to_dict(self, include_overdue=False):
    data = {...}                       # ÚNICO lugar que serializa Task
    if include_overdue:
        data["overdue"] = self.is_overdue()
    return data

# controllers/task_controller.py
def _validate_payload(data, partial=False):
    """Valida presença/tipo/intervalo; levanta ValidationError. Usada por create E update."""
```

Regras de validação: presença → tipo (`isinstance`) → formato (regex/parse) → intervalo/enum → unicidade. Conversões de query string (`int(...)`) sempre com tratamento que vira 400, não 500. Payloads com nomes crípticos existentes: mantenha a compatibilidade de leitura, documente a melhoria sugerida no output final (não quebre clientes).

---

## PB-11 — Achatar callback hell com async/await (Node)

**Antes:**
```js
this.db.get("SELECT ...", [cid], (err, course) => {
    this.db.get("SELECT ...", [e], (err, user) => {
        this.db.run("INSERT ...", [...], function (err) {
            self.db.run("INSERT ...", [...], function (err) { /* ... */ });
        });
    });
});
```

**Depois (promisificar uma vez no `database.js`):**
```js
const { promisify } = require('util');
const dbGet = promisify(db.get.bind(db));
const dbAll = promisify(db.all.bind(db));
function dbRun(sql, params = []) {           // preserva this.lastID
    return new Promise((resolve, reject) =>
        db.run(sql, params, function (err) {
            err ? reject(err) : resolve({ lastID: this.lastID, changes: this.changes });
        }));
}

// controller
async function checkout(req, res, next) {
    try {
        const course = await courseModel.findActive(courseId);
        if (!course) throw new NotFoundError('Curso não encontrado');
        const enrollment = await enrollmentModel.create(userId, course.id);
        res.status(200).json({ msg: 'Sucesso', enrollment_id: enrollment.lastID });
    } catch (err) { next(err); }
}
```

Padrões de "contador de pendências" para agregar resultados viram `await` sequencial ou `Promise.all`.

---

## PB-12 — Logging estruturado (corrige AP-16; apoia AP-04)

**Python:** `logging` da stdlib — `logger = logging.getLogger(__name__)`; `logging.basicConfig(level=...)` no entry point; `logger.info/warning/exception` no lugar de `print`. **Node:** wrapper mínimo sobre `console` com níveis e timestamp (ou lib se o projeto já tiver). **Regra de ouro:** nunca logar senha, cartão, token ou chave — substitua por redação (`****1234`) ou remova o log.

---

## PB-13 — Constantes nomeadas para magic numbers/strings (corrige AP-17)

```python
# Antes
if faturamento > 10000:
    desconto = faturamento * 0.1

# Depois (no model do domínio correspondente)
DISCOUNT_TIERS = ((10_000, 0.10), (5_000, 0.05), (1_000, 0.02))
def calcular_desconto(faturamento):
    return next((faturamento * taxa for piso, taxa in DISCOUNT_TIERS if faturamento > piso), 0)
```

Enums/listas de status, roles e categorias: declarar uma vez (model ou constants) e importar em todo uso. Se o projeto já tem o módulo de constantes mas não o usa, **passe a usá-lo** em vez de criar outro.

---

## PB-14 — Proteger endpoints administrativos/destrutivos (corrige AP-06; ver política nas guidelines)

```python
# middlewares/auth.py
def require_admin_token(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        expected = settings.ADMIN_TOKEN
        provided = request.headers.get("X-Admin-Token", "")
        if not expected or not secrets.compare_digest(provided, expected):
            raise ForbiddenError("Acesso negado")
        return view(*args, **kwargs)
    return wrapped
```

Aplique o decorator/middleware às rotas administrativas. Sem `ADMIN_TOKEN` no ambiente → 403 sempre (seguro por default). Endpoints cuja única função é insegura (console SQL) ficam protegidos E marcados para remoção em `Security Contract Changes`.

---

## PB-15 — Remover dead code com segurança (corrige AP-19)

1. Confirme ausência de referências (grep pelo símbolo no projeto inteiro, incluindo scripts).
2. Remova imports não usados, funções nunca chamadas, variáveis exportadas e nunca lidas, condicionais redundantes (`if x: return True else: return False` → `return bool(x)`).
3. Serviços inteiros não referenciados: se implementam funcionalidade claramente pretendida (ex.: notificações), prefira **integrá-los** na camada correta (chamados pelo controller/service) a deletá-los — registre a decisão no output final; caso contrário, remova.
4. Rode a validação completa após a limpeza (imports quebrados aparecem no boot).
