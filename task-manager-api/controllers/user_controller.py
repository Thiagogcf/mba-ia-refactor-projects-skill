import logging
from flask import request, jsonify
from database import db
from models.user import User, VALID_ROLES, MIN_PASSWORD_LENGTH
from models.task import Task
from middlewares.error_handler import (
    ValidationError, NotFoundError, UnauthorizedError, ForbiddenError, ConflictError
)
from utils.helpers import validate_email

logger = logging.getLogger(__name__)


def _validate_user_payload(data, partial=False):
    if not partial or 'name' in data:
        if not data.get('name'):
            raise ValidationError('Nome é obrigatório')
    if not partial or 'email' in data:
        email = data.get('email', '')
        if not email:
            raise ValidationError('Email é obrigatório')
        if not validate_email(email):
            raise ValidationError('Email inválido')
    if not partial or 'password' in data:
        pwd = data.get('password', '')
        if not pwd:
            raise ValidationError('Senha é obrigatória')
        if len(pwd) < MIN_PASSWORD_LENGTH:
            raise ValidationError('Senha deve ter no mínimo 4 caracteres')
    if 'role' in data and data['role'] not in VALID_ROLES:
        raise ValidationError('Role inválido')


def get_users():
    users = User.query.all()
    result = [{**u.to_dict(), 'task_count': len(u.tasks)} for u in users]
    return jsonify(result), 200


def get_user(user_id):
    user = db.session.get(User, user_id)
    if not user:
        raise NotFoundError('Usuário não encontrado')
    data = user.to_dict()
    data['tasks'] = [t.to_dict() for t in Task.query.filter_by(user_id=user_id).all()]
    return jsonify(data), 200


def create_user():
    data = request.get_json(silent=True) or {}
    _validate_user_payload(data)

    if User.query.filter_by(email=data['email']).first():
        raise ConflictError('Email já cadastrado')

    user = User(name=data['name'], email=data['email'], role=data.get('role', 'user'))
    user.set_password(data['password'])

    db.session.add(user)
    db.session.commit()
    logger.info('Usuário criado: %s - %s', user.id, user.name)
    return jsonify(user.to_dict()), 201


def update_user(user_id):
    user = db.session.get(User, user_id)
    if not user:
        raise NotFoundError('Usuário não encontrado')

    data = request.get_json(silent=True) or {}
    _validate_user_payload(data, partial=True)

    if 'name' in data:
        user.name = data['name']
    if 'email' in data:
        existing = User.query.filter_by(email=data['email']).first()
        if existing and existing.id != user_id:
            raise ConflictError('Email já cadastrado')
        user.email = data['email']
    if 'password' in data:
        user.set_password(data['password'])
    if 'role' in data:
        user.role = data['role']
    if 'active' in data:
        user.active = data['active']

    db.session.commit()
    return jsonify(user.to_dict()), 200


def delete_user(user_id):
    user = db.session.get(User, user_id)
    if not user:
        raise NotFoundError('Usuário não encontrado')

    Task.query.filter_by(user_id=user_id).delete()
    db.session.delete(user)
    db.session.commit()
    logger.info('Usuário deletado: %s', user_id)
    return jsonify({'message': 'Usuário deletado com sucesso'}), 200


def get_user_tasks(user_id):
    user = db.session.get(User, user_id)
    if not user:
        raise NotFoundError('Usuário não encontrado')
    tasks = Task.query.filter_by(user_id=user_id).all()
    return jsonify([t.to_dict(include_overdue=True) for t in tasks]), 200


def login():
    data = request.get_json(silent=True) or {}
    email = data.get('email')
    password = data.get('password')

    if not email or not password:
        raise ValidationError('Email e senha são obrigatórios')

    user = User.query.filter_by(email=email).first()
    if not user or not user.check_password(password):
        raise UnauthorizedError('Credenciais inválidas')

    if not user.active:
        raise ForbiddenError('Usuário inativo')

    return jsonify({
        'message': 'Login realizado com sucesso',
        'user': user.to_dict(),
    }), 200
