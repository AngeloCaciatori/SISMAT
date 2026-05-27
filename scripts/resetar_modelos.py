"""
Utilitário: recria/atualiza os modelos padrão de documentação no banco.
Remove modelos padrão obsoletos e garante que só os ativos existam.

Execute uma vez após atualizar o sistema:

    python scripts/resetar_modelos.py
"""

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from scripts.init_db import TEMPLATE_FIDU_PADRAO
from app import create_app
from app.extensions import db
from app.models import ModeloDocumento

MODELOS = [
    ("Ficha de Cautela (FIDU)", TEMPLATE_FIDU_PADRAO),
]

NOMES_ATIVOS = {nome for nome, _ in MODELOS}


def main():
    app = create_app()
    with app.app_context():

        # Remover modelos padrão que não estão mais na lista
        obsoletos = ModeloDocumento.query.filter_by(padrao=True).all()
        for m in obsoletos:
            if m.nome not in NOMES_ATIVOS:
                print(f"[REMOVIDO] Modelo obsoleto: {m.nome!r}")
                db.session.delete(m)
        db.session.commit()

        # Criar ou atualizar os modelos ativos
        for nome, html in MODELOS:
            m = ModeloDocumento.query.filter_by(padrao=True, nome=nome).first()
            if m:
                m.conteudo_html = html
                print(f"[OK] Modelo atualizado: {nome!r}")
            else:
                db.session.add(ModeloDocumento(nome=nome, conteudo_html=html, padrao=True))
                print(f"[OK] Modelo criado:     {nome!r}")
        db.session.commit()

        print("\nModelos padrão no banco:")
        for m in ModeloDocumento.query.filter_by(padrao=True).all():
            print(f"  - [{m.id}] {m.nome}")


if __name__ == "__main__":
    main()
