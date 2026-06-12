import sqlite3
from flask import g
from config import settings

_SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS produtos (
    id        INTEGER PRIMARY KEY AUTOINCREMENT,
    nome      TEXT    NOT NULL,
    descricao TEXT,
    preco     REAL    NOT NULL,
    estoque   INTEGER NOT NULL DEFAULT 0,
    categoria TEXT    NOT NULL,
    ativo     INTEGER NOT NULL DEFAULT 1,
    criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS usuarios (
    id        INTEGER PRIMARY KEY AUTOINCREMENT,
    nome      TEXT NOT NULL,
    email     TEXT NOT NULL UNIQUE,
    senha     TEXT NOT NULL,
    tipo      TEXT NOT NULL DEFAULT 'cliente',
    criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS pedidos (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    usuario_id  INTEGER NOT NULL,
    status      TEXT    NOT NULL DEFAULT 'pendente',
    total       REAL    NOT NULL,
    criado_em   TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (usuario_id) REFERENCES usuarios(id) ON DELETE RESTRICT
);
CREATE TABLE IF NOT EXISTS itens_pedido (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    pedido_id       INTEGER NOT NULL,
    produto_id      INTEGER NOT NULL,
    quantidade      INTEGER NOT NULL,
    preco_unitario  REAL    NOT NULL,
    FOREIGN KEY (pedido_id)  REFERENCES pedidos(id)  ON DELETE CASCADE,
    FOREIGN KEY (produto_id) REFERENCES produtos(id) ON DELETE RESTRICT
);
"""

_SEED_PRODUTOS = [
    ("Notebook Gamer",  "Notebook potente para jogos",   5999.99, 10,  "informatica"),
    ("Mouse Wireless",  "Mouse sem fio ergonômico",       89.90,  50,  "informatica"),
    ("Teclado Mecânico","Teclado mecânico RGB",           299.90,  30, "informatica"),
    ("Monitor 27''",    "Monitor 27 polegadas 144hz",    1899.90,  15, "informatica"),
    ("Headset Gamer",   "Headset com microfone",          199.90,  25, "informatica"),
    ("Cadeira Gamer",   "Cadeira ergonômica",            1299.90,   8, "moveis"),
    ("Webcam HD",       "Webcam 1080p",                   249.90,  20, "informatica"),
    ("Hub USB",         "Hub USB 3.0 7 portas",            79.90,  40, "informatica"),
    ("SSD 1TB",         "SSD NVMe 1TB",                   449.90,  35, "informatica"),
    ("Camiseta Dev",    "Camiseta estampa código",         59.90, 100, "vestuario"),
]


def get_db():
    if "db" not in g:
        g.db = sqlite3.connect(settings.DATABASE_PATH)
        g.db.row_factory = sqlite3.Row
        g.db.execute("PRAGMA foreign_keys = ON")
    return g.db


def close_db(_exc=None):
    db = g.pop("db", None)
    if db is not None:
        db.close()


def init_db(app):
    with app.app_context():
        db = get_db()
        db.executescript(_SCHEMA_SQL)
        db.commit()
        _seed_if_empty(db)


def _seed_if_empty(db):
    from werkzeug.security import generate_password_hash

    if db.execute("SELECT COUNT(*) FROM produtos").fetchone()[0] > 0:
        return

    db.executemany(
        "INSERT INTO produtos (nome, descricao, preco, estoque, categoria) VALUES (?, ?, ?, ?, ?)",
        _SEED_PRODUTOS,
    )
    seed_usuarios = [
        ("Admin",        "admin@loja.com",  generate_password_hash("admin123"), "admin"),
        ("João Silva",   "joao@email.com",  generate_password_hash("123456"),   "cliente"),
        ("Maria Santos", "maria@email.com", generate_password_hash("senha123"), "cliente"),
    ]
    db.executemany(
        "INSERT INTO usuarios (nome, email, senha, tipo) VALUES (?, ?, ?, ?)",
        seed_usuarios,
    )
    db.commit()
