# app/services/auth_service.py
import logging
from psycopg2 import DatabaseError

logger = logging.getLogger("nova.auth")

class AuthService:
    def __init__(self, db):
        self.db = db
        self.logger = logger
    
    def validate_credentials(self, username: str, password: str) -> bool:
        """Valida las credenciales contra la base de datos"""
        try:
            # Obtener conexión
            conn = self.db.get_connection()
            if not conn:
                self.logger.error("No se pudo obtener conexión a la base de datos")
                return False
                
            cursor = None
            try:
                cursor = conn.cursor()
                
                # Consulta SQL que se ejecutará
                sql_query = """
                    SELECT id FROM users 
                    WHERE username = %s AND password = crypt(%s, password)
                    """
                params = (username, password)
                
                # Mostrar consulta SQL con parámetros (para depuración)
                debug_query = sql_query % (f"'{username}'", f"'{password}'")
                self.logger.debug(f"Ejecutando consulta SQL: {debug_query}")
                
                cursor.execute(sql_query, params)
                result = cursor.fetchone()
                
                if result:
                    self.logger.debug(f"Autenticación exitosa para usuario: {username}")
                else:
                    self.logger.debug("Credenciales no válidas")
                
                return result is not None
                
            except DatabaseError as e:
                self.logger.error(f"Error de base de datos: {str(e)}")
                conn.rollback()
                return False
            finally:
                if cursor:
                    cursor.close()
                self.db.release_connection(conn)
                
        except Exception as e:
            self.logger.error(f"Error al validar credenciales: {str(e)}", exc_info=True)
            return False