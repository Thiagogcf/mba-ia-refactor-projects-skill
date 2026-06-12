import os

SECRET_KEY = os.environ.get("SECRET_KEY", "dev-only-change-me")
DEBUG = os.environ.get("FLASK_DEBUG", "0") == "1"
HOST = os.environ.get("HOST", "127.0.0.1")
PORT = int(os.environ.get("PORT", "5000"))
DATABASE_PATH = os.environ.get("DATABASE_PATH", "loja.db")
CORS_ORIGINS = os.environ.get("CORS_ORIGINS", "*")
ADMIN_TOKEN = os.environ.get("ADMIN_TOKEN", "")
