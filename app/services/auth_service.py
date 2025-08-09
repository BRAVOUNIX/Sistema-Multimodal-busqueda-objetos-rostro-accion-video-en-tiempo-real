# app/services/auth_service.py
import logging
from psycopg2 import DatabaseError

logger = logging.getLogger("nova.auth")

class AuthService:
    def __init__(self, db):
        self.db = db
        self.logger = logger
    
    def validate_credentials(self, username: str, password: str) -> dict:
        """Valida credenciales y retorna dict con id, username y perfil"""
        result = {
            'authenticated': False,
            'username': username,
            'profile': 1  # Default a perfil operador
        }
        
        try:
            conn = self.db.get_connection()
            if not conn:
                self.logger.error("No hay conexión a la base de datos")
                return result
                
            cursor = None
            try:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT id, perfil FROM users 
                    WHERE username = %s AND password = crypt(%s, password)
                    """, (username, password))
                
                row = cursor.fetchone()
                if row:
                    result = {
                        'authenticated': True,
                        'username': username,
                        'profile': row[1]  # Obtener el campo perfil
                    }
                
            except DatabaseError as e:
                self.logger.error(f"Error de base de datos: {str(e)}")
                conn.rollback()
            finally:
                if cursor:
                    cursor.close()
                self.db.release_connection(conn)
                
        except Exception as e:
            self.logger.error(f"Error al validar credenciales: {str(e)}", exc_info=True)
        
        return result