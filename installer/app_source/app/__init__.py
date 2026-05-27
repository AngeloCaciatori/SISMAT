"""Application factory do SISMAT."""

from pathlib import Path
from flask import Flask

from config import Config
from .extensions import db, login_manager, csrf


def create_app(config_class=Config) -> Flask:
    app = Flask(__name__, instance_relative_config=False)
    app.config.from_object(config_class)

    # Garante que a pasta instance/ existe (onde fica o sismat.db)
    Path(app.config["SQLALCHEMY_DATABASE_URI"].replace("sqlite:///", "")).parent.mkdir(
        parents=True, exist_ok=True
    )

    # Inicializa extensões
    db.init_app(app)
    login_manager.init_app(app)
    csrf.init_app(app)

    # Carregador de usuário (Flask-Login)
    from .models import Operador

    @login_manager.user_loader
    def load_user(user_id):
        return db.session.get(Operador, int(user_id))

    # Registra blueprints (rotas)
    from .routes import register_blueprints

    register_blueprints(app)

    # Filtros úteis no Jinja
    from datetime import date

    @app.template_filter("data_br")
    def data_br(d):
        if not d:
            return "—"
        if hasattr(d, "strftime"):
            return d.strftime("%d/%m/%Y")
        return str(d)

    @app.template_filter("moeda")
    def moeda(v):
        if v is None:
            return "—"
        try:
            return f"R$ {float(v):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
        except (TypeError, ValueError):
            return "—"

    @app.context_processor
    def inject_globals():
        from flask import request
        # Detecta acesso local (PC servidor) vs remoto (PC da LAN).
        # Webcam (getUserMedia) só funciona em "secure context" — localhost ou HTTPS.
        try:
            host = (request.host or "").split(":")[0].lower()
        except RuntimeError:
            host = ""
        is_localhost = host in ("localhost", "127.0.0.1", "::1", "[::1]")

        return {
            "NOME_INSTITUICAO": app.config["NOME_INSTITUICAO"],
            "CIDADE_QUARTEL": app.config["CIDADE_QUARTEL"],
            "is_localhost": is_localhost,
            "host_atual": host,
        }

    # Força troca de senha quando ela é temporária (após reset).
    # Rotas de auth e static ficam liberadas para que o próprio fluxo de
    # troca de senha não seja barrado por ele mesmo.
    from flask import request, redirect, url_for
    from flask_login import current_user

    ROTAS_LIVRES = {"auth.login", "auth.logout", "auth.trocar_senha",
                    "auth.recuperar_senha", "auth.index", "static"}

    @app.before_request
    def exigir_troca_senha_temporaria():
        if not current_user.is_authenticated:
            return None
        if not getattr(current_user, "senha_temporaria", False):
            return None
        endpoint = request.endpoint or ""
        if endpoint in ROTAS_LIVRES or endpoint.startswith("static"):
            return None
        return redirect(url_for("auth.trocar_senha"))

    return app
