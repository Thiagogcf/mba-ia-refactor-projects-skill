import secrets
from functools import wraps
from flask import request
from config import settings
from middlewares.error_handler import ForbiddenError


def require_admin_token(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        expected = settings.ADMIN_TOKEN
        provided = request.headers.get("X-Admin-Token", "")
        if not expected or not secrets.compare_digest(provided, expected):
            raise ForbiddenError("Acesso negado")
        return view(*args, **kwargs)
    return wrapped
