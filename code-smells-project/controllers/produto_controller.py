import logging
from flask import request, jsonify
import models.produto_model as produto_model
from middlewares.error_handler import ValidationError, NotFoundError

logger = logging.getLogger(__name__)


def _validar_payload(dados):
    if not isinstance(dados, dict):
        raise ValidationError("Dados inválidos")
    nome     = dados.get("nome", "")
    preco    = dados.get("preco")
    estoque  = dados.get("estoque")
    categoria = dados.get("categoria", "geral")

    if not nome:
        raise ValidationError("Nome é obrigatório")
    if len(nome) < produto_model.NOME_MIN_LEN:
        raise ValidationError("Nome muito curto")
    if len(nome) > produto_model.NOME_MAX_LEN:
        raise ValidationError("Nome muito longo")
    if preco is None:
        raise ValidationError("Preço é obrigatório")
    if not isinstance(preco, (int, float)) or preco < 0:
        raise ValidationError("Preço não pode ser negativo")
    if estoque is None:
        raise ValidationError("Estoque é obrigatório")
    if not isinstance(estoque, int) or estoque < 0:
        raise ValidationError("Estoque não pode ser negativo")
    if categoria not in produto_model.CATEGORIAS_VALIDAS:
        raise ValidationError(
            f"Categoria inválida. Válidas: {list(produto_model.CATEGORIAS_VALIDAS)}"
        )


def listar_produtos():
    produtos = produto_model.get_todos()
    logger.info("Listando %d produtos", len(produtos))
    return jsonify({"dados": produtos, "sucesso": True}), 200


def buscar_produtos():
    termo        = request.args.get("q", "")
    categoria    = request.args.get("categoria") or None
    preco_min_r  = request.args.get("preco_min")
    preco_max_r  = request.args.get("preco_max")
    try:
        preco_min = float(preco_min_r) if preco_min_r else None
        preco_max = float(preco_max_r) if preco_max_r else None
    except ValueError:
        raise ValidationError("preco_min e preco_max devem ser numéricos")
    resultados = produto_model.buscar(termo, categoria, preco_min, preco_max)
    return jsonify({"dados": resultados, "total": len(resultados), "sucesso": True}), 200


def buscar_produto(id):
    produto = produto_model.get_por_id(id)
    if not produto:
        raise NotFoundError("Produto não encontrado")
    return jsonify({"dados": produto, "sucesso": True}), 200


def criar_produto():
    dados = request.get_json(silent=True) or {}
    _validar_payload(dados)
    novo_id = produto_model.criar(
        dados["nome"],
        dados.get("descricao", ""),
        dados["preco"],
        dados["estoque"],
        dados.get("categoria", "geral"),
    )
    logger.info("Produto criado com ID %d", novo_id)
    return jsonify({"dados": {"id": novo_id}, "sucesso": True, "mensagem": "Produto criado"}), 201


def atualizar_produto(id):
    if not produto_model.get_por_id(id):
        raise NotFoundError("Produto não encontrado")
    dados = request.get_json(silent=True) or {}
    _validar_payload(dados)
    produto_model.atualizar(
        id,
        dados["nome"],
        dados.get("descricao", ""),
        dados["preco"],
        dados["estoque"],
        dados.get("categoria", "geral"),
    )
    return jsonify({"sucesso": True, "mensagem": "Produto atualizado"}), 200


def deletar_produto(id):
    if not produto_model.get_por_id(id):
        raise NotFoundError("Produto não encontrado")
    produto_model.deletar(id)
    logger.info("Produto %d deletado", id)
    return jsonify({"sucesso": True, "mensagem": "Produto deletado"}), 200
