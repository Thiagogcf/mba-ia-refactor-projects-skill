import logging
from flask import request, jsonify
from database import db
from models.category import Category
from models.task import Task
from middlewares.error_handler import ValidationError, NotFoundError

logger = logging.getLogger(__name__)


def get_categories():
    categories = Category.query.all()
    result = []
    for c in categories:
        data = c.to_dict()
        data['task_count'] = Task.query.filter_by(category_id=c.id).count()
        result.append(data)
    return jsonify(result), 200


def create_category():
    data = request.get_json(silent=True) or {}
    if not data.get('name'):
        raise ValidationError('Nome é obrigatório')

    category = Category(
        name=data['name'],
        description=data.get('description', ''),
        color=data.get('color', '#000000'),
    )
    db.session.add(category)
    db.session.commit()
    return jsonify(category.to_dict()), 201


def update_category(cat_id):
    cat = db.session.get(Category, cat_id)
    if not cat:
        raise NotFoundError('Categoria não encontrada')

    data = request.get_json(silent=True) or {}
    if 'name' in data:
        cat.name = data['name']
    if 'description' in data:
        cat.description = data['description']
    if 'color' in data:
        cat.color = data['color']

    db.session.commit()
    return jsonify(cat.to_dict()), 200


def delete_category(cat_id):
    cat = db.session.get(Category, cat_id)
    if not cat:
        raise NotFoundError('Categoria não encontrada')

    Task.query.filter_by(category_id=cat_id).update({'category_id': None})
    db.session.delete(cat)
    db.session.commit()
    return jsonify({'message': 'Categoria deletada'}), 200
