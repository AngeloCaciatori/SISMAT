"""Dashboard principal."""

from collections import Counter
from datetime import date, timedelta
from flask import Blueprint, render_template, make_response, redirect, request, url_for, g
from flask_login import login_required
from sqlalchemy import func, text

from ..extensions import db
from ..models import Militar, Material, Cautela, RacaoOperacional, Operador, BackupLog
from .. import render_resp

bp = Blueprint("main", __name__)


# ── Tabelas de conversão medida → tamanho de fardamento ──────────────────────

_ORDEM_TAMANHO = ["PP", "P", "M", "G", "GG", "XG"]
_TAMANHOS_VALIDOS = set(_ORDEM_TAMANHO)


def _safe_int(val, minv, maxv):
    """Converte string para int e valida o intervalo. Retorna None se inválido."""
    try:
        v = int(str(val).strip())
        return v if minv <= v <= maxv else None
    except (TypeError, ValueError):
        return None


def _graf(counter, ordem):
    """Retorna dict {labels, data} ordenado pela lista de referência."""
    labels = [t for t in ordem if t in counter]
    data   = [counter[t] for t in labels]
    return {"labels": labels, "data": data}


def _computar_graficos_fardamento():
    """Lê medidas do banco e retorna dicts prontos para os gráficos SVG."""
    try:
        rows = db.session.execute(text("""
            SELECT m.pe, m.cabeca, m.camisa, m.calca
            FROM   medidas m
            JOIN   militar mil ON m.militar_id = mil.id
            WHERE  mil.excluido = 0
        """)).fetchall()
    except Exception:
        rows = []

    pe_cnt      = Counter()
    camisa_cnt  = Counter()
    calca_cnt   = Counter()
    cabeca_cnt  = Counter()
    com_medidas = 0

    for pe_raw, cab_raw, camisa_raw, calca_raw in rows:
        tem = False

        pe = _safe_int(pe_raw, 30, 50)
        if pe:
            pe_cnt[str(pe)] += 1
            tem = True

        # Camisa/Gandola: já armazenado como PP/P/M/G/GG/XG
        if camisa_raw and str(camisa_raw).strip().upper() in _TAMANHOS_VALIDOS:
            camisa_cnt[str(camisa_raw).strip().upper()] += 1
            tem = True

        # Calça: já armazenado como PP/P/M/G/GG/XG
        if calca_raw and str(calca_raw).strip().upper() in _TAMANHOS_VALIDOS:
            calca_cnt[str(calca_raw).strip().upper()] += 1
            tem = True

        # Cabeça: agrupado por valor numérico real (54, 55, 56...)
        cab = _safe_int(cab_raw, 50, 70)
        if cab:
            cabeca_cnt[str(cab)] += 1
            tem = True

        if tem:
            com_medidas += 1

    # Ordenar numericamente (calçado e cabeça)
    pe_sorted     = sorted(pe_cnt.items(),     key=lambda x: int(x[0]))
    cabeca_sorted = sorted(cabeca_cnt.items(), key=lambda x: int(x[0]))

    return {
        "com_medidas": com_medidas,
        "total_rows":  len(rows),
        "calcado": {"labels": [k for k, _ in pe_sorted],
                    "data":   [v for _, v in pe_sorted]},
        "camisa":  _graf(camisa_cnt, _ORDEM_TAMANHO),
        "calca":   _graf(calca_cnt,  _ORDEM_TAMANHO),
        "cabeca":  {"labels": [k for k, _ in cabeca_sorted],
                    "data":   [v for _, v in cabeca_sorted]},
    }


# ── Rota principal ────────────────────────────────────────────────────────────

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

    # Último backup bem-sucedido (para card no dashboard)
    try:
        ultimo_backup = (
            BackupLog.query.filter_by(ok=True)
            .order_by(BackupLog.criado_em.desc()).first()
        )
    except Exception:
        ultimo_backup = None

    # Gráficos de fardamento
    graf_fardamento = _computar_graficos_fardamento()

    return render_resp(
        "dashboard.html",
        total_militares=total_militares,
        total_itens=total_itens,
        total_unidades=total_unidades,
        cautelas_ativas=cautelas_ativas,
        cautelas_atrasadas=cautelas_atrasadas,
        racao_vencendo=racao_vencendo,
        total_operadores=total_operadores,
        ultimo_backup=ultimo_backup,
        graf_fardamento=graf_fardamento,
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
