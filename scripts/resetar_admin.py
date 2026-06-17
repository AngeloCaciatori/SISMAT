# -*- coding: utf-8 -*-
"""Cria ou reseta a senha do admin para o padrao 'sismat123'.

Se o admin nao existir (init_db.py falhou), CRIA.
Se existir, reseta a senha e limpa a flag de senha temporaria.

Uso emergencial. Nao toca em outros dados.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app import create_app
from app.extensions import db
from app.models import Operador, NIVEL_ADMIN

SENHA_NOVA = "sismat123"
LOGIN_ADMIN = "admin"

app = create_app()
with app.app_context():
    admin = Operador.query.filter_by(login=LOGIN_ADMIN).first()

    if admin:
        print(f"[OK] Admin '{LOGIN_ADMIN}' encontrado - resetando senha.")
        admin.definir_senha(SENHA_NOVA)
        admin.senha_temporaria = False
        admin.ativo = True
        acao = "reset"
    else:
        print(f"[!] Admin '{LOGIN_ADMIN}' nao existe - criando agora.")
        admin = Operador(
            login=LOGIN_ADMIN,
            nivel_seguranca=NIVEL_ADMIN,
            secao="Reserva de Material",
            ativo=True,
            senha_temporaria=False,
        )
        admin.definir_senha(SENHA_NOVA)
        db.session.add(admin)
        acao = "criado"

    db.session.commit()

    print("=" * 50)
    print(f"  ADMIN {'CRIADO' if acao == 'criado' else 'RESETADO'} COM SUCESSO")
    print("=" * 50)
    print(f"  Login: {LOGIN_ADMIN}")
    print(f"  Senha: {SENHA_NOVA}")
    print("=" * 50)
