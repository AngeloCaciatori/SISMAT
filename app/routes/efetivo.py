"""Rotas do Efetivo (lista, detalhes, cadastro, edição, foto, medidas)."""

import base64
import re
from io import BytesIO
from pathlib import Path
from datetime import datetime, timedelta
from flask import (
    Blueprint, render_template, request, redirect, url_for, flash, abort,
    current_app
)
from flask_login import login_required, current_user
from sqlalchemy import or_, func

from ..extensions import db
from .. import render_resp
from ..auth import admin_required
from ..models import (
    Militar, Medidas, Cautela, ItemCautelado, LogAuditoria,
    SITUACAO_ATIVO, SITUACAO_EXCLUIDO, SITUACAO_TRANSFERIDO, SITUACAO_LICENCA,
)
from ..utils import registrar_log


def _log_operadores(acao_criacao: str, acao_edicao: str, ref_id: int):
    """Retorna (label_criador, label_ultimo_editor) consultando o LogAuditoria."""
    criado = (
        LogAuditoria.query
        .filter_by(acao=acao_criacao, referencia_id=ref_id)
        .order_by(LogAuditoria.id.asc()).first()
    )
    editado = (
        LogAuditoria.query
        .filter_by(acao=acao_edicao, referencia_id=ref_id)
        .order_by(LogAuditoria.id.desc()).first()
    )
    return (
        criado.operador_label if criado else None,
        editado.operador_label if editado else None,
    )

bp = Blueprint("efetivo", __name__)

# Hierarquia oficial — do mais moderno (Sd EV) ao mais antigo (Gen Exe).
GRADUACOES_ORDENADAS = [
    "Sd EV", "Sd EP", "Cb",
    "3º Sgt", "2º Sgt", "1º Sgt", "ST", "Asp",
    "2º Ten", "1º Ten", "Cap", "Maj",
    "Ten Cel", "Cel",
    "Gen Brig", "Gen Div", "Gen Exe",
]

# Aliases comuns que vêm do Access ou que o usuário pode digitar.
GRADUACAO_ALIASES = {
    "SD EV": "Sd EV", "SD EP": "Sd EP", "CB": "Cb",
    "3°SGT": "3º Sgt", "3º SGT": "3º Sgt",
    "2°SGT": "2º Sgt", "2º SGT": "2º Sgt",
    "1°SGT": "1º Sgt", "1º SGT": "1º Sgt",
    "SUB TEN": "ST", "SUBTEN": "ST",
    "ASP OF": "Asp",
    "1°TEN": "1º Ten", "1º TEN": "1º Ten",
    "2°TEN": "2º Ten", "2º TEN": "2º Ten",
    "CAP": "Cap", "MAJ": "Maj",
    "TEN CEL": "Ten Cel", "CEL": "Cel",
    "GEN BRIG": "Gen Brig", "GEN DIV": "Gen Div", "GEN EXE": "Gen Exe",
}


def chave_graduacao(grad):
    """Chave de ordenação hierárquica para uma graduação.

    Tenta match exato, depois alias, depois prefixo. Desconhecidas vão pro fim.
    """
    if not grad:
        return (999, "")
    s = grad.strip().upper()
    # Match exato
    for i, g in enumerate(GRADUACOES_ORDENADAS):
        if s == g.upper():
            return (i, "")
    # Aliases
    if s in GRADUACAO_ALIASES:
        canonico = GRADUACAO_ALIASES[s]
        return (GRADUACOES_ORDENADAS.index(canonico), "")
    # Prefixo (ex: "2° SGT BURGOS")
    for i, g in enumerate(GRADUACOES_ORDENADAS):
        if s.startswith(g.upper()):
            return (i, s)
    return (999, s)


def _graduacoes_existentes_ordenadas():
    """Lista única de graduações no banco, em ordem hierárquica."""
    rows = (
        db.session.query(Militar.graduacao)
        .filter(Militar.excluido.is_(False))
        .filter(Militar.graduacao.isnot(None))
        .filter(Militar.graduacao != "")
        .distinct().all()
    )
    grads = {r[0] for r in rows if r[0]}
    return sorted(grads, key=chave_graduacao)


def _salvar_foto_militar(militar, arquivo=None, base64_data=None):
    try:
        from PIL import Image
    except ImportError:
        flash("Pillow não instalado — não é possível processar fotos.", "error")
        return None

    if not arquivo and not base64_data:
        return None

    try:
        if arquivo:
            img = Image.open(arquivo.stream)
        else:
            data = base64_data
            if "," in data:
                data = data.split(",", 1)[1]
            img_bytes = base64.b64decode(data)
            img = Image.open(BytesIO(img_bytes))

        if img.mode != "RGB":
            img = img.convert("RGB")
        img.thumbnail((400, 400))

        upload_dir = Path(current_app.config["UPLOAD_FOLDER"]) / "militares"
        upload_dir.mkdir(parents=True, exist_ok=True)
        nome = f"{militar.id}.jpg"
        path = upload_dir / nome
        img.save(path, "JPEG", quality=85, optimize=True)
        return f"militares/{nome}"
    except Exception as e:
        flash(f"Erro ao processar foto: {e}", "error")
        return None


def _validar_cpf(cpf):
    if not cpf:
        return None
    digitos = re.sub(r"\D", "", cpf)
    return digitos if digitos else None


@bp.route("/")
@login_required
def lista():
    busca = (request.args.get("q") or "").strip()
    graduacao = (request.args.get("graduacao") or "").strip()
    incluir_inativos = request.args.get("incluir_excluidos") == "1"
    com_foto = request.args.get("com_foto", "")

    query = Militar.query
    if not incluir_inativos:
        query = query.filter(Militar.situacao == SITUACAO_ATIVO)

    if busca:
        like = f"%{busca}%"
        query = query.filter(or_(
            Militar.nome_guerra.ilike(like),
            Militar.nome_completo.ilike(like),
            Militar.cpf.ilike(like),
        ))
    if graduacao:
        query = query.filter(Militar.graduacao == graduacao)
    if com_foto == "sim":
        query = query.filter(Militar.foto_path.isnot(None))
    elif com_foto == "nao":
        query = query.filter(Militar.foto_path.is_(None))

    militares = query.all()
    # Ordenação hierárquica em Python (a lista é pequena: ~172 itens)
    militares.sort(key=lambda m: (
        chave_graduacao(m.graduacao),
        m.antiguidade if m.antiguidade is not None else 99999,
        (m.nome_guerra or "").upper(),
    ))

    total = Militar.query.filter(Militar.situacao == SITUACAO_ATIVO).count()
    com_foto_count = (
        Militar.query.filter(Militar.situacao == SITUACAO_ATIVO)
        .filter(Militar.foto_path.isnot(None)).count()
    )
    com_medidas_count = (
        db.session.query(func.count(Medidas.id))
        .join(Militar).filter(Militar.situacao == SITUACAO_ATIVO).scalar() or 0
    )
    inativos_count = Militar.query.filter(Militar.situacao != SITUACAO_ATIVO).count()

    return render_resp(
        "efetivo/lista.html",
        militares=militares,
        total=total,
        com_foto_count=com_foto_count,
        com_medidas_count=com_medidas_count,
        inativos_count=inativos_count,
        busca=busca, graduacao=graduacao,
        incluir_excluidos=incluir_inativos, com_foto=com_foto,
        graduacoes=_graduacoes_existentes_ordenadas(),
    )


@bp.route("/<int:mil_id>")
@login_required
def detalhe(mil_id):
    militar = db.session.get(Militar, mil_id) or abort(404)
    cautelas_ativas = (
        Cautela.query.filter_by(militar_id=militar.id, devolvida=False)
        .order_by(Cautela.data_cautela.desc()).all()
    )
    hist_page = request.args.get("hist_page", 1, type=int)
    cautelas_devolvidas = (
        Cautela.query.filter_by(militar_id=militar.id, devolvida=True)
        .order_by(Cautela.devolvida_em.desc())
        .paginate(page=hist_page, per_page=15, error_out=False)
    )
    return render_resp(
        "efetivo/detalhe.html",
        militar=militar,
        cautelas_ativas=cautelas_ativas,
        cautelas_devolvidas=cautelas_devolvidas,
        SITUACAO_ATIVO=SITUACAO_ATIVO,
    )


@bp.route("/<int:mil_id>/imprimir-cautelas")
@login_required
def imprimir_cautelas(mil_id):
    """FIDU — Ficha Individual de Distribuição de Uniformes."""
    militar = db.session.get(Militar, mil_id) or abort(404)
    cautelas = (
        Cautela.query.filter_by(militar_id=militar.id, devolvida=False)
        .order_by(Cautela.data_cautela).all()
    )

    # Agrupa todos os itens por categoria (tipo do material)
    grupos = {}
    for cautela in cautelas:
        for item in cautela.itens:
            if not item.material:
                continue
            tipo = (item.material.tipo or "OUTROS").upper()
            grupos.setdefault(tipo, []).append({
                "qtd": item.quantidade,
                "nomenclatura": item.material.nomenclatura,
                "data": cautela.data_cautela,
                "obs": item.obs or "",
            })

    # Ordena dentro de cada grupo por nomenclatura
    for tipo in grupos:
        grupos[tipo].sort(key=lambda x: x["nomenclatura"])

    # Ordem oficial dos blocos: EQUIPAMENTO, FARDAMENTO, MATERIAL, OUTROS
    ordem = ["EQUIPAMENTO", "FARDAMENTO", "MATERIAL", "OUTROS"]
    grupos_ordenados = [(t, grupos[t]) for t in ordem if t in grupos]
    # Quaisquer outros tipos imprevistos vão depois
    extras = [t for t in grupos if t not in ordem]
    grupos_ordenados.extend((t, grupos[t]) for t in extras)

    return render_template(
        "efetivo/imprimir_cautelas.html",
        militar=militar,
        grupos=grupos_ordenados,
        total_itens=sum(len(g) for _, g in grupos_ordenados),
    )


@bp.route("/novo", methods=["GET", "POST"])
@login_required
def novo():
    if request.method == "POST":
        return _salvar(militar=None)
    return render_template(
        "efetivo/form.html", modo="novo", militar=None,
        graduacoes=GRADUACOES_ORDENADAS,
        log_criado=None, log_editado=None,
    )


@bp.route("/<int:mil_id>/editar", methods=["GET", "POST"])
@login_required
def editar(mil_id):
    militar = db.session.get(Militar, mil_id) or abort(404)
    if request.method == "POST":
        return _salvar(militar=militar)
    log_criado, log_editado = _log_operadores("CADASTRO_MILITAR", "EDICAO_MILITAR", mil_id)
    return render_template(
        "efetivo/form.html", modo="editar", militar=militar,
        graduacoes=GRADUACOES_ORDENADAS,
        log_criado=log_criado, log_editado=log_editado,
    )


def _salvar(militar):
    cpf = _validar_cpf(request.form.get("cpf"))
    if not cpf:
        flash("CPF é obrigatório.", "error")
        return redirect(request.path)

    # Unicidade
    existente = Militar.query.filter_by(cpf=cpf).first()
    if existente and (militar is None or existente.id != militar.id):
        flash(f"Já existe militar com CPF {cpf}.", "error")
        return redirect(request.path)

    # --- Campos obrigatórios adicionais ---
    graduacao = (request.form.get("graduacao") or "").strip() or None
    if not graduacao:
        flash("Graduação é obrigatória.", "error")
        return redirect(request.path)

    nome_guerra = (request.form.get("nome_guerra") or "").strip() or None
    if not nome_guerra:
        flash("Nome de guerra é obrigatório.", "error")
        return redirect(request.path)

    nome_completo = (request.form.get("nome_completo") or "").strip() or None
    if not nome_completo:
        flash("Nome completo é obrigatório.", "error")
        return redirect(request.path)

    telefone1 = (request.form.get("telefone1") or "").strip() or None
    if not telefone1:
        flash("Pelo menos um telefone é obrigatório.", "error")
        return redirect(request.path)

    if militar is None:
        militar = Militar(cpf=cpf, nome_guerra=nome_guerra, graduacao=graduacao)
        db.session.add(militar)
        novo_flag = True
    else:
        militar.cpf = cpf
        novo_flag = False

    militar.graduacao = graduacao
    militar.nome_guerra = nome_guerra
    militar.nome_completo = nome_completo
    militar.ri = (request.form.get("ri") or "").strip() or None

    ant = (request.form.get("antiguidade") or "").strip()
    try:
        militar.antiguidade = float(ant) if ant else None
    except ValueError:
        militar.antiguidade = None

    militar.numero = (request.form.get("numero") or "").strip() or None
    militar.telefone1 = telefone1
    militar.telefone2 = (request.form.get("telefone2") or "").strip() or None
    militar.om = (request.form.get("om") or current_app.config["OM_PADRAO"]).strip()

    db.session.commit()

    arquivo = request.files.get("foto") if "foto" in request.files else None
    if arquivo and arquivo.filename:
        path = _salvar_foto_militar(militar, arquivo=arquivo)
        if path:
            militar.foto_path = path
            db.session.commit()

    nome_log = f"{militar.graduacao or ''} {militar.nome_guerra or militar.cpf}".strip()
    acao = "CADASTRO_MILITAR" if novo_flag else "EDICAO_MILITAR"
    registrar_log(acao, f"{nome_log} (CPF {cpf})", referencia_id=militar.id)

    flash(
        f"Militar {nome_log} {'cadastrado' if novo_flag else 'atualizado'}.",
        "success",
    )
    return redirect(url_for("efetivo.detalhe", mil_id=militar.id))


@bp.route("/<int:mil_id>/foto", methods=["POST"])
@login_required
def upload_foto(mil_id):
    militar = db.session.get(Militar, mil_id) or abort(404)
    arquivo = request.files.get("foto")
    base64_data = request.form.get("foto_base64")

    if not arquivo and not base64_data:
        flash("Nenhuma foto enviada.", "error")
        return redirect(url_for("efetivo.detalhe", mil_id=militar.id))

    path = _salvar_foto_militar(militar, arquivo=arquivo, base64_data=base64_data)
    if path:
        militar.foto_path = path
        db.session.commit()
        flash("Foto atualizada.", "success")

    return redirect(url_for("efetivo.detalhe", mil_id=militar.id))


@bp.route("/<int:mil_id>/foto/remover", methods=["POST"])
@login_required
def remover_foto(mil_id):
    militar = db.session.get(Militar, mil_id) or abort(404)
    if militar.foto_path:
        path = Path(current_app.config["UPLOAD_FOLDER"]) / militar.foto_path
        if path.exists():
            try:
                path.unlink()
            except OSError:
                pass
        militar.foto_path = None
        db.session.commit()
        flash("Foto removida.", "success")
    return redirect(url_for("efetivo.detalhe", mil_id=militar.id))


@bp.route("/<int:mil_id>/medidas", methods=["POST"])
@login_required
def atualizar_medidas(mil_id):
    militar = db.session.get(Militar, mil_id) or abort(404)
    med = militar.medidas
    if not med:
        med = Medidas(militar_id=militar.id)
        db.session.add(med)

    _TAMANHOS_VALIDOS = {"PP", "P", "M", "G", "GG", "XG"}

    def _val_tamanho(campo):
        """Valida select de tamanho (PP/P/M/G/GG/XG). Retorna None se vazio."""
        raw = (request.form.get(campo) or "").strip().upper()
        if not raw:
            return None
        return raw if raw in _TAMANHOS_VALIDOS else "INVALIDO"

    def _val_int(campo, minv, maxv):
        """Valida campo numérico. Retorna string inteira, None se vazio, ou 'INVALIDO'."""
        raw = (request.form.get(campo) or "").strip()
        if not raw:
            return None
        try:
            v = int(raw)
        except (TypeError, ValueError):
            return "INVALIDO"
        return str(v) if minv <= v <= maxv else "INVALIDO"

    camisa_val = _val_tamanho("camisa")
    calca_val  = _val_tamanho("calca")
    cabeca_val = _val_int("cabeca", 50, 70)
    pe_val     = _val_int("pe", 30, 50)

    invalidos = []
    if camisa_val == "INVALIDO": invalidos.append("Camisa/Gandola")
    if calca_val  == "INVALIDO": invalidos.append("Calca/Shorts")
    if cabeca_val == "INVALIDO": invalidos.append("Cabeca (50-70 cm)")
    if pe_val     == "INVALIDO": invalidos.append("Pe (30-50)")

    if invalidos:
        flash(
            "Valor invalido nos campos: {}. Verifique e tente novamente.".format(
                ", ".join(invalidos)
            ),
            "error",
        )
        return redirect(url_for("efetivo.detalhe", mil_id=militar.id))

    med.camisa  = camisa_val
    med.calca   = calca_val
    med.cabeca  = cabeca_val
    med.pe      = pe_val

    db.session.commit()
    flash("Medidas atualizadas.", "success")
    return redirect(url_for("efetivo.detalhe", mil_id=militar.id))


SITUACOES_VALIDAS = {
    SITUACAO_ATIVO: "Ativo",
    SITUACAO_EXCLUIDO: "Excluído",
    SITUACAO_TRANSFERIDO: "Transferido",
    SITUACAO_LICENCA: "Licença",
}


@bp.route("/<int:mil_id>/mudar-situacao", methods=["POST"])
@login_required
def mudar_situacao(mil_id):
    """Muda a situação de um militar (ATIVO / EXCLUIDO / TRANSFERIDO / LICENCA)."""
    militar = db.session.get(Militar, mil_id) or abort(404)
    nova_sit = (request.form.get("situacao") or "").strip().upper()
    motivo = (request.form.get("motivo") or "").strip() or None

    if nova_sit not in SITUACOES_VALIDAS:
        flash("Situação inválida.", "error")
        return redirect(url_for("efetivo.detalhe", mil_id=militar.id))

    # Impede saída de ATIVO se há cautelas abertas
    if nova_sit != SITUACAO_ATIVO and militar.situacao == SITUACAO_ATIVO:
        cautelas_abertas = Cautela.query.filter_by(
            militar_id=militar.id, devolvida=False
        ).count()
        if cautelas_abertas > 0:
            nome = f"{militar.graduacao or ''} {militar.nome_guerra or militar.cpf}"
            flash(
                f"Não é possível alterar situação — {nome} "
                f"tem {cautelas_abertas} cautela(s) ativa(s).",
                "error",
            )
            return redirect(url_for("efetivo.detalhe", mil_id=militar.id))

    situacao_anterior = militar.situacao
    militar.situacao = nova_sit
    militar.situacao_em = datetime.utcnow()
    militar.situacao_motivo = motivo

    # Mantém backward compat com campos legados
    if nova_sit == SITUACAO_EXCLUIDO:
        militar.excluido = True
        militar.excluido_em = militar.situacao_em
    elif nova_sit == SITUACAO_ATIVO:
        militar.excluido = False
        militar.excluido_em = None

    db.session.commit()

    nome_log = f"{militar.graduacao or ''} {militar.nome_guerra or militar.cpf}".strip()
    descricao = (
        f"{nome_log}: {situacao_anterior} → {nova_sit}"
        + (f" (motivo: {motivo})" if motivo else "")
    )
    registrar_log("MUDANCA_SITUACAO_MILITAR", descricao, referencia_id=militar.id)

    label_nova = SITUACOES_VALIDAS[nova_sit]
    flash(f"{nome_log} — situação alterada para {label_nova}.", "success")
    return redirect(url_for("efetivo.detalhe", mil_id=militar.id))
