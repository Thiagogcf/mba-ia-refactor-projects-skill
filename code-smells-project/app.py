import logging
from flask import Flask, jsonify
from flask_cors import CORS
from config import settings
from database import close_db, init_db
from views.routes import bp
from middlewares.error_handler import register_error_handlers

logging.basicConfig(
    level=logging.DEBUG if settings.DEBUG else logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)


def create_app():
    app = Flask(__name__)
    app.config["SECRET_KEY"] = settings.SECRET_KEY
    app.config["DEBUG"] = settings.DEBUG

    CORS(app, origins=settings.CORS_ORIGINS)
    app.teardown_appcontext(close_db)
    app.register_blueprint(bp)
    register_error_handlers(app)

    @app.route("/")
    def index():
        return jsonify({
            "mensagem": "Bem-vindo à API da Loja",
            "versao": "1.0.0",
            "endpoints": {
                "produtos":   "/produtos",
                "usuarios":   "/usuarios",
                "pedidos":    "/pedidos",
                "login":      "/login",
                "relatorios": "/relatorios/vendas",
                "health":     "/health",
            },
        })

    return app


if __name__ == "__main__":
    _logger = logging.getLogger(__name__)
    app = create_app()
    init_db(app)
    _logger.info("=" * 50)
    _logger.info("SERVIDOR INICIADO")
    _logger.info("Rodando em http://%s:%s", settings.HOST, settings.PORT)
    _logger.info("=" * 50)
    app.run(host=settings.HOST, port=settings.PORT, debug=settings.DEBUG)
