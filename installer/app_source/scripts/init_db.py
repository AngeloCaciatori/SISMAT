# -*- coding: utf-8 -*-
"""Inicializa o banco SQLite do SISMAT.

Cria todas as tabelas e o usuario administrador inicial.
Executar UMA VEZ antes do primeiro uso:

    python scripts/init_db.py

Para resetar tudo (apaga banco e recria):

    python scripts/init_db.py --reset
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app import create_app
from app.extensions import db
from app.models import Operador, NIVEL_ADMIN, ModeloDocumento
from config import Config


TEMPLATE_FIDU_PADRAO = r"""
<div style="text-align:center; font-family:'Times New Roman',serif; margin-bottom:8px;">
  <strong style="font-size:17pt;">{{NOME_INSTITUICAO}}</strong><br>
  <em style="font-size:13pt;">Ficha Individual de Distribuicao de Uniformes (FIDU)</em><br>
  <span style="font-size:10pt;">Cautela No {{CAUTELA_NUMERO}} - {{CAUTELA_DATA}}</span>
</div>
<hr style="border:none; border-top:2px solid #000; margin:10px 0;">
<table style="width:100%; border-collapse:collapse; margin-bottom:12px;">
  <tr>
    <td style="border:1px solid #000; padding:6px 10px; font-weight:bold; width:90px;">MILITAR</td>
    <td style="border:1px solid #000; padding:6px 10px; font-weight:bold; width:90px;">{{MILITAR_GRADUACAO}}</td>
    <td style="border:1px solid #000; padding:6px 10px; font-weight:bold;">{{MILITAR_NOME}}</td>
    <td style="border:1px solid #000; padding:6px 10px; width:180px;">CPF: {{MILITAR_CPF}}</td>
  </tr>
</table>
<p style="text-align:center; font-weight:bold; font-size:12pt; border-top:1px solid #000;
   border-bottom:1px solid #000; padding:4px; margin:10px 0;">
  1. FARDAMENTO / EQUIPAMENTO / MATERIAL / OUTROS
</p>
{{ITENS_LISTA}}
<br>
<p style="font-size:10pt; margin:16px 0;">[Declaro que recebi o material acima especificado sem
alteracao, e estou ciente que deverei restituir ou indenizar qualquer material extraviado sob
minha responsabilidade]</p>
<p style="text-align:center; margin:20px 0;">
  Quartel em {{CIDADE_QUARTEL}}, {{DATA_HOJE}}
</p>
<br><br>
<p style="text-align:center; font-style:italic; margin-top:40px;">
  _______________________________________________<br>
  <strong>{{MILITAR_NOME}}</strong> - {{MILITAR_GRADUACAO}}
</p>
""".strip()


def reset(app):
    print("[!] Resetando banco - apagando todas as tabelas...")
    with app.app_context():
        db.drop_all()
    print("[OK] Tabelas removidas.")


def init(app):
    with app.app_context():
        print("[--] Criando tabelas...")
        db.create_all()
        print("[OK] Tabelas criadas.")

        login = Config.ADMIN_INICIAL_LOGIN
        if Operador.query.filter_by(login=login).first():
            print(f"[OK] Admin '{login}' ja existe. Pulando.")
        else:
            admin = Operador(
                login=login,
                nivel_seguranca=NIVEL_ADMIN,
                secao="Reserva de Material",
                ativo=True,
                senha_temporaria=True,
            )
            admin.definir_senha(Config.ADMIN_INICIAL_SENHA)
            db.session.add(admin)
            db.session.commit()
            print(f"[OK] Admin '{login}' criado (senha inicial: '{Config.ADMIN_INICIAL_SENHA}')")
            print("  [!] TROQUE A SENHA APOS O PRIMEIRO LOGIN.")

        _modelos_padrao = [
            ("Ficha de Cautela (FIDU)", TEMPLATE_FIDU_PADRAO),
        ]
        for nome_modelo, html in _modelos_padrao:
            m = ModeloDocumento.query.filter_by(padrao=True, nome=nome_modelo).first()
            if m:
                m.conteudo_html = html
                print(f"Modelo '{nome_modelo}' atualizado.")
            else:
                db.session.add(ModeloDocumento(nome=nome_modelo, conteudo_html=html, padrao=True))
                print(f"Modelo '{nome_modelo}' criado.")
        db.session.commit()
        print("Modelos de documento OK.")


if __name__ == "__main__":
    _app = create_app()
    if "--reset" in sys.argv:
        reset(_app)
    init(_app)
