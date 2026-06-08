"""Blueprint de assinatura digital via QR Code local.

Rotas desktop (requerem login):
    GET  /assinatura/perfil/qr                — admin gera QR para cadastro de operador
    GET  /assinatura/perfil/<token>/status    — polling JSON (cadastro)
    POST /assinatura/senha-confirma           — valida senha + renova janela de confiança
    POST /assinatura/aplicar-operador         — operador assina cautela (janela aberta)
    POST /assinatura/qr-recebedor             — admin gera QR para recebedor assinar
    GET  /assinatura/cautela/<id>/status-recebedor  — polling JSON recebedor

Rotas mobile (SEM login — acesso via QR Code):
    GET  /assinatura/m/perfil/<token>         — canvas para cadastrar assinatura do operador
    POST /assinatura/m/perfil/<token>         — grava assinatura no Operador
    GET  /assinatura/m/<token>                — canvas para o recebedor assinar
    POST /assinatura/m/<token>                — grava AssinaturaAplicada do recebedor
"""

from datetime import datetime

from flask import (
    Blueprint, render_template, request, redirect, url_for,
    jsonify, flash, abort, session,
)
from flask_login import login_required, current_user

from ..extensions import db, csrf
from ..models import (
    Operador, Cautela, AssinaturaAplicada, TokenAssinatura,
)
from ..utils import registrar_log
from ..utils.assinatura import (
    gerar_token, consumir_token, gerar_qr_png_base64,
    janela_aberta, renovar_janela, precisa_assinatura, ip_externo,
)

bp = Blueprint("assinatura", __name__, url_prefix="/assinatura")


# ------------------------------------------------------------------ #
#  HELPERS internos
# ------------------------------------------------------------------ #

def _url_base() -> str:
    """Retorna http://<IP LAN>:<porta> para montar URLs do QR.
    Sempre usa o IP da LAN, mesmo quando o admin acessa via localhost.
    """
    import socket
    porta = request.host.split(":")[-1] if ":" in request.host else "5000"
    try:
        # Pega o IP da interface de rede local (não loopback)
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip_lan = s.getsockname()[0]
        s.close()
    except Exception:
        ip_lan = request.host.split(":")[0]  # fallback
    return f"http://{ip_lan}:{porta}"


def _label_operador(op: Operador) -> str:
    if op.militar:
        grad = op.militar.graduacao or ""
        nome = op.militar.nome_guerra or ""
        return f"{grad} {nome}".strip() or op.login
    return op.login


# ================================================================== #
#  CADASTRO DE ASSINATURA DO OPERADOR
# ================================================================== #

@bp.route("/perfil/qr")
@login_required
def perfil_qr():
    """Admin gera QR Code para que um operador cadastre sua assinatura."""
    if not current_user.is_admin:
        abort(403)

    operador_id = request.args.get("operador_id", type=int)
    if not operador_id:
        flash("Informe o operador.", "error")
        return redirect(url_for("operadores.lista"))

    operador = db.session.get(Operador, operador_id) or abort(404)
    if operador.is_admin:
        flash("Admin não usa assinatura digital.", "warning")
        return redirect(url_for("operadores.lista"))

    ip = ip_externo(request)
    tok = gerar_token("cadastro_operador", operador_id=operador_id, validade_min=5, ip=ip)
    url_mobile = f"{_url_base()}{url_for('assinatura.mobile_perfil', token=tok.token)}"
    qr_data_uri = gerar_qr_png_base64(url_mobile)

    return render_template(
        "assinatura/qr_perfil.html",
        operador=operador,
        token=tok.token,
        qr_data_uri=qr_data_uri,
        url_mobile=url_mobile,
        expira_min=5,
    )


@bp.route("/perfil/<token>/status")
@login_required
def perfil_status(token):
    """Polling JSON — desktop aguarda o operador assinar no celular."""
    tok = TokenAssinatura.query.filter_by(token=token).first()
    if not tok:
        return jsonify({"status": "invalido"})
    if datetime.utcnow() > tok.expira_em:
        return jsonify({"status": "expirado"})
    if tok.usado:
        # Busca a assinatura recém-gravada
        op = db.session.get(Operador, tok.operador_id)
        label = _label_operador(op) if op else "?"
        return jsonify({"status": "ok", "operador": label})
    return jsonify({"status": "aguardando"})


# ================================================================== #
#  MOBILE — cadastro de assinatura do operador
# ================================================================== #

@bp.route("/m/perfil/<token>", methods=["GET", "POST"])
@csrf.exempt
def mobile_perfil(token):
    """Sem @login_required — acessado via QR pelo celular do operador."""
    tok = TokenAssinatura.query.filter_by(token=token, usado=False).first()
    if not tok:
        return render_template("assinatura/token_invalido.html", motivo="inválido ou já usado"), 400
    if datetime.utcnow() > tok.expira_em:
        return render_template("assinatura/token_invalido.html", motivo="expirado"), 400
    if tok.tipo != "cadastro_operador" or not tok.operador_id:
        return render_template("assinatura/token_invalido.html", motivo="tipo incorreto"), 400

    operador = db.session.get(Operador, tok.operador_id)
    if not operador:
        abort(404)

    if request.method == "POST":
        imagem = (request.form.get("assinatura") or "").strip()
        if not imagem or not imagem.startswith("data:image/png;base64,"):
            return jsonify({"ok": False, "erro": "Assinatura inválida."}), 400

        # Consome o token
        ip = ip_externo(request)
        tok_consumido = consumir_token(token, ip)
        if not tok_consumido:
            return jsonify({"ok": False, "erro": "Token expirado durante envio."}), 400

        # Grava no operador
        operador.assinatura_base64 = imagem
        operador.assinatura_cadastrada_em = datetime.utcnow()
        db.session.commit()

        registrar_log(
            "ASSINATURA_CADASTRADA",
            f"Operador {operador.login} cadastrou assinatura digital.",
            referencia_id=operador.id,
        )
        return jsonify({"ok": True})

    return render_template(
        "mobile/assinar_perfil.html",
        operador=operador,
        token=token,
    )


# ================================================================== #
#  JANELA DE CONFIANÇA — validação de senha desktop
# ================================================================== #

@bp.route("/senha-confirma", methods=["POST"])
@login_required
def senha_confirma():
    """Valida senha do operador logado e renova a janela de confiança."""
    if current_user.is_admin:
        # Admin não assina — mas pode chamar se necessário
        return jsonify({"ok": True})

    senha = request.form.get("senha") or request.json.get("senha", "") if request.is_json else request.form.get("senha", "")
    if not current_user.verificar_senha(senha):
        return jsonify({"ok": False, "erro": "Senha incorreta."}), 401

    renovar_janela(session)
    return jsonify({"ok": True})


# ================================================================== #
#  OPERADOR ASSINA CAUTELA — via janela de confiança ou senha
# ================================================================== #

@bp.route("/aplicar-operador", methods=["POST"])
@login_required
def aplicar_operador():
    """Operador assina como 'operador' numa cautela (recebimento ou devolução)."""
    if current_user.is_admin:
        return jsonify({"ok": True, "aviso": "Admin não assina."})

    if precisa_assinatura(current_user):
        return jsonify({"ok": False, "erro": "Cadastre sua assinatura primeiro."}), 400

    cautela_id = request.form.get("cautela_id", type=int) or (request.json or {}).get("cautela_id")
    tipo_doc = request.form.get("tipo") or (request.json or {}).get("tipo", "cautela_recebimento")

    if not cautela_id:
        return jsonify({"ok": False, "erro": "cautela_id obrigatório."}), 400

    # Verifica janela de confiança
    if not janela_aberta(session):
        return jsonify({"ok": False, "precisa_senha": True}), 401

    cautela = db.session.get(Cautela, cautela_id) or abort(404)

    # Evita duplicata
    ja = AssinaturaAplicada.query.filter_by(
        cautela_id=cautela_id, papel="operador", tipo_documento=tipo_doc
    ).first()
    if ja:
        return jsonify({"ok": True, "aviso": "Já assinado."})

    ip = ip_externo(request)
    ass = AssinaturaAplicada(
        tipo_documento=tipo_doc,
        cautela_id=cautela_id,
        papel="operador",
        operador_id=current_user.id,
        imagem_base64=current_user.assinatura_base64,
        ip_origem=ip,
    )
    db.session.add(ass)
    db.session.commit()
    renovar_janela(session)

    registrar_log(
        "ASSINATURA_APLICADA",
        f"Operador assinou cautela {cautela.numero} ({tipo_doc}).",
        referencia_id=cautela_id,
    )
    return jsonify({"ok": True})


# ================================================================== #
#  RECEBEDOR ASSINA — QR gerado pelo desktop, assinatura no celular
# ================================================================== #

@bp.route("/qr-recebedor", methods=["POST"])
@login_required
def qr_recebedor():
    """Gera token + QR para o recebedor assinar no celular."""
    cautela_id = request.form.get("cautela_id", type=int)
    tipo_doc = request.form.get("tipo", "cautela_recebimento")

    if not cautela_id:
        return jsonify({"ok": False, "erro": "cautela_id obrigatório."}), 400

    cautela = db.session.get(Cautela, cautela_id) or abort(404)
    ip = ip_externo(request)
    tok = gerar_token(tipo_doc, cautela_id=cautela_id, validade_min=5, ip=ip)
    url_mobile = f"{_url_base()}{url_for('assinatura.mobile_recebedor', token=tok.token)}"
    qr_data_uri = gerar_qr_png_base64(url_mobile)

    return jsonify({
        "ok": True,
        "token": tok.token,
        "qr_data_uri": qr_data_uri,
        "url_mobile": url_mobile,
    })


@bp.route("/cautela/<int:cautela_id>/status-recebedor")
@login_required
def status_recebedor(cautela_id):
    """Polling JSON — desktop aguarda assinatura do recebedor."""
    tipo_doc = request.args.get("tipo", "cautela_recebimento")
    token_str = request.args.get("token")

    ass = AssinaturaAplicada.query.filter_by(
        cautela_id=cautela_id, papel="recebedor", tipo_documento=tipo_doc
    ).order_by(AssinaturaAplicada.id.desc()).first()

    if ass:
        return jsonify({"status": "ok", "assinado_em": ass.assinado_em.strftime("%d/%m/%Y %H:%M")})

    # Verifica se o token expirou
    if token_str:
        tok = TokenAssinatura.query.filter_by(token=token_str).first()
        if tok and datetime.utcnow() > tok.expira_em and not tok.usado:
            return jsonify({"status": "expirado"})

    return jsonify({"status": "aguardando"})


# ================================================================== #
#  MOBILE — recebedor assina
# ================================================================== #

@bp.route("/m/<token>", methods=["GET", "POST"])
@csrf.exempt
def mobile_recebedor(token):
    """Sem @login_required — acessado via QR pelo celular do recebedor."""
    tok = TokenAssinatura.query.filter_by(token=token, usado=False).first()
    if not tok:
        return render_template("assinatura/token_invalido.html", motivo="inválido ou já usado"), 400
    if datetime.utcnow() > tok.expira_em:
        return render_template("assinatura/token_invalido.html", motivo="expirado"), 400
    if not tok.cautela_id:
        return render_template("assinatura/token_invalido.html", motivo="sem cautela associada"), 400

    cautela = db.session.get(Cautela, tok.cautela_id) or abort(404)
    tipo_doc = tok.tipo  # "cautela_recebimento" | "cautela_devolucao"

    if request.method == "POST":
        imagem = (request.form.get("assinatura") or "").strip()
        if not imagem or not imagem.startswith("data:image/png;base64,"):
            return jsonify({"ok": False, "erro": "Assinatura inválida."}), 400

        ip = ip_externo(request)
        tok_consumido = consumir_token(token, ip)
        if not tok_consumido:
            return jsonify({"ok": False, "erro": "Token expirado durante envio."}), 400

        # Determina identidade do recebedor
        militar_id = None
        ext_nome = None
        ext_cpf = None
        if cautela.militar:
            militar_id = cautela.militar_id
        else:
            ext_nome = cautela.recebedor_nome_completo or cautela.recebedor_nome_guerra
            ext_cpf = cautela.recebedor_cpf

        ass = AssinaturaAplicada(
            tipo_documento=tipo_doc,
            cautela_id=cautela.id,
            papel="recebedor",
            militar_id=militar_id,
            recebedor_externo_nome=ext_nome,
            recebedor_externo_cpf=ext_cpf,
            imagem_base64=imagem,
            ip_origem=ip,
            token_id=tok_consumido.id,
        )
        db.session.add(ass)
        db.session.commit()

        registrar_log(
            "ASSINATURA_RECEBEDOR",
            f"Recebedor assinou cautela {cautela.numero} ({tipo_doc}).",
            referencia_id=cautela.id,
        )
        return jsonify({"ok": True})

    return render_template(
        "mobile/assinar_cautela.html",
        cautela=cautela,
        token=token,
        tipo_doc=tipo_doc,
    )
