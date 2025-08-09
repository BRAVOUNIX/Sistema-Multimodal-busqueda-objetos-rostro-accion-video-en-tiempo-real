# app/controllers/auth_controller.py
import logging
from app.services.auth_service import AuthService

class AuthController:
    def __init__(self, db):
        self.auth_service = AuthService(db)
        self.db = db
        self.logger = logging.getLogger("nova.auth")
    
    def authenticate(self, username: str, password: str) -> dict:
        """Autentica usuario y retorna dict con resultados"""
        try:
            self.logger.info(f"Intento de login para usuario: {username}")
            return self.auth_service.validate_credentials(username, password)
        except Exception as e:
            self.logger.error(f"Error en autenticación: {str(e)}", exc_info=True)
            return {
                'authenticated': False,
                'username': username,
                'profile': 1
            }
    
    def ensure_connection(self):
        """Verifica conexión a la base de datos"""
        try:
            if not self.db.connection_pool:
                return False
            self.db.connection = self.db.get_connection()
            return self.db.connection is not None
        except Exception as e:
            self.logger.error(f"Error al verificar conexión: {str(e)}")
            return False