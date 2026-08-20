from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_wtf import CSRFProtect
from flask_migrate import Migrate
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

db = SQLAlchemy()
login_manager = LoginManager()
login_manager.login_view = "auth.login"
login_manager.login_message = "Connecte-toi pour accéder à cette page."
login_manager.login_message_category = "info"
csrf = CSRFProtect()
migrate = Migrate()

# Limitation de débit : protège les points d'entrée sensibles (connexion,
# inscription, commentaires, réinitialisation de mot de passe, webhook) contre
# le bourrage d'identifiants et le spam automatisé.
limiter = Limiter(
    key_func=get_remote_address,
    default_limits=[],          # aucune limite globale : appliquée route par route
    storage_uri="memory://",    # voir RATELIMIT_STORAGE_URI pour la production
)
