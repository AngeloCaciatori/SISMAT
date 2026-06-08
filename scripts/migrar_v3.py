"""Migração v3 — assinatura digital.

Adiciona:
  - operador.assinatura_base64  (TEXT)
  - operador.assinatura_cadastrada_em  (DATETIME)
  - tabela token_assinatura
  - tabela assinatura_aplicada

Idempotente: pode rodar várias vezes sem erro.
"""

import sys
import os

# Garante que o pacote app está no path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from sqlalchemy import text
from app import create_app
from app.extensions import db


def _add_column_if_missing(conn, table, column, definition):
    """Tenta fazer ALTER TABLE ADD COLUMN; ignora se já existir."""
    try:
        conn.execute(text(f"ALTER TABLE {table} ADD COLUMN {column} {definition}"))
        print(f"  + {table}.{column} adicionada.")
    except Exception as e:
        if "duplicate column" in str(e).lower() or "already exists" in str(e).lower():
            print(f"  . {table}.{column} já existe — ok.")
        else:
            raise


def migrar():
    app = create_app()
    with app.app_context():
        with db.engine.connect() as conn:
            print("=== Migração v3: assinatura digital ===")

            # 1. Colunas novas em operador
            _add_column_if_missing(conn, "operador", "assinatura_base64", "TEXT")
            _add_column_if_missing(conn, "operador", "assinatura_cadastrada_em", "DATETIME")

            # 2. Tabela token_assinatura
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS token_assinatura (
                    id              INTEGER PRIMARY KEY AUTOINCREMENT,
                    token           VARCHAR(36)  NOT NULL UNIQUE,
                    tipo            VARCHAR(40)  NOT NULL,
                    operador_id     INTEGER      REFERENCES operador(id),
                    cautela_id      INTEGER      REFERENCES cautela(id),
                    documento_id    INTEGER,
                    criado_em       DATETIME     DEFAULT CURRENT_TIMESTAMP,
                    expira_em       DATETIME     NOT NULL,
                    usado           BOOLEAN      DEFAULT 0,
                    usado_em        DATETIME,
                    ip_origem       VARCHAR(45),
                    ip_uso          VARCHAR(45)
                )
            """))
            print("  . token_assinatura criada/verificada.")

            # 3. Tabela assinatura_aplicada
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS assinatura_aplicada (
                    id                      INTEGER PRIMARY KEY AUTOINCREMENT,
                    tipo_documento          VARCHAR(40)  NOT NULL,
                    cautela_id              INTEGER      REFERENCES cautela(id),
                    documento_id            INTEGER,
                    papel                   VARCHAR(20)  NOT NULL,
                    operador_id             INTEGER      REFERENCES operador(id),
                    militar_id              INTEGER      REFERENCES militar(id),
                    recebedor_externo_nome  VARCHAR(200),
                    recebedor_externo_cpf   VARCHAR(20),
                    imagem_base64           TEXT         NOT NULL,
                    assinado_em             DATETIME     DEFAULT CURRENT_TIMESTAMP NOT NULL,
                    ip_origem               VARCHAR(45)  NOT NULL,
                    token_id                INTEGER      REFERENCES token_assinatura(id)
                )
            """))
            print("  . assinatura_aplicada criada/verificada.")

            conn.commit()

        print("=== Migração v3 concluída. ===")


if __name__ == "__main__":
    migrar()
