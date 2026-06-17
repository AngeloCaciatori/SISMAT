"""Rotas de autenticação: login, logout e solicitação de redefinição de senha."""

from datetime import datetime
from flask import Blueprint, render_template, request, redirect, url_for, flash, g
from flask_login import login_user, logout_user, login_required, current_user

from ..extensions import db
from ..models import Operador, SolicitacaoReset
from .. import render_resp

bp = Blueprint("auth", __name__)


@bp.route("/", methods=["GET"])
def index():
    """Redireciona raiz para o dashboard ou login."""
    if current_user.is_authenticated:
        return redirect(url_for("main.dashboard"))
    return redirect(url_for("auth.login"))


@bp.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("main.dashboard"))

    if request.method == "POST":
        login_str = (request.form.get("login") or "").strip().lower()
        senha = request.form.get("senha") or ""

        operador = Operador.query.filter_by(login=login_str, ativo=True).first()
        if not operador or not operador.verificar_senha(senha):
            flash("Login ou senha inválidos.", "error")
            return render_resp("login.html", login_str=login_str)

        operador.ultimo_acesso = datetime.utcnow()
        db.session.commit()

        login_user(operador, remember=False)

        # Log no terminal do servidor
        _ip = request.headers.get("X-Forwarded-For", request.remote_addr or "?")
        _tipo = "MOBILE" if g.get("is_mobile") else "PC"
        _nivel = "ADMIN" if operador.nivel_seguranca == 1 else "operador"
        _ua = request.headers.get("User-Agent", "?")
        print(
            f"\n  LOGIN  [{_tipo}]  {operador.login} ({_nivel})"
            f"  |  IP: {_ip}"
            f"  |  {datetime.utcnow().strftime('%d/%m/%Y %H:%M:%S')}"
            f"\n  UA: {_ua}\n",
            flush=True,
        )

        flash(f"Bem-vindo, {operador.login}.", "success")

        if operador.senha_temporaria:
            flash("Sua senha e temporaria - recomendamos trocar em 'Trocar Senha'.", "warning")

        return redirect(url_for("main.dashboard"))

    return render_resp("login.html")


@bp.route("/logout")
@login_required
def logout():
    logout_user()
    flash("Sessao encerrada.", "success")
    return redirect(url_for("auth.login"))


@bp.route("/trocar-senha", methods=["GET", "POST"])
@login_required
def trocar_senha():
    """Permite ao operador trocar sua propria senha.

    Obrigatorio no 1o login (quando senha_temporaria=True).
    """
    if request.method == "POST":
        senha_atual = request.form.get("senha_atual") or ""
        nova = request.form.get("nova_senha") or ""
        confirmar = request.form.get("confirmar_senha") or ""

        if not current_user.verificar_senha(senha_atual):
            flash("Senha atual incorreta.", "error")
            return render_template("trocar_senha.html")
        if len(nova) < 6:
            flash("A nova senha deve ter ao menos 6 caracteres.", "error")
            return render_template("trocar_senha.html")
        if nova != confirmar:
            flash("Nova senha e confirmacao nao coincidem.", "error")
            return render_template("trocar_senha.html")
        if nova == senha_atual:
            flash("A nova senha precisa ser diferente da atual.", "error")
            return render_template("trocar_senha.html")

        current_user.definir_senha(nova)
        current_user.senha_temporaria = False
        db.session.commit()

        flash("Senha alterada com sucesso.", "success")
        return redirect(url_for("main.dashboard"))

    return render_template("trocar_senha.html")


@bp.route("/recuperar-senha", methods=["GET", "POST"])
def recuperar_senha():
    """O usuario registra um pedido; o admin redefine presencialmente."""
    if request.method == "POST":
        cpf = (request.form.get("cpf") or "").strip()
        nome = (request.form.get("nome") or "").strip()
        motivo = (request.form.get("motivo") or "").strip()

        if not cpf:
            flash("Informe o CPF.", "error")
            return render_template("recuperar.html")

        sol = SolicitacaoReset(cpf=cpf, nome=nome, motivo=motivo)
        db.session.add(sol)
        db.session.commit()

        flash(
            "Solicitacao registrada. Procure o administrador presencialmente "
            "para receber a nova senha.",
            "success",
        )
        return redirect(url_for("auth.login"))

    return render_template("recuperar.html")
