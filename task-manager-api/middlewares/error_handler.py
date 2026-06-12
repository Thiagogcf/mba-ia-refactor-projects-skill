import logging
from flask import jsonify

logger = logging.getLogger(__name__)


class AppError(Exception):
    status_code = 500


class ValidationError(AppError):
    status_code = 400


class NotFoundError(AppError):
    status_code = 404


class UnauthorizedError(AppError):
    status_code = 401


class ForbiddenError(AppError):
    status_code = 403


class ConflictError(AppError):
    status_code = 409


def register_error_handlers(app):
    @app.errorhandler(AppError)
    def handle_app_error(e):
        return jsonify({'error': str(e)}), e.status_code

    @app.errorhandler(Exception)
    def handle_unexpected(e):
        logger.exception('Erro não tratado')
        return jsonify({'error': 'Erro interno do servidor'}), 500
