"""Rotas de Ração Operacional (lotes, validades)."""

from flask import Blueprint, render_template
from flask_login import login_required

bp = Blueprint("racao", __name__)


@bp.route("/")
@login_required
def lista():
    return render_template("em_construcao.html", secao="Ração Operacional")
