from flask import Blueprint
import controllers.produto_controller as produto_ctrl
import controllers.usuario_controller as usuario_ctrl
import controllers.pedido_controller as pedido_ctrl
import controllers.admin_controller as admin_ctrl
from middlewares.auth import require_admin_token

bp = Blueprint("main", __name__)

# Produtos
bp.add_url_rule("/produtos",            "listar_produtos",  produto_ctrl.listar_produtos,  methods=["GET"])
bp.add_url_rule("/produtos/busca",      "buscar_produtos",  produto_ctrl.buscar_produtos,  methods=["GET"])
bp.add_url_rule("/produtos/<int:id>",   "buscar_produto",   produto_ctrl.buscar_produto,   methods=["GET"])
bp.add_url_rule("/produtos",            "criar_produto",    produto_ctrl.criar_produto,    methods=["POST"])
bp.add_url_rule("/produtos/<int:id>",   "atualizar_produto",produto_ctrl.atualizar_produto,methods=["PUT"])
bp.add_url_rule("/produtos/<int:id>",   "deletar_produto",  produto_ctrl.deletar_produto,  methods=["DELETE"])

# Usuários
bp.add_url_rule("/usuarios",            "listar_usuarios",  usuario_ctrl.listar_usuarios,  methods=["GET"])
bp.add_url_rule("/usuarios/<int:id>",   "buscar_usuario",   usuario_ctrl.buscar_usuario,   methods=["GET"])
bp.add_url_rule("/usuarios",            "criar_usuario",    usuario_ctrl.criar_usuario,    methods=["POST"])
bp.add_url_rule("/login",               "login",            usuario_ctrl.login,            methods=["POST"])

# Pedidos
bp.add_url_rule("/pedidos",                            "criar_pedido",          pedido_ctrl.criar_pedido,         methods=["POST"])
bp.add_url_rule("/pedidos",                            "listar_todos_pedidos",  pedido_ctrl.listar_todos_pedidos, methods=["GET"])
bp.add_url_rule("/pedidos/usuario/<int:usuario_id>",   "listar_pedidos_usuario",pedido_ctrl.listar_pedidos_usuario,methods=["GET"])
bp.add_url_rule("/pedidos/<int:pedido_id>/status",     "atualizar_status_pedido",pedido_ctrl.atualizar_status_pedido,methods=["PUT"])

# Relatórios (requer X-Admin-Token)
bp.add_url_rule("/relatorios/vendas", "relatorio_vendas",
                require_admin_token(pedido_ctrl.relatorio_vendas), methods=["GET"])

# Health (público)
bp.add_url_rule("/health", "health_check", admin_ctrl.health_check, methods=["GET"])

# Admin (requer X-Admin-Token; /admin/query marcado para remoção)
bp.add_url_rule("/admin/reset-db", "reset_database",
                require_admin_token(admin_ctrl.reset_database), methods=["POST"])
bp.add_url_rule("/admin/query", "executar_query",
                require_admin_token(admin_ctrl.executar_query), methods=["POST"])
