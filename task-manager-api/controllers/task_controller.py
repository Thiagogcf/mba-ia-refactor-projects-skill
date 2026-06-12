import logging
from datetime import datetime
from flask import request, jsonify
from sqlalchemy.orm import joinedload
from database import db
from models.task import Task, VALID_STATUSES, MIN_TITLE_LENGTH, MAX_TITLE_LENGTH, DEFAULT_PRIORITY
from models.user import User
from models.category import Category
from middlewares.error_handler import ValidationError, NotFoundError
from services.notification_service import NotificationService
from utils.helpers import utcnow

logger = logging.getLogger(__name__)
_notification_service = NotificationService()


def _validate_task_payload(data, partial=False):
    if not partial or 'title' in data:
        title = data.get('title', '')
        if not title:
            raise ValidationError('Título é obrigatório')
        if len(title.strip()) < MIN_TITLE_LENGTH:
            raise ValidationError('Título muito curto')
        if len(title.strip()) > MAX_TITLE_LENGTH:
            raise ValidationError('Título muito longo')
    if 'status' in data and data['status'] not in VALID_STATUSES:
        raise ValidationError('Status inválido')
    if 'priority' in data:
        p = data['priority']
        if not isinstance(p, int) or p < 1 or p > 5:
            raise ValidationError('Prioridade deve ser entre 1 e 5')
    if 'due_date' in data and data['due_date']:
        try:
            datetime.strptime(data['due_date'], '%Y-%m-%d')
        except ValueError:
            raise ValidationError('Formato de data inválido. Use YYYY-MM-DD')


def get_tasks():
    tasks = Task.query.options(
        joinedload(Task.user),
        joinedload(Task.category),
    ).all()
    result = []
    for t in tasks:
        data = t.to_dict(include_overdue=True)
        data['user_name'] = t.user.name if t.user else None
        data['category_name'] = t.category.name if t.category else None
        result.append(data)
    return jsonify(result), 200


def get_task(task_id):
    task = db.session.get(Task, task_id)
    if not task:
        raise NotFoundError('Task não encontrada')
    return jsonify(task.to_dict(include_overdue=True)), 200


def create_task():
    data = request.get_json(silent=True) or {}
    _validate_task_payload(data)

    user = None
    if data.get('user_id'):
        user = db.session.get(User, data['user_id'])
        if not user:
            raise NotFoundError('Usuário não encontrado')
    if data.get('category_id') and not db.session.get(Category, data['category_id']):
        raise NotFoundError('Categoria não encontrada')

    task = Task(
        title=data['title'].strip(),
        description=data.get('description', ''),
        status=data.get('status', 'pending'),
        priority=data.get('priority', DEFAULT_PRIORITY),
        user_id=data.get('user_id'),
        category_id=data.get('category_id'),
    )
    if data.get('due_date'):
        task.due_date = datetime.strptime(data['due_date'], '%Y-%m-%d')
    tags = data.get('tags')
    if tags:
        task.tags = ','.join(tags) if isinstance(tags, list) else tags

    db.session.add(task)
    db.session.commit()
    logger.info('Task criada: %s - %s', task.id, task.title)

    if user:
        _notification_service.notify_task_assigned(user, task)

    return jsonify(task.to_dict()), 201


def update_task(task_id):
    task = db.session.get(Task, task_id)
    if not task:
        raise NotFoundError('Task não encontrada')

    data = request.get_json(silent=True) or {}
    _validate_task_payload(data, partial=True)

    if 'title' in data:
        task.title = data['title'].strip()
    if 'description' in data:
        task.description = data['description']
    if 'status' in data:
        task.status = data['status']
    if 'priority' in data:
        task.priority = data['priority']
    if 'user_id' in data:
        if data['user_id'] and not db.session.get(User, data['user_id']):
            raise NotFoundError('Usuário não encontrado')
        task.user_id = data['user_id']
    if 'category_id' in data:
        if data['category_id'] and not db.session.get(Category, data['category_id']):
            raise NotFoundError('Categoria não encontrada')
        task.category_id = data['category_id']
    if 'due_date' in data:
        task.due_date = datetime.strptime(data['due_date'], '%Y-%m-%d') if data['due_date'] else None
    if 'tags' in data:
        task.tags = ','.join(data['tags']) if isinstance(data['tags'], list) else data['tags']

    task.updated_at = utcnow()
    db.session.commit()
    logger.info('Task atualizada: %s', task.id)
    return jsonify(task.to_dict()), 200


def delete_task(task_id):
    task = db.session.get(Task, task_id)
    if not task:
        raise NotFoundError('Task não encontrada')
    db.session.delete(task)
    db.session.commit()
    logger.info('Task deletada: %s', task_id)
    return jsonify({'message': 'Task deletada com sucesso'}), 200


def search_tasks():
    query_str = request.args.get('q', '')
    status = request.args.get('status', '')
    priority_str = request.args.get('priority', '')
    user_id_str = request.args.get('user_id', '')

    tasks = Task.query
    if query_str:
        tasks = tasks.filter(
            db.or_(
                Task.title.like(f'%{query_str}%'),
                Task.description.like(f'%{query_str}%'),
            )
        )
    if status:
        tasks = tasks.filter(Task.status == status)
    if priority_str:
        try:
            tasks = tasks.filter(Task.priority == int(priority_str))
        except ValueError:
            raise ValidationError('Parâmetro priority deve ser um número inteiro')
    if user_id_str:
        try:
            tasks = tasks.filter(Task.user_id == int(user_id_str))
        except ValueError:
            raise ValidationError('Parâmetro user_id deve ser um número inteiro')

    return jsonify([t.to_dict() for t in tasks.all()]), 200


def task_stats():
    now = utcnow()
    total = Task.query.count()
    pending = Task.query.filter_by(status='pending').count()
    in_progress = Task.query.filter_by(status='in_progress').count()
    done = Task.query.filter_by(status='done').count()
    cancelled = Task.query.filter_by(status='cancelled').count()
    overdue = Task.query.filter(
        Task.due_date.isnot(None),
        Task.due_date < now,
        Task.status.notin_(('done', 'cancelled')),
    ).count()

    return jsonify({
        'total': total,
        'pending': pending,
        'in_progress': in_progress,
        'done': done,
        'cancelled': cancelled,
        'overdue': overdue,
        'completion_rate': round((done / total) * 100, 2) if total > 0 else 0,
    }), 200
