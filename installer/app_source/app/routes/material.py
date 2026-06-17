"""Rotas de Material (lista, cadastro, edição, ficha de prateleira, conferência)."""

from collections import defaultdict
from flask import (
    Blueprint, render_template, request, redirect, url_for, flash, abort
)
from flask_login import login_required, current_user
from sqlalchemy import func, or_
from decimal import Decimal, InvalidOperation

from ..extensions import db
from ..auth import admin_required
from ..models import Material, ItemCautelado, Cautela, LogAuditoria, TIPOS_MATERIAL, ESTADOS_CONSERVACAO
from ..utils import registrar_log


def _log_operadores_mat(mat_id: int):
    criado = (
        LogAuditoria.query
        .filter_by(acao="CADASTRO_MATERIAL", referencia_id=mat_id)
        .order_by(LogAuditoria.id.asc()).first()
    )
    editado = (
        LogAuditoria.query
        .filter_by(acao="EDICAO_MATERIAL", referencia_id=mat_id)
        .order_by(LogAuditoria.id.desc()).first()
    )
    return (
        criado.operador_label if criado else None,
        editado.operador_label if editado else None,
    )

bp = Blueprint("material", __name__)


def _parse_decimal(v):
    if not v:
        return None
    try:
        return Decimal(str(v).replace(",", "."))
    except (InvalidOperation, ValueError):
        return None


def _calcular_cautelado(material_ids):
    """Para cada material_id, retorna a quantidade total cautelada (não devolvida)."""
    if not material_ids:
        return {}
    rows = (
        db.session.query(
            ItemCautelado.material_id,
            func.coalesce(func.sum(ItemCautelado.quantidade), 0)
        )
        .join(Cautela, Cautela.id == ItemCautelado.cautela_id)
        .filter(Cautela.devolvida.is_(False))
        .filter(ItemCautelado.material_id.in_(material_ids))
        .group_by(ItemCautelado.material_id)
        .all()
    )
    return {mat_id: int(qtd) for mat_id, qtd in rows}


def _valores_distintos():
    """Lê valores distintos de tipo/dependência diretamente do banco.

    Garante que filtros mostrem TODAS as opções que existem (mesmo as que
    não estavam no enum padrão como 'Reserva 4', 'PO', etc.).
    """
    tipos_db = [
        r[0] for r in db.session.query(Material.tipo)
        .filter(Material.ativo.is_(True))
        .filter(Material.tipo.isnot(None))
        .filter(Material.tipo != "")
        .distinct().all() if r[0]
    ]
    deps_db = [
        r[0] for r in db.session.query(Material.dependencia)
        .filter(Material.ativo.is_(True))
        .filter(Material.dependencia.isnot(None))
        .filter(Material.dependencia != "")
        .distinct().all() if r[0]
    ]
    # Mantém ordem alfabética; sobe RESERVA 1, RESERVA 2 ao topo se existirem
    def chave_dep(d):
        if d.upper().startswith("RESERVA"):
            return (0, d.upper())
        return (1, d.upper())
    return sorted(set(tipos_db)), sorted(set(deps_db), key=chave_dep)


def _ids_da_query(args):
    """Lê 'ids' (lista CSV) do query string, retorna lista de int."""
    ids_str = (args.get("ids") or "").strip()
    if not ids_str:
        return []
    out = []
    for x in ids_str.split(","):
        x = x.strip()
        if x.isdigit():
            out.append(int(x))
    return out


@bp.route("/")
@login_required
def lista():
    busca = (request.args.get("q") or "").strip()
    tipo = request.args.get("tipo") or ""
    dependencia = request.args.get("dependencia") or ""

    query = Material.query.filter_by(ativo=True)

    if busca:
        like = f"%{busca}%"
        query = query.filter(or_(
            Material.nomenclatura.ilike(like),
            Material.ficha_siscofis.ilike(like),
            Material.prateleira.ilike(like),
        ))
    if tipo:
        query = query.filter(Material.tipo == tipo)
    if dependencia == "sem":
        query = query.filter(or_(Material.dependencia.is_(None), Material.dependencia == ""))
    elif dependencia:
        query = query.filter(Material.dependencia == dependencia)

    materiais = query.order_by(Material.nomenclatura).all()

    ids = [m.id for m in materiais]
    cautelados = _calcular_cautelado(ids)

    total_itens = Material.query.filter_by(ativo=True).count()
    total_unidades = (
        db.session.query(func.coalesce(func.sum(Material.qnt_siscofis), 0))
        .filter(Material.ativo.is_(True)).scalar() or 0
    )
    total_cautelado = (
        db.session.query(func.coalesce(func.sum(ItemCautelado.quantidade), 0))
        .join(Cautela).filter(Cautela.devolvida.is_(False)).scalar() or 0
    )
    total_disponivel = max(0, total_unidades - total_cautelado)

    tipos_disp, deps_disp = _valores_distintos()

    return render_template(
        "material/lista.html",
        materiais=materiais,
        cautelados=cautelados,
        total_itens=total_itens,
        total_unidades=total_unidades,
        total_cautelado=total_cautelado,
        total_disponivel=total_disponivel,
        busca=busca,
        tipo=tipo,
        dependencia=dependencia,
        tipos_disponiveis=tipos_disp,
        deps_disponiveis=deps_disp,
    )


@bp.route("/prateleira")
@login_required
def prateleira():
    """Lista materiais (1 ficha por item) com checkbox para impressão em lote."""
    prat_filtro = (request.args.get("p") or "").strip()
    tipo = (request.args.get("tipo") or "").strip()

    query = Material.query.filter_by(ativo=True)
    if prat_filtro:
        query = query.filter(Material.prateleira == prat_filtro)
    if tipo:
        query = query.filter(Material.tipo == tipo)

    materiais = query.order_by(Material.prateleira, Material.nomenclatura).all()

    todas = (
        db.session.query(Material.prateleira)
        .filter(Material.ativo.is_(True))
        .filter(Material.prateleira.isnot(None))
        .filter(Material.prateleira != "")
        .filter(Material.prateleira != "0")
        .distinct().all()
    )
    def chave(p):
        try:
            return (0, int(p))
        except (ValueError, TypeError):
            return (1, str(p or ""))
    todas_prateleiras = sorted({p[0] for p in todas if p[0]}, key=chave)

    tipos_disp, _ = _valores_distintos()

    return render_template(
        "material/prateleira.html",
        materiais=materiais,
        todas_prateleiras=todas_prateleiras,
        tipos_disponiveis=tipos_disp,
        prat_filtro=prat_filtro,
        tipo=tipo,
    )


@bp.route("/prateleira/imprimir")
@login_required
def imprimir_prateleira():
    """Página standalone (sem topbar) para impressão de fichas selecionadas."""
    ids = _ids_da_query(request.args)
    if not ids:
        flash("Nenhuma ficha selecionada para impressão.", "warning")
        return redirect(url_for("material.prateleira"))

    materiais = (
        Material.query.filter(Material.id.in_(ids))
        .filter_by(ativo=True)
        .order_by(Material.prateleira, Material.nomenclatura).all()
    )
    return render_template("material/imprimir_prateleira.html", materiais=materiais)


@bp.route("/conferencia")
@login_required
def conferencia():
    """Lista de Conferência impressa (CONTROLE DE MATERIAL).

    Se receber ?ids=1,2,3 imprime só esses; senão imprime todos os filtrados.
    Aceita os mesmos filtros da lista para conveniência.
    """
    ids = _ids_da_query(request.args)
    busca = (request.args.get("q") or "").strip()
    tipo = (request.args.get("tipo") or "").strip()
    dependencia = (request.args.get("dependencia") or "").strip()

    query = Material.query.filter_by(ativo=True)

    if ids:
        query = query.filter(Material.id.in_(ids))
    else:
        if busca:
            like = f"%{busca}%"
            query = query.filter(or_(
                Material.nomenclatura.ilike(like),
                Material.ficha_siscofis.ilike(like),
                Material.prateleira.ilike(like),
            ))
        if tipo:
            query = query.filter(Material.tipo == tipo)
        if dependencia == "sem":
            query = query.filter(or_(Material.dependencia.is_(None), Material.dependencia == ""))
        elif dependencia:
            query = query.filter(Material.dependencia == dependencia)

    materiais = query.order_by(Material.tipo, Material.nomenclatura).all()
    return render_template(
        "material/conferencia.html",
        materiais=materiais,
        operador=current_user.login,
        filtros={"busca": busca, "tipo": tipo, "dependencia": dependencia},
    )



@bp.route("/onde-estao")
@login_required
def onde_estao():
    """Relatório: onde estão os materiais selecionados (quem está com cada item cautelado)."""
    ids = _ids_da_query(request.args)
    if not ids:
        flash("Nenhum material selecionado.", "warning")
        return redirect(url_for("material.lista"))

    from ..models import ItemCautelado, Cautela
    from sqlalchemy import and_

    materiais = (
        Material.query
        .filter(Material.id.in_(ids), Material.ativo == True)
        .order_by(Material.tipo, Material.nomenclatura)
        .all()
    )

    # Para cada material, buscar itens em cautelas ativas (não devolvidas)
    dados = []
    for mat in materiais:
        itens_ativos = (
            ItemCautelado.query
            .join(Cautela)
            .filter(
                ItemCautelado.material_id == mat.id,
                Cautela.devolvida == False,
            )
            .order_by(Cautela.data_cautela)
            .all()
        )
        dados.append({
            "material": mat,
            "itens": itens_ativos,
            "total_cautelado": sum(i.quantidade for i in itens_ativos),
        })

    from datetime import datetime as _dt
    return render_template(
        "material/onde_estao.html",
        dados=dados,
        operador=current_user.login,
        now=_dt.now(),
    )

@bp.route("/novo", methods=["GET", "POST"])
@login_required
def novo():
    if request.method == "POST":
        return _salvar(material=None)
    tipos_disp, deps_disp = _valores_distintos()
    return render_template(
        "material/form.html", modo="novo", material=None,
        TIPOS=TIPOS_MATERIAL, ESTADOS=ESTADOS_CONSERVACAO,
        tipos_existentes=tipos_disp, deps_existentes=deps_disp,
        log_criado=None, log_editado=None,
    )


@bp.route("/<int:mat_id>/editar", methods=["GET", "POST"])
@login_required
def editar(mat_id):
    material = db.session.get(Material, mat_id) or abort(404)
    if request.method == "POST":
        return _salvar(material=material)
    tipos_disp, deps_disp = _valores_distintos()
    log_criado, log_editado = _log_operadores_mat(mat_id)
    return render_template(
        "material/form.html", modo="editar", material=material,
        TIPOS=TIPOS_MATERIAL, ESTADOS=ESTADOS_CONSERVACAO,
        tipos_existentes=tipos_disp, deps_existentes=deps_disp,
        log_criado=log_criado, log_editado=log_editado,
    )


def _salvar(material):
    nomenclatura = (request.form.get("nomenclatura") or "").strip()
    if not nomenclatura:
        flash("Nomenclatura é obrigatória.", "error")
        return redirect(request.path)

    tipo = (request.form.get("tipo") or "OUTROS").upper().strip()
    # NÃO restringimos a TIPOS_MATERIAL — aceita valores existentes no banco

    if material is None:
        material = Material(nomenclatura=nomenclatura, tipo=tipo)
        db.session.add(material)
        novo_flag = True
    else:
        novo_flag = False

    material.nomenclatura = nomenclatura
    material.tipo = tipo
    material.ficha_siscofis = (request.form.get("ficha_siscofis") or "").strip() or None
    material.conta_contabil = (request.form.get("conta_contabil") or "").strip() or None
    material.dependencia = (request.form.get("dependencia") or "").strip() or None
    material.prateleira = (request.form.get("prateleira") or "").strip() or None
    material.qnt_siscofis = int(request.form.get("qnt_siscofis") or 0)
    material.valor_unitario = _parse_decimal(request.form.get("valor_unitario"))
    estado = (request.form.get("estado_conservacao") or "Bom").strip()
    if estado in ESTADOS_CONSERVACAO:
        material.estado_conservacao = estado
    material.obs = (request.form.get("obs") or "").strip() or None

    db.session.commit()
    acao = "CADASTRO_MATERIAL" if novo_flag else "EDICAO_MATERIAL"
    registrar_log(acao, f"'{nomenclatura}' ({material.tipo})", referencia_id=material.id)
    flash(
        f"Material '{nomenclatura}' {'cadastrado' if novo_flag else 'atualizado'}.",
        "success",
    )
    return redirect(url_for("material.lista"))


@bp.route("/<int:mat_id>/remover", methods=["POST"])
@login_required
def remover(mat_id):
    material = db.session.get(Material, mat_id) or abort(404)
    cautelado = (
        db.session.query(func.coalesce(func.sum(ItemCautelado.quantidade), 0))
        .join(Cautela)
        .filter(ItemCautelado.material_id == material.id)
        .filter(Cautela.devolvida.is_(False))
        .scalar() or 0
    )
    if cautelado > 0:
        flash(
            f"Não é possível remover '{material.nomenclatura}' — há "
            f"{int(cautelado)} unidade(s) em cautelas ativas.",
            "error",
        )
        return redirect(url_for("material.lista"))

    material.ativo = False
    db.session.commit()
    registrar_log("REMOCAO_MATERIAL", f"'{material.nomenclatura}'", referencia_id=material.id)
    flash(f"Material '{material.nomenclatura}' desativado.", "success")
    return redirect(url_for("material.lista"))
