import logging
import re
from flask import request, jsonify
import models.usuario_model as usuario_model
from middlewares.error_handler import ValidationError, NotFoundError, ConflictError

logger = logging.getLogger(__name__)

_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def listar_usuarios():
    usuarios = usuario_model.get_todos()
    return jsonify({"dados": usuarios, "sucesso": True}), 200


def buscar_usuario(id):
    usuario = usuario_model.get_por_id(id)
    if not usuario:
        raise NotFoundError("Usuário não encontrado")
    return jsonify({"dados": usuario, "sucesso": True}), 200


def criar_usuario():
    dados = request.get_json(silent=True) or {}
    nome  = dados.get("nome", "").strip()
    email = dados.get("email", "").strip()
    senha = dados.get("senha", "")

    if not nome or not email or not senha:
        raise ValidationError("Nome, email e senha são obrigatórios")
    if not _EMAIL_RE.match(email):
        raise ValidationError("Formato de email inválido")
    if usuario_model.email_existe(email):
        raise ConflictError("Email já cadastrado")

    novo_id = usuario_model.criar(nome, email, senha)
    logger.info("Usuário criado: %s", email)
    return jsonify({"dados": {"id": novo_id}, "sucesso": True}), 201


def login():
    dados = request.get_json(silent=True) or {}
    email = dados.get("email", "")
    senha = dados.get("senha", "")

    if not email or not senha:
        raise ValidationError("Email e senha são obrigatórios")

    usuario = usuario_model.autenticar(email, senha)
    if usuario:
        logger.info("Login bem-sucedido: %s", email)
        return jsonify({"dados": usuario, "sucesso": True, "mensagem": "Login OK"}), 200

    logger.warning("Login falhou: %s", email)
    return jsonify({"erro": "Email ou senha inválidos", "sucesso": False}), 401
