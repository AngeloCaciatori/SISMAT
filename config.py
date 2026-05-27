"""Configurações do SISMAT.

Para alterar a senha do administrador inicial ou outras configurações,
edite este arquivo. Ele é lido na inicialização do app.
"""

import os
import secrets
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent


class Config:
    # Chave usada para assinar sessões. Trocada automaticamente se estiver vazia.
    SECRET_KEY = os.environ.get("SISMAT_SECRET_KEY") or secrets.token_hex(32)

    # Banco SQLite local (arquivo único em instance/)
    SQLALCHEMY_DATABASE_URI = f"sqlite:///{BASE_DIR / 'instance' / 'sismat.db'}"
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # Pasta para uploads (fotos dos militares)
    UPLOAD_FOLDER = BASE_DIR / "app" / "static" / "uploads"
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16 MB
    EXTENSOES_IMAGEM = {"png", "jpg", "jpeg", "webp"}

    # Sessão
    PERMANENT_SESSION_LIFETIME = 60 * 60 * 4  # 4 horas
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"

    # Padrões institucionais
    OM_PADRAO = "Bia C AD/5"
    NOME_INSTITUICAO = "Bateria de Comando da AD/5"
    CIDADE_QUARTEL = "Curitiba/PR"

    # Rede — para servidor local na LAN
    HOST = os.environ.get("SISMAT_HOST", "0.0.0.0")  # 0.0.0.0 = qualquer PC da rede
    PORT = int(os.environ.get("SISMAT_PORT", 5000))

    # Admin inicial criado pelo init_db (TROQUE A SENHA APÓS O 1º LOGIN)
    ADMIN_INICIAL_LOGIN = "admin"
    ADMIN_INICIAL_SENHA = "sismat123"
