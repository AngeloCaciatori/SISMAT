"""app/utils — pacote de utilitários compartilhados.

Re-exporta registrar_log para manter compatibilidade com os imports existentes:
    from ..utils import registrar_log
"""

from datetime import datetime
from flask_login import current_user

from ..extensions import db
from ..models import LogAuditoria


def registrar_log(acao: str, descricao: str, referencia_id: int = None) -> None:
    """Registra uma ação no log de auditoria.

    Deve ser chamado APÓS db.session.commit() (ou dentro da mesma transação,
    seguido de commit). Nunca deixa o log quebrar a operação principal.
    """
    try:
        op_id = current_user.id if current_user.is_authenticated else None
        entrada = LogAuditoria(
            operador_id=op_id,
            acao=acao,
            descricao=descricao,
            referencia_id=referencia_id,
            criado_em=datetime.utcnow(),
        )
        db.session.add(entrada)
        db.session.commit()
    except Exception:
        db.session.rollback()
