# app/controllers/user_controller.py
import logging
from app.services.user_service import UserService

class UserController:
    def __init__(self, db):
        self.user_service = UserService(db)
        self.db = db
        self.logger = logging.getLogger("nova.user")
    
    def list_users(self):
        """Obtiene lista de usuarios"""
        return self.user_service.list_users()
    
    def add_user(self, username: str, password: str, profile: int) -> bool:
        """Agrega un nuevo usuario"""
        if not username or not password:
            self.logger.warning("Intento de agregar usuario sin username o password")
            return False
        return self.user_service.add_user(username, password, profile)
    
    def update_user(self, user_id: int, username: str, password: str = None, profile: int = None) -> bool:
        """Actualiza un usuario existente"""
        if not user_id or not username:
            self.logger.warning("Intento de actualizar usuario sin ID o username")
            return False
        return self.user_service.update_user(user_id, username, password, profile)
    
    def delete_user(self, user_id: int) -> bool:
        """Elimina un usuario"""
        if not user_id:
            self.logger.warning("Intento de eliminar usuario sin ID")
            return False
        return self.user_service.delete_user(user_id)