"""Rotas de Documentação — modelos somente-leitura, documentos editáveis."""

from datetime import datetime

from flask import (
    Blueprint, render_template, redirect, url_for,
    request, flash, abort
)
from flask_login import login_required, current_user

from ..extensions import db
from ..models import ModeloDocumento

bp = Blueprint("documentacao", __name__)


# ─── LISTA ────────────────────────────────────────────────────────────────────

@bp.route("/")
@login_required
def lista():
    """Tela principal: modelos (padrao=True) + documentos criados (padrao=False)."""
    modelos    = ModeloDocumento.query.filter_by(padrao=True ).order_by(ModeloDocumento.nome).all()
    documentos = ModeloDocumento.query.filter_by(padrao=False).order_by(ModeloDocumento.atualizado_em.desc()).all()
    return render_template("documentacao/lista.html",
                           modelos=modelos, documentos=documentos)


# ─── CRIAR DOCUMENTO A PARTIR DE UM MODELO ────────────────────────────────────

@bp.route("/<int:modelo_id>/criar-documento", methods=["POST"])
@login_required
def criar_documento(modelo_id):
    """Duplica um modelo (padrao=True) em um documento editável (padrao=False)."""
    modelo = db.session.get(ModeloDocumento, modelo_id) or abort(404)
    if not modelo.padrao:
        flash("Use um modelo como base para criar documentos.", "error")
        return redirect(url_for("documentacao.lista"))

    doc = ModeloDocumento(
        nome=f"{modelo.nome} — {datetime.now().strftime('%d/%m/%Y')}",
        conteudo_html=modelo.conteudo_html,
        padrao=False
    )
    db.session.add(doc)
    db.session.commit()
    flash(f"Documento criado a partir de '{modelo.nome}'. Edite à vontade.", "success")
    return redirect(url_for("documentacao.editar", doc_id=doc.id))


# ─── NOVO DOCUMENTO EM BRANCO ─────────────────────────────────────────────────

@bp.route("/novo", methods=["GET", "POST"])
@login_required
def novo():
    """Cria um documento em branco (não é um modelo padrão)."""
    if request.method == "POST":
        nome     = request.form.get("nome", "").strip()
        conteudo = request.form.get("conteudo_html", "").strip()
        if not nome:
            flash("Nome do documento é obrigatório.", "error")
            return render_template("documentacao/editor.html",
                                   doc=None, nome=nome, conteudo=conteudo)
        doc = ModeloDocumento(nome=nome, conteudo_html=conteudo, padrao=False)
        db.session.add(doc)
        db.session.commit()
        flash(f"Documento '{nome}' salvo.", "success")
        return redirect(url_for("documentacao.lista"))
    return render_template("documentacao/editor.html",
                           doc=None, nome="", conteudo="")


# ─── EDITAR DOCUMENTO (apenas padrao=False) ───────────────────────────────────

@bp.route("/<int:doc_id>/editar", methods=["GET", "POST"])
@login_required
def editar(doc_id):
    doc = db.session.get(ModeloDocumento, doc_id) or abort(404)
    if doc.padrao:
        flash("Modelos padrão não podem ser editados. Crie um documento a partir dele.", "warning")
        return redirect(url_for("documentacao.lista"))

    if request.method == "POST":
        nome     = request.form.get("nome", "").strip()
        conteudo = request.form.get("conteudo_html", "").strip()
        if not nome:
            flash("Nome é obrigatório.", "error")
            return render_template("documentacao/editor.html",
                                   doc=doc, nome=nome, conteudo=conteudo)
        doc.nome         = nome
        doc.conteudo_html = conteudo
        db.session.commit()
        flash(f"Documento '{nome}' atualizado.", "success")
        return redirect(url_for("documentacao.lista"))

    return render_template("documentacao/editor.html",
                           doc=doc, nome=doc.nome, conteudo=doc.conteudo_html)


# ─── EXCLUIR DOCUMENTO (apenas padrao=False) ──────────────────────────────────

@bp.route("/<int:doc_id>/excluir", methods=["POST"])
@login_required
def excluir(doc_id):
    doc = db.session.get(ModeloDocumento, doc_id) or abort(404)
    if doc.padrao:
        flash("Modelos padrão não podem ser excluídos.", "error")
        return redirect(url_for("documentacao.lista"))
    nome = doc.nome
    db.session.delete(doc)
    db.session.commit()
    flash(f"Documento '{nome}' excluído.", "success")
    return redirect(url_for("documentacao.lista"))


# ─── VISUALIZAR / IMPRIMIR ────────────────────────────────────────────────────

@bp.route("/<int:doc_id>/gerar")
@login_required
def gerar(doc_id):
    doc = db.session.get(ModeloDocumento, doc_id) or abort(404)
    now = datetime.now()
    from flask import current_app
    cfg = current_app.config
    variaveis = {
        "NOME_INSTITUICAO": cfg.get("NOME_INSTITUICAO", "BATERIA DE COMANDO DA AD/5"),
        "CIDADE_QUARTEL":   cfg.get("CIDADE_QUARTEL",   "Curitiba/PR"),
        "DATA_HOJE":        now.strftime("%d/%m/%Y"),
        "OPERADOR":         current_user.login,
        "MILITAR_NOME":       "______________________________",
        "MILITAR_GRADUACAO":  "________",
        "MILITAR_CPF":        "___.___.___-__",
        "CAUTELA_NUMERO":     "________",
        "CAUTELA_DATA":       "____/____/________",
        "ITENS_LISTA":        "[ itens da cautela ]",
    }
    html = doc.conteudo_html
    for chave, valor in variaveis.items():
        html = html.replace("{{" + chave + "}}", str(valor))
    return render_template("documentacao/gerar.html",
                           modelo=doc, conteudo_renderizado=html, now=now)
