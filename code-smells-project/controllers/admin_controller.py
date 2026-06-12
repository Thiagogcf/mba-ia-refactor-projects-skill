import logging
from flask import request, jsonify
from database import get_db

logger = logging.getLogger(__name__)


def health_check():
    db = get_db()
    db.execute("SELECT 1")
    produtos = db.execute("SELECT COUNT(*) FROM produtos").fetchone()[0]
    usuarios = db.execute("SELECT COUNT(*) FROM usuarios").fetchone()[0]
    pedidos  = db.execute("SELECT COUNT(*) FROM pedidos").fetchone()[0]
    return jsonify({
        "status":   "ok",
        "database": "connected",
        "counts":   {"produtos": produtos, "usuarios": usuarios, "pedidos": pedidos},
        "versao":   "1.0.0",
    }), 200


def reset_database():
    db = get_db()
    db.execute("DELETE FROM itens_pedido")
    db.execute("DELETE FROM pedidos")
    db.execute("DELETE FROM produtos")
    db.execute("DELETE FROM usuarios")
    db.commit()
    logger.warning("Banco de dados resetado via /admin/reset-db")
    return jsonify({"mensagem": "Banco de dados resetado", "sucesso": True}), 200


def executar_query():
    """
    ATENÇÃO: endpoint de console SQL — protegido por X-Admin-Token mas marcado
    para remoção. Ver Security Contract Changes no relatório de refatoração.
    """
    dados = request.get_json(silent=True) or {}
    query = dados.get("sql", "").strip()
    if not query:
        return jsonify({"erro": "Query não informada"}), 400

    db = get_db()
    try:
        cursor = db.execute(query)
        if query.upper().startswith("SELECT"):
            result = [dict(row) for row in cursor.fetchall()]
            return jsonify({"dados": result, "sucesso": True}), 200
        db.commit()
        return jsonify({"mensagem": "Query executada", "sucesso": True}), 200
    except Exception as e:
        logger.exception("Erro ao executar query administrativa")
        return jsonify({"erro": str(e)}), 500
