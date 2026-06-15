"""Rotas de Operadores do Sistema + administração (backup, etc.)."""

import secrets
import shutil
import sqlite3
import string
import tempfile
import zipfile
from datetime import datetime
from pathlib import Path
from flask import (
    Blueprint, render_template, request, redirect, url_for, flash, abort,
    current_app, send_file
)
from flask_login import login_required, current_user

from ..extensions import db
from ..auth import admin_required
from ..models import Operador, Militar, LogAuditoria, NIVEL_ADMIN, NIVEL_OPERADOR, BackupLog

bp = Blueprint("operadores", __name__)


def gerar_senha_temp(tamanho: int = 10) -> str:
    """Gera uma senha temporária legível (sem caracteres ambíguos)."""
    alfabeto = string.ascii_letters + string.digits
    for c in "0OIl1":
        alfabeto = alfabeto.replace(c, "")
    return "".join(secrets.choice(alfabeto) for _ in range(tamanho))


@bp.route("/")
@login_required
@admin_required
def lista():
    operadores = Operador.query.order_by(Operador.nivel_seguranca, Operador.login).all()
    return render_template("operadores/lista.html", operadores=operadores)


@bp.route("/novo", methods=["GET", "POST"])
@login_required
@admin_required
def novo():
    militares = Militar.query.filter_by(excluido=False).order_by(Militar.nome_guerra).all()

    if request.method == "POST":
        login_str = (request.form.get("login") or "").strip().lower()
        senha = request.form.get("senha") or ""
        nivel = int(request.form.get("nivel_seguranca", NIVEL_OPERADOR))
        secao = (request.form.get("secao") or "Reserva de Material").strip()
        militar_id = request.form.get("militar_id") or None
        militar_id = int(militar_id) if militar_id else None

        if not login_str or not senha:
            flash("Login e senha são obrigatórios.", "error")
            return render_template("operadores/form.html", militares=militares,
                                   modo="novo", op=None)
        if len(senha) < 6:
            flash("A senha deve ter ao menos 6 caracteres.", "error")
            return render_template("operadores/form.html", militares=militares,
                                   modo="novo", op=None)
        if Operador.query.filter_by(login=login_str).first():
            flash(f"Já existe operador com login '{login_str}'.", "error")
            return render_template("operadores/form.html", militares=militares,
                                   modo="novo", op=None)

        op = Operador(
            login=login_str,
            nivel_seguranca=nivel,
            secao=secao,
            militar_id=militar_id,
            senha_temporaria=True,
            ativo=True,
        )
        op.definir_senha(senha)
        db.session.add(op)
        db.session.commit()

        flash(f"Operador '{login_str}' cadastrado. A senha será trocada no 1º login.", "success")
        return redirect(url_for("operadores.lista"))

    return render_template("operadores/form.html", militares=militares,
                           modo="novo", op=None)


@bp.route("/<int:op_id>/editar", methods=["GET", "POST"])
@login_required
@admin_required
def editar(op_id):
    op = db.session.get(Operador, op_id) or abort(404)
    militares = Militar.query.filter_by(excluido=False).order_by(Militar.nome_guerra).all()

    if request.method == "POST":
        op.nivel_seguranca = int(request.form.get("nivel_seguranca", NIVEL_OPERADOR))
        op.secao = (request.form.get("secao") or "Reserva de Material").strip()
        militar_id = request.form.get("militar_id") or None
        op.militar_id = int(militar_id) if militar_id else None
        op.ativo = request.form.get("ativo") == "on"

        if op.id == current_user.id and op.nivel_seguranca != NIVEL_ADMIN:
            outros = Operador.query.filter(
                Operador.nivel_seguranca == NIVEL_ADMIN,
                Operador.id != op.id,
                Operador.ativo.is_(True),
            ).count()
            if outros == 0:
                flash("Você não pode se rebaixar — é o único administrador ativo.", "error")
                return redirect(url_for("operadores.editar", op_id=op.id))

        db.session.commit()
        flash(f"Operador '{op.login}' atualizado.", "success")
        return redirect(url_for("operadores.lista"))

    return render_template("operadores/form.html", militares=militares,
                           modo="editar", op=op)


@bp.route("/<int:op_id>/resetar-senha", methods=["GET", "POST"])
@login_required
@admin_required
def resetar_senha(op_id):
    op = db.session.get(Operador, op_id) or abort(404)

    if request.method == "POST":
        nova = (request.form.get("nova_senha") or "").strip()
        if not nova or len(nova) < 6:
            flash("Senha temporária deve ter ao menos 6 caracteres.", "error")
            return redirect(url_for("operadores.resetar_senha", op_id=op.id))

        op.definir_senha(nova)
        op.senha_temporaria = True
        db.session.commit()

        flash(
            f"Senha de '{op.login}' resetada. Anote e entregue presencialmente: {nova}",
            "success"
        )
        return redirect(url_for("operadores.lista"))

    senha_sugerida = gerar_senha_temp()
    return render_template("operadores/resetar_senha.html",
                           op=op, senha_sugerida=senha_sugerida)


@bp.route("/<int:op_id>/remover", methods=["POST"])
@login_required
@admin_required
def remover(op_id):
    op = db.session.get(Operador, op_id) or abort(404)

    if op.id == current_user.id:
        flash("Você não pode remover a si mesmo.", "error")
        return redirect(url_for("operadores.lista"))

    if op.nivel_seguranca == NIVEL_ADMIN:
        outros = Operador.query.filter(
            Operador.nivel_seguranca == NIVEL_ADMIN,
            Operador.id != op.id,
            Operador.ativo.is_(True),
        ).count()
        if outros == 0:
            flash("Não é possível remover o único administrador ativo.", "error")
            return redirect(url_for("operadores.lista"))

    op.ativo = False
    db.session.commit()
    flash(f"Operador '{op.login}' desativado.", "success")
    return redirect(url_for("operadores.lista"))


# ===== Backup do Banco =====

def _pasta_backups():
    base = Path(current_app.config["SQLALCHEMY_DATABASE_URI"].replace("sqlite:///", "")).parent
    pasta = base / "backups"
    pasta.mkdir(parents=True, exist_ok=True)
    return base, pasta


def _restaurar_db(source_path: Path) -> None:
    """Substitui o banco ativo pelo source_path via sqlite3.backup() (atômico).
    Seguro mesmo com Flask em execução — não requer parar o servidor.
    """
    db_path = Path(
        current_app.config["SQLALCHEMY_DATABASE_URI"].replace("sqlite:///", "")
    )
    src = sqlite3.connect(str(source_path))
    dst = sqlite3.connect(str(db_path))
    try:
        src.backup(dst)
    finally:
        src.close()
        dst.close()


@bp.route("/backup")
@login_required
@admin_required
def backup_lista():
    base, pasta_backups = _pasta_backups()
    arquivos = []
    for p in sorted(pasta_backups.glob("sismat-*.zip"), reverse=True):
        st = p.stat()
        arquivos.append({
            "nome": p.name,
            "tamanho_kb": st.st_size / 1024,
            "criado": datetime.fromtimestamp(st.st_mtime),
        })

    db_atual = base / "sismat.db"
    db_info = {
        "path": str(db_atual),
        "existe": db_atual.exists(),
        "tamanho_kb": db_atual.stat().st_size / 1024 if db_atual.exists() else 0,
        "modificado": datetime.fromtimestamp(db_atual.stat().st_mtime) if db_atual.exists() else None,
    }

    # Últimos registros do log de backup
    try:
        ultimos_logs = (
            BackupLog.query.order_by(BackupLog.criado_em.desc()).limit(20).all()
        )
    except Exception:
        ultimos_logs = []

    return render_template(
        "operadores/backup.html",
        arquivos=arquivos[:30],
        total=len(arquivos),
        db_info=db_info,
        pasta=str(pasta_backups),
        ultimos_logs=ultimos_logs,
    )


@bp.route("/backup/criar", methods=["POST"])
@login_required
@admin_required
def backup_criar():
    """Cria backup manualmente via interface web (tipo 'manual')."""
    import subprocess
    import sys
    base = Path(current_app.config["SQLALCHEMY_DATABASE_URI"].replace("sqlite:///", "")).parent.parent
    python = Path(sys.executable)
    script = base / "scripts" / "backup_db.py"
    try:
        result = subprocess.run(
            [str(python), str(script), "--tipo", "diario"],
            capture_output=True, text=True, timeout=60, cwd=str(base)
        )
        if result.returncode == 0:
            flash("Backup criado com sucesso.", "success")
        else:
            flash(f"Erro no backup: {result.stderr[-300:]}", "error")
    except Exception as e:
        flash(f"Erro ao executar backup: {e}", "error")
    return redirect(url_for("operadores.backup_lista"))



@bp.route("/backup/importar", methods=["POST"])
@login_required
@admin_required
def backup_importar():
    """Importa um banco externo (ZIP de backup ou .db direto) enviado pelo usuário."""
    arq = request.files.get("arquivo")
    if not arq or not arq.filename:
        flash("Nenhum arquivo selecionado.", "error")
        return redirect(url_for("operadores.backup_lista"))

    nome = arq.filename
    if not (nome.endswith(".zip") or nome.endswith(".db")):
        flash("Formato inválido. Envie um arquivo .zip (backup SISMAT) ou .db (SQLite direto).", "error")
        return redirect(url_for("operadores.backup_lista"))

    try:
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            if nome.endswith(".zip"):
                zip_path = tmp / "upload.zip"
                arq.save(str(zip_path))
                with zipfile.ZipFile(zip_path) as zf:
                    if "sismat.db" not in zf.namelist():
                        flash("ZIP inválido: não contém o arquivo sismat.db.", "error")
                        return redirect(url_for("operadores.backup_lista"))
                    zf.extract("sismat.db", tmp)
                _restaurar_db(tmp / "sismat.db")
            else:  # .db direto
                db_path = tmp / "upload.db"
                arq.save(str(db_path))
                _restaurar_db(db_path)

        flash(
            f"Banco importado com sucesso a partir de '{nome}'. "
            "Recarregue a página para ver os dados atualizados.",
            "success"
        )
    except Exception as e:
        flash(f"Erro ao importar banco: {e}", "error")

    return redirect(url_for("operadores.backup_lista"))


@bp.route("/backup/<nome>/restaurar", methods=["POST"])
@login_required
@admin_required
def backup_restaurar(nome):
    """Restaura o banco a partir de um backup ZIP já existente na pasta de backups."""
    if "/" in nome or "\\" in nome or ".." in nome:
        abort(400)
    if not nome.endswith(".zip"):
        abort(400)

    _, pasta = _pasta_backups()
    zip_path = pasta / nome
    if not zip_path.exists():
        abort(404)

    try:
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            with zipfile.ZipFile(zip_path) as zf:
                if "sismat.db" not in zf.namelist():
                    flash("ZIP inválido: não contém sismat.db.", "error")
                    return redirect(url_for("operadores.backup_lista"))
                zf.extract("sismat.db", tmp)
            _restaurar_db(tmp / "sismat.db")

        flash(
            f"Banco restaurado a partir de '{nome}'. "
            "Recarregue a página para ver os dados atualizados.",
            "success"
        )
    except Exception as e:
        flash(f"Erro ao restaurar backup: {e}", "error")

    return redirect(url_for("operadores.backup_lista"))


@bp.route("/backup/<nome>/baixar")
@login_required
@admin_required
def backup_baixar(nome):
    if "/" in nome or "\\" in nome or ".." in nome:
        abort(400)
    if not (nome.endswith(".db") or nome.endswith(".zip")):
        abort(400)
    _, pasta = _pasta_backups()
    arq = pasta / nome
    if not arq.exists():
        abort(404)
    return send_file(arq, as_attachment=True, download_name=nome)


@bp.route("/backup/<nome>/remover", methods=["POST"])
@login_required
@admin_required
def backup_remover(nome):
    if "/" in nome or "\\" in nome or ".." in nome:
        abort(400)
    _, pasta = _pasta_backups()
    arq = pasta / nome
    if arq.exists():
        try:
            arq.unlink()
            flash(f"Backup '{nome}' removido.", "success")
        except OSError as e:
            flash(f"Erro ao remover: {e}", "error")
    return redirect(url_for("operadores.backup_lista"))


# ---------------------------------------------------------------------------
# Log de auditoria
# ---------------------------------------------------------------------------

@bp.route("/log")
@login_required
@admin_required
def log_auditoria():
    """Histórico de ações registradas no sistema."""
    pagina = request.args.get("p", 1, type=int)
    filtro_acao = (request.args.get("acao") or "").strip()
    filtro_op = (request.args.get("op") or "").strip()

    query = LogAuditoria.query

    if filtro_acao:
        query = query.filter(LogAuditoria.acao == filtro_acao)
    if filtro_op:
        query = (
            query.join(Operador, LogAuditoria.operador_id == Operador.id, isouter=True)
            .filter(Operador.login.ilike(f"%{filtro_op}%"))
        )

    total = query.count()
    por_pagina = 50
    entradas = (
        query.order_by(LogAuditoria.criado_em.desc())
        .offset((pagina - 1) * por_pagina)
        .limit(por_pagina)
        .all()
    )

    # Lista de ações distintas para o filtro
    acoes_disponiveis = [
        r[0] for r in
        db.session.query(LogAuditoria.acao).distinct().order_by(LogAuditoria.acao).all()
    ]

    total_paginas = max(1, (total + por_pagina - 1) // por_pagina)

    return render_template(
        "operadores/log.html",
        entradas=entradas,
        total=total,
        pagina=pagina,
        total_paginas=total_paginas,
        filtro_acao=filtro_acao,
        filtro_op=filtro_op,
        acoes_disponiveis=acoes_disponiveis,
    )
