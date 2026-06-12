from database import get_db
from middlewares.error_handler import NotFoundError, ValidationError

STATUS_VALIDOS = ("pendente", "aprovado", "enviado", "entregue", "cancelado")

DISCOUNT_TIERS = ((10_000, 0.10), (5_000, 0.05), (1_000, 0.02))


def _calcular_desconto(faturamento):
    return next(
        (faturamento * taxa for piso, taxa in DISCOUNT_TIERS if faturamento > piso),
        0,
    )


def _fetch_pedidos_com_itens(db, pedidos_rows):
    if not pedidos_rows:
        return []

    pedido_ids = [r["id"] for r in pedidos_rows]
    placeholders = ",".join("?" * len(pedido_ids))
    itens_rows = db.execute(
        f"""SELECT ip.pedido_id, ip.produto_id, ip.quantidade, ip.preco_unitario,
                   p.nome AS produto_nome
            FROM itens_pedido ip
            JOIN produtos p ON p.id = ip.produto_id
            WHERE ip.pedido_id IN ({placeholders})""",
        pedido_ids,
    ).fetchall()

    pedidos = {}
    for row in pedidos_rows:
        pedidos[row["id"]] = {
            "id":         row["id"],
            "usuario_id": row["usuario_id"],
            "status":     row["status"],
            "total":      row["total"],
            "criado_em":  row["criado_em"],
            "itens":      [],
        }
    for item in itens_rows:
        pedidos[item["pedido_id"]]["itens"].append({
            "produto_id":     item["produto_id"],
            "produto_nome":   item["produto_nome"],
            "quantidade":     item["quantidade"],
            "preco_unitario": item["preco_unitario"],
        })
    return list(pedidos.values())


def get_todos():
    db = get_db()
    rows = db.execute("SELECT * FROM pedidos").fetchall()
    return _fetch_pedidos_com_itens(db, rows)


def get_por_usuario(usuario_id):
    db = get_db()
    rows = db.execute(
        "SELECT * FROM pedidos WHERE usuario_id = ?", (usuario_id,)
    ).fetchall()
    return _fetch_pedidos_com_itens(db, rows)


def criar(usuario_id, itens):
    db = get_db()

    produto_ids = [item["produto_id"] for item in itens]
    placeholders = ",".join("?" * len(produto_ids))
    rows = db.execute(
        f"SELECT * FROM produtos WHERE id IN ({placeholders})", produto_ids
    ).fetchall()
    produtos_map = {row["id"]: row for row in rows}

    total = 0.0
    for item in itens:
        prod = produtos_map.get(item["produto_id"])
        if prod is None:
            raise NotFoundError(f"Produto {item['produto_id']} não encontrado")
        if prod["estoque"] < item["quantidade"]:
            raise ValidationError(f"Estoque insuficiente para {prod['nome']}")
        total += prod["preco"] * item["quantidade"]

    cursor = db.execute(
        "INSERT INTO pedidos (usuario_id, status, total) VALUES (?, 'pendente', ?)",
        (usuario_id, total),
    )
    pedido_id = cursor.lastrowid

    for item in itens:
        prod = produtos_map[item["produto_id"]]
        db.execute(
            "INSERT INTO itens_pedido (pedido_id, produto_id, quantidade, preco_unitario) VALUES (?, ?, ?, ?)",
            (pedido_id, item["produto_id"], item["quantidade"], prod["preco"]),
        )
        db.execute(
            "UPDATE produtos SET estoque = estoque - ? WHERE id = ?",
            (item["quantidade"], item["produto_id"]),
        )

    db.commit()
    return {"pedido_id": pedido_id, "total": total}


def atualizar_status(pedido_id, novo_status):
    db = get_db()
    db.execute(
        "UPDATE pedidos SET status = ? WHERE id = ?",
        (novo_status, pedido_id),
    )
    db.commit()


def relatorio_vendas():
    db = get_db()
    total_pedidos = db.execute("SELECT COUNT(*) FROM pedidos").fetchone()[0]
    faturamento = db.execute(
        "SELECT COALESCE(SUM(total), 0) FROM pedidos"
    ).fetchone()[0]
    pendentes  = db.execute("SELECT COUNT(*) FROM pedidos WHERE status = 'pendente'").fetchone()[0]
    aprovados  = db.execute("SELECT COUNT(*) FROM pedidos WHERE status = 'aprovado'").fetchone()[0]
    cancelados = db.execute("SELECT COUNT(*) FROM pedidos WHERE status = 'cancelado'").fetchone()[0]

    desconto = _calcular_desconto(faturamento)
    return {
        "total_pedidos":       total_pedidos,
        "faturamento_bruto":   round(faturamento, 2),
        "desconto_aplicavel":  round(desconto, 2),
        "faturamento_liquido": round(faturamento - desconto, 2),
        "pedidos_pendentes":   pendentes,
        "pedidos_aprovados":   aprovados,
        "pedidos_cancelados":  cancelados,
        "ticket_medio":        round(faturamento / total_pedidos, 2) if total_pedidos > 0 else 0,
    }
