# -*- coding: utf-8 -*-
"""Migracao v5 - Simplifica medidas corporais.

Troca medicoes brutas (ombro, cintura) por tamanhos diretos:
  camisa TEXT  -- PP/P/M/G/GG/XG
  calca  TEXT  -- PP/P/M/G/GG/XG

As colunas antigas (ombro, cintura, quadril, braco) podem ou nao existir,
dependendo se a instalacao e nova ou veio de uma versao mais antiga.

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


def migrar(con):
    cur = con.cursor()

    # 1. Adicionar camisa/calca se necessario
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

    # 2. Migrar dados legados, SE existirem
    colunas_atualizadas = {row[1] for row in cur.execute("PRAGMA table_info(medidas)")}
    tem_legado = "ombro" in colunas_atualizadas and "cintura" in colunas_atualizadas

    if not tem_legado:
        print("[--] Colunas legadas (ombro/cintura) nao existem - instalacao nova, sem migracao de dados.")
        con.commit()
        print("[OK] Migracao v5 concluida.")
        return

    rows = cur.execute(
        "SELECT id, ombro, cintura, camisa, calca FROM medidas"
    ).fetchall()

    atualizados = 0
    for row_id, ombro_raw, cintura_raw, camisa_atual, calca_atual in rows:
        novo_camisa = camisa_atual
        novo_calca = calca_atual

        if not camisa_atual:
            ombro = _safe_int(ombro_raw, 35, 70)
            if ombro:
                novo_camisa = _ombro_tamanho(ombro)

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
        print(f"[OK] {atualizados} registro(s) migrado(s) de ombro/cintura para camisa/calca.")
    else:
        print("[--] Nenhum registro precisou de conversao.")

    con.commit()
    print("[OK] Migracao v5 concluida.")


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
