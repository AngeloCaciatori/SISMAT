"""Dashboard principal."""

from datetime import date, timedelta
from flask import Blueprint, render_template, make_response, redirect, request, url_for, g
from flask_login import login_required
from sqlalchemy import func

from ..extensions import db
from ..models import Militar, Material, Cautela, RacaoOperacional, Operador
from .. import render_resp

bp = Blueprint("main", __name__)


@bp.route("/dashboard")
@login_required
def dashboard():
    total_militares = (
        db.session.query(func.count(Militar.id))
        .filter_by(excluido=False).scalar() or 0
    )
    total_itens = (
        db.session.query(func.count(Material.id))
        .filter_by(ativo=True).scalar() or 0
    )
    total_unidades = (
        db.session.query(func.coalesce(func.sum(Material.qnt_siscofis), 0))
        .filter(Material.ativo.is_(True)).scalar() or 0
    )
    cautelas_ativas = (
        db.session.query(func.count(Cautela.id))
        .filter_by(devolvida=False).scalar() or 0
    )
    cautelas_atrasadas = (
        db.session.query(func.count(Cautela.id))
        .filter(Cautela.devolvida.is_(False))
        .filter(Cautela.devolucao_prevista < date.today())
        .scalar() or 0
    )
    racao_vencendo = (
        db.session.query(func.count(RacaoOperacional.id))
        .filter(RacaoOperacional.ativo.is_(True))
        .filter(RacaoOperacional.validade <= date.today() + timedelta(days=30))
        .filter(RacaoOperacional.validade >= date.today())
        .scalar() or 0
    )
    total_operadores = (
        db.session.query(func.count(Operador.id))
        .filter_by(ativo=True).scalar() or 0
    )

    return render_resp(
        "dashboard.html",
        total_militares=total_militares,
        total_itens=total_itens,
        total_unidades=total_unidades,
        cautelas_ativas=cautelas_ativas,
        cautelas_atrasadas=cautelas_atrasadas,
        racao_vencendo=racao_vencendo,
        total_operadores=total_operadores,
    )


@bp.route("/view/alternar")
def alternar_view():
    """Alterna entre visão mobile e desktop via cookie."""
    atual = request.cookies.get("sismat_view")
    if atual not in ("mobile", "desktop"):
        atual = "mobile" if g.get("is_mobile") else "desktop"
    novo = "desktop" if atual == "mobile" else "mobile"
    resp = make_response(redirect(request.referrer or url_for("main.dashboard")))
    resp.set_cookie("sismat_view", novo, max_age=60 * 60 * 24 * 365)
    return resp


@bp.route("/mais")
@login_required
def mais():
    """Página 'Mais' da bottom-nav mobile (exclusiva mobile — sem fallback desktop)."""
    from flask import render_template
    return render_template("mobile/mais.html")
