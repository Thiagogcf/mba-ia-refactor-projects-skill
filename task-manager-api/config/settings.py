import os
from dotenv import load_dotenv

load_dotenv()

SECRET_KEY = os.environ.get('SECRET_KEY', 'dev-only-change-me')
DEBUG = os.environ.get('FLASK_DEBUG', '0') == '1'
HOST = os.environ.get('HOST', '127.0.0.1')
PORT = int(os.environ.get('PORT', '5000'))
DATABASE_URI = os.environ.get('DATABASE_URI', 'sqlite:///tasks.db')
CORS_ORIGINS = os.environ.get('CORS_ORIGINS', '*')
ADMIN_TOKEN = os.environ.get('ADMIN_TOKEN', '')

SMTP_HOST = os.environ.get('SMTP_HOST', 'smtp.gmail.com')
SMTP_PORT = int(os.environ.get('SMTP_PORT', '587'))
SMTP_USER = os.environ.get('SMTP_USER', '')
SMTP_PASSWORD = os.environ.get('SMTP_PASSWORD', '')
