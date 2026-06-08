"""Rotas de Cautelas (lista, nova, devolver, ficha FIDU por cautela)."""

from datetime import date, datetime, timedelta
from flask import (
    Blueprint, render_template, request, redirect, url_for, flash, abort
)
from flask_login import login_required, current_user
from sqlalchemy import or_, func, extract

from ..extensions import db
from .. import render_resp
from ..models import (
    Cautela, ItemCautelado, Militar, Material, Operador, LogAuditoria,
    OM_INTERNA, OM_EXTERNA,
)
from ..utils import registrar_log

bp = Blueprint("cautelas", __name__)


def _proximo_numero():
    """Gera próximo número da cautela no formato '0001/2026'."""
    ano = date.today().year
    ultimo = (
        db.session.query(Cautela.numero)
        .filter(Cautela.numero.like(f"%/{ano}"))
        .filter(~Cautela.numero.like("L-%"))  # ignora legadas
        .order_by(Cautela.numero.desc())
        .first()
    )
    if ultimo:
        try:
            seq = int(ultimo[0].split("/")[0])
            return f"{seq + 1:04d}/{ano}"
        except (ValueError, IndexError):
            pass
    return f"0001/{ano}"


@bp.route("/")
@login_required
def lista():
    busca = (request.args.get("q") or "").strip()
    status = request.args.get("status", "ativas")  # ativas, atrasadas, devolvidas, todas
    militar_id = request.args.get("militar_id", "")

    query = Cautela.query

    if status == "ativas":
        query = query.filter(Cautela.devolvida.is_(False))
    elif status == "atrasadas":
        query = query.filter(Cautela.devolvida.is_(False))
        query = query.filter(Cautela.devolucao_prevista < date.today())
    elif status == "devolvidas":
        query = query.filter(Cautela.devolvida.is_(True))

    if busca:
        like = f"%{busca}%"
        query = (
            query.outerjoin(Militar, Cautela.militar_id == Militar.id)
            .filter(or_(
                Cautela.numero.ilike(like),
                Militar.nome_guerra.ilike(like),
                Militar.cpf.ilike(like),
                Cautela.recebedor_nome_guerra.ilike(like),
                Cautela.recebedor_cpf.ilike(like),
                Cautela.om_externa_nome.ilike(like),
            ))
        )

    if militar_id:
        try:
            query = query.filter(Cautela.militar_id == int(militar_id))
        except ValueError:
            pass

    cautelas = query.order_by(Cautela.data_cautela.desc(), Cautela.id.desc()).limit(200).all()

    # Stats
    total_ativas = Cautela.query.filter_by(devolvida=False).count()
    total_atrasadas = (
        Cautela.query.filter(Cautela.devolvida.is_(False))
        .filter(Cautela.devolucao_prevista < date.today())
        .count()
    )
    total_devolvidas_30d = (
        Cautela.query.filter(Cautela.devolvida.is_(True))
        .filter(Cautela.devolvida_em >= date.today() - timedelta(days=30))
        .count()
    )
    total_geral = Cautela.query.count()

    from datetime import date as _date
    return render_resp(
        "cautelas/lista.html",
        cautelas=cautelas,
        total_ativas=total_ativas,
        total_atrasadas=total_atrasadas,
        total_devolvidas_30d=total_devolvidas_30d,
        total_geral=total_geral,
        busca=busca,
        status=status,
        militar_id=militar_id,
        hoje=_date.today(),
    )


@bp.route("/<int:cautela_id>")
@login_required
def detalhe(cautela_id):
    cautela = db.session.get(Cautela, cautela_id) or abort(404)
    from datetime import date as _date

    # Quem fez a devolução (se houver entrada no log)
    log_devol = (
        LogAuditoria.query
        .filter_by(acao="DEVOLUCAO_CAUTELA", referencia_id=cautela_id)
        .order_by(LogAuditoria.id.desc()).first()
    )
    devolvido_por = log_devol.operador_label if log_devol else None

    from ..models import AssinaturaAplicada
    assinaturas = (
        AssinaturaAplicada.query
        .filter_by(cautela_id=cautela_id)
        .order_by(AssinaturaAplicada.id)
        .all()
    )

    return render_resp(
        "cautelas/detalhe.html",
        cautela=cautela,
        hoje=_date.today(),
        devolvido_por=devolvido_por,
        assinaturas=assinaturas,
    )


@bp.route("/<int:cautela_id>/imprimir")
@login_required
def imprimir(cautela_id):
    """Ficha FIDU específica desta cautela."""
    cautela = db.session.get(Cautela, cautela_id) or abort(404)

    # Agrupa itens por categoria
    grupos = {}
    for item in cautela.itens:
        if not item.material:
            continue
        tipo = (item.material.tipo or "OUTROS").upper()
        grupos.setdefault(tipo, []).append({
            "qtd": item.quantidade,
            "nomenclatura": item.material.nomenclatura,
            "ficha_siscofis": item.material.ficha_siscofis,
            "obs": item.obs or "",
        })

    for tipo in grupos:
        grupos[tipo].sort(key=lambda x: x["nomenclatura"])

    ordem = ["EQUIPAMENTO", "FARDAMENTO", "MATERIAL", "OUTROS"]
    grupos_ordenados = [(t, grupos[t]) for t in ordem if t in grupos]
    extras = [t for t in grupos if t not in ordem]
    grupos_ordenados.extend((t, grupos[t]) for t in extras)

    from ..models import AssinaturaAplicada
    assinaturas_imp = (
        AssinaturaAplicada.query
        .filter_by(cautela_id=cautela_id)
        .order_by(AssinaturaAplicada.id)
        .all()
    )

    return render_template(
        "cautelas/imprimir_ficha.html",
        cautela=cautela,
        grupos=grupos_ordenados,
        assinaturas=assinaturas_imp,
    )


@bp.route("/nova", methods=["GET", "POST"])
@login_required
def nova():
    if current_user.is_admin:
        flash("O administrador não realiza cautelas. Utilize um operador.", "error")
        return redirect(url_for("cautelas.lista"))
    if request.method == "POST":
        return _processar_nova()

    militares = (
        Militar.query.filter_by(excluido=False)
        .order_by(Militar.nome_guerra).all()
    )
    materiais = (
        Material.query.filter_by(ativo=True)
        .order_by(Material.nomenclatura).all()
    )

    from flask import session as _sess
    from ..utils.assinatura import janela_aberta as _janela_aberta
    return render_resp(
        "cautelas/nova.html",
        militares=militares,
        materiais=materiais,
        numero_proposto=_proximo_numero(),
        hoje=date.today(),
        hoje_str=date.today().isoformat(),
        devolucao_padrao=date.today() + timedelta(days=7),
        janela_aberta_flag=_janela_aberta(_sess),
    )


def _processar_nova():
    om_tipo = (request.form.get("om_tipo") or OM_INTERNA).strip()

    # Cria cautela
    cautela = Cautela(
        numero=_proximo_numero(),
        operador_id=current_user.id,
        om_tipo=om_tipo,
        finalidade=(request.form.get("finalidade") or "").strip() or None,
        obs_geral=(request.form.get("obs_geral") or "").strip() or None,
    )

    # Data da cautela
    data_str = request.form.get("data_cautela") or ""
    try:
        cautela.data_cautela = datetime.strptime(data_str, "%Y-%m-%d").date()
    except ValueError:
        cautela.data_cautela = date.today()

    # Devolução prevista (opcional)
    devol_str = request.form.get("devolucao_prevista") or ""
    if devol_str:
        try:
            cautela.devolucao_prevista = datetime.strptime(devol_str, "%Y-%m-%d").date()
        except ValueError:
            pass

    # Recebedor
    if om_tipo == OM_INTERNA:
        militar_id = request.form.get("militar_id")
        if not militar_id:
            flash("Selecione o militar recebedor.", "error")
            return redirect(url_for("cautelas.nova"))
        try:
            militar = db.session.get(Militar, int(militar_id))
        except ValueError:
            militar = None
        if not militar or militar.excluido:
            flash("Militar inválido ou excluído.", "error")
            return redirect(url_for("cautelas.nova"))
        cautela.militar_id = militar.id
    else:
        # Externo: dados manuais
        nome_g = (request.form.get("recebedor_nome_guerra") or "").strip()
        cpf = (request.form.get("recebedor_cpf") or "").strip()
        if not nome_g or not cpf:
            flash("Para OM externa, informe pelo menos nome de guerra e CPF.", "error")
            return redirect(url_for("cautelas.nova"))
        cautela.om_externa_nome = (request.form.get("om_externa_nome") or "").strip() or None
        cautela.recebedor_grad = (request.form.get("recebedor_grad") or "").strip() or None
        cautela.recebedor_nome_guerra = nome_g
        cautela.recebedor_nome_completo = (
            request.form.get("recebedor_nome_completo") or "").strip() or None
        cautela.recebedor_cpf = cpf

    # Itens — vêm como arrays paralelos: material_id[], quantidade[], obs[]
    material_ids = request.form.getlist("material_id[]")
    quantidades = request.form.getlist("quantidade[]")
    obs_itens = request.form.getlist("obs_item[]")

    if not material_ids:
        flash("Adicione pelo menos um item à cautela.", "error")
        return redirect(url_for("cautelas.nova"))

    db.session.add(cautela)
    db.session.flush()  # garante cautela.id

    itens_criados = 0
    for i, mid in enumerate(material_ids):
        if not mid:
            continue
        try:
            mid_int = int(mid)
            qtd = int(quantidades[i]) if i < len(quantidades) else 1
        except (ValueError, IndexError):
            continue
        if qtd <= 0:
            continue

        material = db.session.get(Material, mid_int)
        if not material:
            continue

        # Verifica disponibilidade
        if qtd > material.disponivel:
            flash(
                f"Material '{material.nomenclatura}' tem só {material.disponivel} "
                f"disponível — você pediu {qtd}.",
                "error",
            )
            db.session.rollback()
            return redirect(url_for("cautelas.nova"))

        item = ItemCautelado(
            cautela_id=cautela.id,
            material_id=material.id,
            quantidade=qtd,
            obs=(obs_itens[i] if i < len(obs_itens) else "").strip() or None,
        )
        db.session.add(item)
        itens_criados += 1

    if itens_criados == 0:
        db.session.rollback()
        flash("Nenhum item válido foi informado.", "error")
        return redirect(url_for("cautelas.nova"))

    db.session.commit()

    # Auto-aplica assinatura do operador se janela de confiança estiver aberta
    if not current_user.is_admin and current_user.assinatura_base64:
        from flask import session as _session
        from ..utils.assinatura import janela_aberta, renovar_janela, ip_externo
        from ..models import AssinaturaAplicada
        if janela_aberta(_session):
            _ass = AssinaturaAplicada(
                tipo_documento="cautela_recebimento",
                cautela_id=cautela.id,
                papel="operador",
                operador_id=current_user.id,
                imagem_base64=current_user.assinatura_base64,
                ip_origem=ip_externo(request),
            )
            db.session.add(_ass)
            db.session.commit()
            renovar_janela(_session)

    # Nome do recebedor para o log
    if cautela.militar:
        recebedor = f"{cautela.militar.graduacao or ''} {cautela.militar.nome_guerra or ''}".strip()
    else:
        recebedor = f"{cautela.recebedor_grad or ''} {cautela.recebedor_nome_guerra or ''}".strip()
    registrar_log(
        "NOVA_CAUTELA",
        f"Cautela {cautela.numero} — {itens_criados} item(ns) — recebedor: {recebedor or '?'}",
        referencia_id=cautela.id,
    )

    flash(
        f"Cautela {cautela.numero} criada com {itens_criados} item(ns).",
        "success",
    )
    return redirect(url_for("cautelas.detalhe", cautela_id=cautela.id))


@bp.route("/<int:cautela_id>/devolver", methods=["POST"])
@login_required
def devolver(cautela_id):
    if current_user.is_admin:
        flash("O administrador não realiza devoluções. Utilize um operador.", "error")
        return redirect(url_for("cautelas.detalhe", cautela_id=cautela_id))

    cautela = db.session.get(Cautela, cautela_id) or abort(404)

    if cautela.devolvida:
        flash("Esta cautela já foi devolvida.", "warning")
        return redirect(url_for("cautelas.detalhe", cautela_id=cautela.id))

    cautela.devolvida = True
    cautela.devolvida_em = date.today()
    db.session.commit()
    registrar_log("DEVOLUCAO_CAUTELA", f"Cautela {cautela.numero}", referencia_id=cautela.id)
    flash(f"Cautela {cautela.numero} devolvida.", "success")
    return redirect(url_for("cautelas.detalhe", cautela_id=cautela.id))


@bp.route("/<int:cautela_id>/reabrir", methods=["POST"])
@login_required
def reabrir(cautela_id):
    if not current_user.is_admin:
        abort(403)
    """Desfaz a devolução (caso de erro)."""
    cautela = db.session.get(Cautela, cautela_id) or abort(404)
    if not cautela.devolvida:
        flash("Cautela já está ativa.", "warning")
        return redirect(url_for("cautelas.detalhe", cautela_id=cautela.id))

    cautela.devolvida = False
    cautela.devolvida_em = None
    db.session.commit()
    flash(f"Cautela {cautela.numero} reaberta.", "success")
    return redirect(url_for("cautelas.detalhe", cautela_id=cautela.id))


@bp.route("/<int:cautela_id>/cancelar", methods=["POST"])
@login_required
def cancelar(cautela_id):
    """Apaga uma cautela criada por engano (só admin, e só se não devolvida)."""
    cautela = db.session.get(Cautela, cautela_id) or abort(404)
    if not current_user.is_admin:
        abort(403)
    if cautela.devolvida:
        flash("Não cancele uma cautela já devolvida — preserva o histórico.", "error")
        return redirect(url_for("cautelas.detalhe", cautela_id=cautela.id))

    numero = cautela.numero
    db.session.delete(cautela)
    db.session.commit()
    flash(f"Cautela {numero} cancelada (apagada).", "success")
    return redirect(url_for("cautelas.lista"))
