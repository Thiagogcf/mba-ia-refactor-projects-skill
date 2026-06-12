import logging
from flask import request, jsonify
import models.pedido_model as pedido_model
import models.usuario_model as usuario_model
from middlewares.error_handler import ValidationError, NotFoundError

logger = logging.getLogger(__name__)


def criar_pedido():
    dados      = request.get_json(silent=True) or {}
    usuario_id = dados.get("usuario_id")
    itens      = dados.get("itens", [])

    if not usuario_id:
        raise ValidationError("usuario_id é obrigatório")
    if not itens:
        raise ValidationError("Pedido deve ter pelo menos 1 item")
    if not usuario_model.get_por_id(usuario_id):
        raise NotFoundError("Usuário não encontrado")

    resultado = pedido_model.criar(usuario_id, itens)
    logger.info(
        "Pedido %d criado para usuário %d — total R$ %.2f",
        resultado["pedido_id"], usuario_id, resultado["total"],
    )
    logger.debug("Notificação: enviar email/SMS/push para pedido %d", resultado["pedido_id"])
    return jsonify({"dados": resultado, "sucesso": True, "mensagem": "Pedido criado com sucesso"}), 201


def listar_todos_pedidos():
    pedidos = pedido_model.get_todos()
    return jsonify({"dados": pedidos, "sucesso": True}), 200


def listar_pedidos_usuario(usuario_id):
    pedidos = pedido_model.get_por_usuario(usuario_id)
    return jsonify({"dados": pedidos, "sucesso": True}), 200


def atualizar_status_pedido(pedido_id):
    dados      = request.get_json(silent=True) or {}
    novo_status = dados.get("status", "")

    if novo_status not in pedido_model.STATUS_VALIDOS:
        raise ValidationError(f"Status inválido. Válidos: {list(pedido_model.STATUS_VALIDOS)}")

    pedido_model.atualizar_status(pedido_id, novo_status)
    logger.info("Pedido %d: status atualizado para '%s'", pedido_id, novo_status)
    return jsonify({"sucesso": True, "mensagem": "Status atualizado"}), 200


def relatorio_vendas():
    relatorio = pedido_model.relatorio_vendas()
    return jsonify({"dados": relatorio, "sucesso": True}), 200
