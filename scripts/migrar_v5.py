"""Migracao v5 — Simplifica medidas corporais.

Troca medicoes brutas (ombro cm, cintura cm...) por tamanhos diretos:
  camisa TEXT  -- tamanho de camisa/gandola/regata/shorts TFM (PP/P/M/G/GG/XG)
  calca  TEXT  -- tamanho de calca/shorts (PP/P/M/G/GG/XG)

As colunas antigas (ombro, cintura, quadril, braco) ficam no banco
mas deixam de ser usadas pelo sistema.

Migracao de dados: converte valores existentes de ombro->camisa e
cintura->calca usando as mesmas tabelas de conversao do dashboard.

Idempotente: pode rodar varias vezes sem problema.
"""

import sqlite3
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DB_PATH = BASE_DIR / "instance" / "sismat.db"


def _ombro_tamanho(cm):
    if cm <= 40: return "PP"
    if cm <= 43: return "P"
    if cm <= 46: return "M"
    if cm <= 49: return "G"
    if cm <= 52: return "GG"
    return "XG"


def _cintura_tamanho(cm):
    if cm <= 70: return "PP"
    if cm <= 78: return "P"
    if cm <= 86: return "M"
    if cm <= 94: return "G"
    if cm <= 102: return "GG"
    return "XG"


def _safe_int(val, minv, maxv):
    try:
        v = int(str(val).strip())
        return v if minv <= v <= maxv else None
    except (TypeError, ValueError):
        return None


def migrar(con: sqlite3.Connection) -> None:
    cur = con.cursor()

    # --- 1. Adicionar colunas camisa e calca (se nao existirem) ---
    colunas = {row[1] for row in cur.execute("PRAGMA table_info(medidas)")}

    if "camisa" not in colunas:
        cur.execute("ALTER TABLE medidas ADD COLUMN camisa TEXT")
        print("[OK] Coluna 'camisa' adicionada.")
    else:
        print("[--] Coluna 'camisa' ja existe.")

    if "calca" not in colunas:
        cur.execute("ALTER TABLE medidas ADD COLUMN calca TEXT")
        print("[OK] Coluna 'calca' adicionada.")
    else:
        print("[--] Coluna 'calca' ja existe.")

    # --- 2. Migrar dados existentes de ombro->camisa e cintura->calca ---
    rows = cur.execute(
        "SELECT id, ombro, cintura, camisa, calca FROM medidas"
    ).fetchall()

    atualizados = 0
    for row_id, ombro_raw, cintura_raw, camisa_atual, calca_atual in rows:
        novo_camisa = camisa_atual
        novo_calca  = calca_atual

        # Converte ombro -> camisa apenas se camisa ainda nao foi definida
        if not camisa_atual:
            ombro = _safe_int(ombro_raw, 35, 70)
            if ombro:
                novo_camisa = _ombro_tamanho(ombro)

        # Converte cintura -> calca apenas se calca ainda nao foi definida
        if not calca_atual:
            cintura = _safe_int(cintura_raw, 50, 160)
            if cintura:
                novo_calca = _cintura_tamanho(cintura)

        if novo_camisa != camisa_atual or novo_calca != calca_atual:
            cur.execute(
                "UPDATE medidas SET camisa=?, calca=? WHERE id=?",
                (novo_camisa, novo_calca, row_id),
            )
            atualizados += 1

    if atualizados:
        print(f"[OK] {atualizados} registro(s) migrado(s) (ombro->camisa, cintura->calca).")
    else:
        print("[--] Nenhum registro precisou de conversao.")

    con.commit()
    print("\n[OK] Migracao v5 concluida.")


def main():
    if not DB_PATH.exists():
        print(f"[ERRO] Banco nao encontrado: {DB_PATH}")
        sys.exit(1)
    con = sqlite3.connect(str(DB_PATH))
    try:
        migrar(con)
    finally:
        con.close()


if __name__ == "__main__":
    main()
