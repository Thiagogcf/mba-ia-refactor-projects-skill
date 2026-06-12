import sqlite3
from database import get_db
from middlewares.error_handler import ConflictError

CATEGORIAS_VALIDAS = ("informatica", "moveis", "vestuario", "geral", "eletronicos", "livros")
NOME_MIN_LEN = 2
NOME_MAX_LEN = 200


def to_dict(row):
    return {
        "id":         row["id"],
        "nome":       row["nome"],
        "descricao":  row["descricao"],
        "preco":      row["preco"],
        "estoque":    row["estoque"],
        "categoria":  row["categoria"],
        "ativo":      row["ativo"],
        "criado_em":  row["criado_em"],
    }


def get_todos():
    db = get_db()
    return [to_dict(r) for r in db.execute("SELECT * FROM produtos").fetchall()]


def get_por_id(produto_id):
    db = get_db()
    row = db.execute("SELECT * FROM produtos WHERE id = ?", (produto_id,)).fetchone()
    return to_dict(row) if row else None


def criar(nome, descricao, preco, estoque, categoria):
    db = get_db()
    cursor = db.execute(
        "INSERT INTO produtos (nome, descricao, preco, estoque, categoria) VALUES (?, ?, ?, ?, ?)",
        (nome, descricao, preco, estoque, categoria),
    )
    db.commit()
    return cursor.lastrowid


def atualizar(produto_id, nome, descricao, preco, estoque, categoria):
    db = get_db()
    db.execute(
        "UPDATE produtos SET nome = ?, descricao = ?, preco = ?, estoque = ?, categoria = ? WHERE id = ?",
        (nome, descricao, preco, estoque, categoria, produto_id),
    )
    db.commit()


def deletar(produto_id):
    db = get_db()
    try:
        db.execute("DELETE FROM produtos WHERE id = ?", (produto_id,))
        db.commit()
    except sqlite3.IntegrityError:
        db.rollback()
        raise ConflictError("Produto referenciado em pedidos e não pode ser deletado")


def buscar(termo, categoria=None, preco_min=None, preco_max=None):
    db = get_db()
    query = "SELECT * FROM produtos WHERE 1=1"
    params = []
    if termo:
        query += " AND (nome LIKE ? OR descricao LIKE ?)"
        params.extend([f"%{termo}%", f"%{termo}%"])
    if categoria:
        query += " AND categoria = ?"
        params.append(categoria)
    if preco_min is not None:
        query += " AND preco >= ?"
        params.append(preco_min)
    if preco_max is not None:
        query += " AND preco <= ?"
        params.append(preco_max)
    return [to_dict(r) for r in db.execute(query, params).fetchall()]
