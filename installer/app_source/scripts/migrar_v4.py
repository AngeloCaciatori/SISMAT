"""Migração v4 — situacao em militar + tabelas de backup.

Adiciona:
    militar.situacao        VARCHAR(20) NOT NULL DEFAULT 'ATIVO'
    militar.situacao_em     DATETIME
    militar.situacao_motivo VARCHAR(200)
    tabela backup_log
    tabela backup_config
    tabela backup_config_log

Sincroniza: militares com excluido=1 recebem situacao='EXCLUIDO' (idempotente).

Pode ser rodado múltiplas vezes sem corromper dados.
"""

import sys
from pathlib import Path
from sqlalchemy import create_engine, text, inspect

BASE_DIR = Path(__file__).resolve().parent.parent
DB_PATH = BASE_DIR / "instance" / "sismat.db"


def coluna_existe(insp, tabela: str, coluna: str) -> bool:
    return any(c["name"] == coluna for c in insp.get_columns(tabela))


def tabela_existe(insp, tabela: str) -> bool:
    return tabela in insp.get_table_names()


def main():
    if not DB_PATH.exists():
        print(f"[ERRO] Banco nao encontrado: {DB_PATH}")
        print("   Rode python scripts/init_db.py primeiro.")
        sys.exit(1)

    engine = create_engine(f"sqlite:///{DB_PATH}")
    insp = inspect(engine)

    with engine.begin() as conn:

        # ── Colunas novas em 'militar' ────────────────────────────────
        if not coluna_existe(insp, "militar", "situacao"):
            conn.execute(text(
                "ALTER TABLE militar ADD COLUMN situacao VARCHAR(20) NOT NULL DEFAULT 'ATIVO'"
            ))
            print("  [OK] militar.situacao adicionado")
        else:
            print("  [--] militar.situacao ja existe")

        if not coluna_existe(insp, "militar", "situacao_em"):
            conn.execute(text(
                "ALTER TABLE militar ADD COLUMN situacao_em DATETIME"
            ))
            print("  [OK] militar.situacao_em adicionado")
        else:
            print("  [--] militar.situacao_em ja existe")

        if not coluna_existe(insp, "militar", "situacao_motivo"):
            conn.execute(text(
                "ALTER TABLE militar ADD COLUMN situacao_motivo VARCHAR(200)"
            ))
            print("  [OK] militar.situacao_motivo adicionado")
        else:
            print("  [--] militar.situacao_motivo ja existe")

        # Sincroniza legado: excluido=1 → situacao='EXCLUIDO'
        result = conn.execute(text(
            "UPDATE militar SET situacao = 'EXCLUIDO', situacao_em = excluido_em "
            "WHERE excluido = 1 AND situacao = 'ATIVO'"
        ))
        if result.rowcount:
            print(f"  [OK] {result.rowcount} militar(es) sincronizados excluido->EXCLUIDO")
        else:
            print("  [--] Nenhum militar legado para sincronizar")

        # ── Tabela backup_log ────────────────────────────────────────
        if not tabela_existe(insp, "backup_log"):
            conn.execute(text("""
                CREATE TABLE backup_log (
                    id            INTEGER PRIMARY KEY AUTOINCREMENT,
                    arquivo       VARCHAR(200) NOT NULL,
                    tipo          VARCHAR(20)  NOT NULL,
                    tamanho_kb    REAL,
                    md5_db        VARCHAR(32),
                    ok            BOOLEAN NOT NULL DEFAULT 1,
                    erro_msg      TEXT,
                    destino_cloud VARCHAR(300),
                    cloud_ok      BOOLEAN,
                    cloud_erro    TEXT,
                    criado_em     DATETIME NOT NULL DEFAULT (datetime('now'))
                )
            """))
            print("  [OK] tabela backup_log criada")
        else:
            # Garante colunas novas (cloud) em instâncias existentes
            for col, ddl in [
                ("destino_cloud", "VARCHAR(300)"),
                ("cloud_ok",      "BOOLEAN"),
                ("cloud_erro",    "TEXT"),
            ]:
                if not coluna_existe(insp, "backup_log", col):
                    conn.execute(text(f"ALTER TABLE backup_log ADD COLUMN {col} {ddl}"))
                    print(f"  [OK] backup_log.{col} adicionado")
            print("  [--] tabela backup_log ja existe")

        # ── Tabela backup_config ─────────────────────────────────────
        if not tabela_existe(insp, "backup_config"):
            conn.execute(text("""
                CREATE TABLE backup_config (
                    id                  INTEGER PRIMARY KEY,
                    nextcloud_url       VARCHAR(300),
                    nextcloud_usuario   VARCHAR(100),
                    nextcloud_senha     VARCHAR(200),
                    nextcloud_pasta     VARCHAR(200) DEFAULT 'SISMAT',
                    cloud_ativo         BOOLEAN NOT NULL DEFAULT 0,
                    atualizado_em       DATETIME NOT NULL DEFAULT (datetime('now')),
                    atualizado_por_id   INTEGER REFERENCES operador(id)
                )
            """))
            # Insere o singleton
            conn.execute(text(
                "INSERT INTO backup_config (id, cloud_ativo, atualizado_em) "
                "VALUES (1, 0, datetime('now'))"
            ))
            print("  [OK] tabela backup_config criada (singleton id=1)")
        else:
            print("  [--] tabela backup_config ja existe")

        # ── Tabela backup_config_log ─────────────────────────────────
        if not tabela_existe(insp, "backup_config_log"):
            conn.execute(text("""
                CREATE TABLE backup_config_log (
                    id              INTEGER PRIMARY KEY AUTOINCREMENT,
                    operador_id     INTEGER REFERENCES operador(id),
                    campo           VARCHAR(50) NOT NULL,
                    valor_anterior  TEXT,
                    valor_novo      TEXT,
                    criado_em       DATETIME NOT NULL DEFAULT (datetime('now'))
                )
            """))
            print("  [OK] tabela backup_config_log criada")
        else:
            print("  [--] tabela backup_config_log ja existe")

    print("\n[OK] Migracao v4 concluida.")


if __name__ == "__main__":
    main()
