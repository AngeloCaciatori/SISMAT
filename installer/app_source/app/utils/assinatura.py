"""Helpers de assinatura digital via QR Code local."""

import uuid
import segno
from datetime import datetime, timedelta

from ..models import TokenAssinatura
from ..extensions import db


def gerar_token(
    tipo: str,
    operador_id: int = None,
    cautela_id: int = None,
    documento_id: int = None,
    validade_min: int = 5,
    ip: str = None,
) -> TokenAssinatura:
    """Cria e persiste um TokenAssinatura de uso único."""
    tok = TokenAssinatura(
        token=str(uuid.uuid4()),
        tipo=tipo,
        operador_id=operador_id,
        cautela_id=cautela_id,
        documento_id=documento_id,
        expira_em=datetime.utcnow() + timedelta(minutes=validade_min),
        ip_origem=ip,
    )
    db.session.add(tok)
    db.session.commit()
    return tok


def consumir_token(token_str: str, ip: str) -> TokenAssinatura | None:
    """Valida e consome o token. Retorna None se inválido/expirado/já usado."""
    tok = TokenAssinatura.query.filter_by(token=token_str, usado=False).first()
    if not tok or datetime.utcnow() > tok.expira_em:
        return None
    tok.usado = True
    tok.usado_em = datetime.utcnow()
    tok.ip_uso = ip
    db.session.commit()
    return tok


def gerar_qr_png_base64(url: str) -> str:
    """Gera um QR code PNG e retorna como data URI base64 (offline, via segno)."""
    return segno.make(url, error="M").png_data_uri(scale=10)


def janela_aberta(session) -> bool:
    """Verifica se a janela de confiança de 15 min ainda está ativa."""
    ts = session.get("assinou_em")
    if not ts:
        return False
    try:
        dt = datetime.fromisoformat(ts)
        return (datetime.utcnow() - dt) < timedelta(minutes=15)
    except Exception:
        return False


def renovar_janela(session) -> None:
    """Renova (reset) a janela de confiança de 15 min."""
    session["assinou_em"] = datetime.utcnow().isoformat()


def precisa_assinatura(operador) -> bool:
    """Retorna True se o operador ainda não cadastrou assinatura."""
    return operador.assinatura_base64 is None


def ip_externo(request) -> str:
    """Extrai o IP real do cliente (suporte a X-Forwarded-For)."""
    return (
        request.headers.get("X-Forwarded-For", request.remote_addr or "?")
        .split(",")[0]
        .strip()
    )
