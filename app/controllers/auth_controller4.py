# app/controllers/auth_controller.py
import logging
from app.services.auth_service import AuthService

class AuthController:
    def __init__(self, db):
        self.auth_service = AuthService(db)
        self.db = db
        self.logger = logging.getLogger("nova.auth")
    
    def authenticate(self, username: str, password: str) -> bool:
        try:
            self.logger.info(f"Intento de login para usuario: {username}")
            return self.auth_service.validate_credentials(username, password)
        except Exception as e:
            self.logger.error(f"Error en autenticación: {str(e)}", exc_info=True)
            return False
    
    def ensure_connection(self):
        """Verifica y establece conexión a la base de datos"""
        try:
            if not self.db.connection_pool:
                return False
            self.db.connection = self.db.get_connection()
            return self.db.connection is not None
        except Exception as e:
            self.logger.error(f"Error al verificar conexión: {str(e)}")
            return False