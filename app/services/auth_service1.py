# app/services/auth_service.py
import logging

class AuthService:
    def __init__(self, db):
        self.db = db
        self.logger = logging.getLogger("nova.auth")

    def validate_credentials(self, username: str, password: str) -> bool:
        """Valida las credenciales contra la base de datos"""
        if not self.db.connection:
            self.logger.error("No hay conexión a la base de datos")
            return False
            
        cursor = None
        try:
            # Crear nuevo cursor para asegurar transacción limpia
            cursor = self.db.connection.cursor()
            
            # Reiniciar cualquier transacción previa fallida
            self.db.connection.rollback()
            
            # Consulta segura con parámetros
            cursor.execute(
                "SELECT id FROM users WHERE username = %s AND password = crypt(%s, password);",
                (username, password)
            )
            return cursor.fetchone() is not None
            
        except Exception as e:
            self.logger.error(f"Error al validar credenciales: {str(e)}", exc_info=True)
            # Asegurar rollback en caso de error
            if self.db.connection:
                self.db.connection.rollback()
            return False
        finally:
            # Cerrar cursor siempre
            if cursor:
                cursor.close()