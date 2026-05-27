"""Migração v2: adiciona coluna 'excluido_em' à tabela militar.

Para usuários que já rodaram o sistema anteriormente. Sem perda de dados.

Uso:
    python scripts/migrar_v2.py
"""

import sqlite3
import sys
from pathlib import Path
from datetime import datetime

BASE_DIR = Path(__file__).resolve().parent.parent
DB = BASE_DIR / "instance" / "sismat.db"


def main():
    if not DB.exists():
        print(f"❌ Banco não encontrado: {DB}")
        print("   Rode init_db.py primeiro.")
        sys.exit(1)

    conn = sqlite3.connect(DB)
    cur = conn.cursor()

    # Verifica colunas existentes em militar
    cur.execute("PRAGMA table_info(militar)")
    colunas = {row[1] for row in cur.fetchall()}

    mudancas = []

    if "excluido_em" not in colunas:
        print("▶ Adicionando coluna 'excluido_em'...")
        cur.execute("ALTER TABLE militar ADD COLUMN excluido_em DATETIME")
        # Para registros já excluídos, usa atualizado_em como aproximação
        cur.execute(
            "UPDATE militar SET excluido_em = atualizado_em "
            "WHERE excluido = 1 AND excluido_em IS NULL"
        )
        mudancas.append("excluido_em adicionada")
    else:
        print("✓ Coluna 'excluido_em' já existe.")

    # Permite graduacao e nome_guerra serem NULL (em SQLite, recriar tabela seria caro;
    # como o ALTER TABLE do SQLite é limitado, contornamos via aplicação — modelos já permitem None)

    conn.commit()
    conn.close()

    if mudancas:
        print(f"\n✓ Migração concluída. Mudanças: {', '.join(mudancas)}")
    else:
        print("\n✓ Banco já está atualizado.")


if __name__ == "__main__":
    main()
