"""Application factory do SISMAT."""

from pathlib import Path
from flask import Flask, g, render_template as _render_template

from config import Config
from .extensions import db, login_manager, csrf


# ---------------------------------------------------------------------------
# Helper de render: serve template mobile se disponível, senão desktop.
# Importar nas blueprints que precisam de fallback mobile.
# ---------------------------------------------------------------------------
def render_resp(tpl: str, **ctx):
    """Sempre serve o template desktop.
    Detecção mobile mantida apenas para o log do servidor.
    Para reativar templates mobile: descomente o bloco abaixo.
    """
    # if g.get("is_mobile"):
    #     return _render_template([f"mobile/{tpl}", tpl], **ctx)
    return _render_template(tpl, **ctx)


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

    # Cria tabelas novas que ainda não existem (seguro: não altera existentes)
    with app.app_context():
        db.create_all()

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

    # -----------------------------------------------------------------------
    # Detecção de mobile via User-Agent + cookie de override
    # -----------------------------------------------------------------------
    try:
        from user_agents import parse as ua_parse
    except ImportError:
        ua_parse = None

    @app.before_request
    def detectar_mobile():
        from flask import request as _req
        # Detecta se o UA é realmente mobile/tablet
        if ua_parse:
            ua = ua_parse(_req.headers.get("User-Agent", ""))
            ua_is_mobile = ua.is_mobile or ua.is_tablet
        else:
            ua_is_mobile = False

        # Cookie de override só vale para dispositivos realmente mobile.
        # No PC (ua_is_mobile=False), sempre serve desktop — ignora cookie.
        g.ua_is_mobile = ua_is_mobile  # sempre baseado no UA real, ignora cookie
        if ua_is_mobile:
            override = _req.cookies.get("sismat_view")
            if override == "desktop":
                g.is_mobile = False
            else:
                g.is_mobile = True
        else:
            g.is_mobile = False

    @app.context_processor
    def injetar_mobile():
        return {
            "is_mobile": g.get("is_mobile", False),
            "ua_is_mobile": g.get("ua_is_mobile", False),
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
