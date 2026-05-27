"""Registro centralizado de blueprints."""

from .auth_routes import bp as auth_bp
from .main import bp as main_bp
from .efetivo import bp as efetivo_bp
from .material import bp as material_bp
from .cautelas import bp as cautelas_bp
from .documentacao import bp as documentacao_bp
from .racao import bp as racao_bp
from .operadores import bp as operadores_bp


def register_blueprints(app):
    app.register_blueprint(auth_bp)
    app.register_blueprint(main_bp)
    app.register_blueprint(efetivo_bp, url_prefix="/efetivo")
    app.register_blueprint(material_bp, url_prefix="/material")
    app.register_blueprint(cautelas_bp, url_prefix="/cautelas")
    app.register_blueprint(documentacao_bp, url_prefix="/documentacao")
    app.register_blueprint(racao_bp, url_prefix="/racao")
    app.register_blueprint(operadores_bp, url_prefix="/operadores")
