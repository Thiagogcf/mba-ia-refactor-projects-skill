from werkzeug.security import generate_password_hash, check_password_hash
from database import get_db


def to_dict(row):
    return {
        "id":        row["id"],
        "nome":      row["nome"],
        "email":     row["email"],
        "tipo":      row["tipo"],
        "criado_em": row["criado_em"],
    }


def get_todos():
    db = get_db()
    return [to_dict(r) for r in db.execute("SELECT * FROM usuarios").fetchall()]


def get_por_id(usuario_id):
    db = get_db()
    row = db.execute("SELECT * FROM usuarios WHERE id = ?", (usuario_id,)).fetchone()
    return to_dict(row) if row else None


def email_existe(email):
    db = get_db()
    return db.execute("SELECT id FROM usuarios WHERE email = ?", (email,)).fetchone() is not None


def criar(nome, email, senha, tipo="cliente"):
    db = get_db()
    senha_hash = generate_password_hash(senha)
    cursor = db.execute(
        "INSERT INTO usuarios (nome, email, senha, tipo) VALUES (?, ?, ?, ?)",
        (nome, email, senha_hash, tipo),
    )
    db.commit()
    return cursor.lastrowid


def autenticar(email, senha):
    db = get_db()
    row = db.execute("SELECT * FROM usuarios WHERE email = ?", (email,)).fetchone()
    if row and check_password_hash(row["senha"], senha):
        return to_dict(row)
    return None
