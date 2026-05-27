"""Extensões do Flask (instâncias compartilhadas).

Mantemos as instâncias separadas do app factory para evitar import circular.
"""

from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_wtf import CSRFProtect

db = SQLAlchemy()
login_manager = LoginManager()
csrf = CSRFProtect()

# Configuração padrão do login manager
login_manager.login_view = "auth.login"
login_manager.login_message = "Faça login para acessar o sistema."
login_manager.login_message_category = "warning"
