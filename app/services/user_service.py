# app/services/user_service.py
import logging
from psycopg2 import DatabaseError

logger = logging.getLogger("nova.user")

class UserService:
    def __init__(self, db):
        self.db = db
        self.logger = logger
    
    def list_users(self):
        """Lista todos los usuarios"""
        users = []
        try:
            conn = self.db.get_connection()
            if not conn:
                self.logger.error("No hay conexión a la base de datos")
                return users
                
            cursor = None
            try:
                cursor = conn.cursor()
                cursor.execute("SELECT id, username, perfil FROM users ORDER BY id")
                users = [{'id': row[0], 'username': row[1], 'profile': row[2]} for row in cursor.fetchall()]
            except DatabaseError as e:
                self.logger.error(f"Error al listar usuarios: {str(e)}")
                conn.rollback()
            finally:
                if cursor:
                    cursor.close()
                self.db.release_connection(conn)
                
        except Exception as e:
            self.logger.error(f"Error inesperado al listar usuarios: {str(e)}", exc_info=True)
        
        return users
    
    def add_user(self, username: str, password: str, profile: int) -> bool:
        """Agrega un nuevo usuario"""
        try:
            conn = self.db.get_connection()
            if not conn:
                self.logger.error("No hay conexión a la base de datos")
                return False
                
            cursor = None
            try:
                cursor = conn.cursor()
                cursor.execute(
                    "INSERT INTO users (username, password, perfil) VALUES (%s, crypt(%s, gen_salt('bf')), %s)",
                    (username, password, profile))
                conn.commit()
                return True
            except DatabaseError as e:
                self.logger.error(f"Error al agregar usuario: {str(e)}")
                conn.rollback()
                return False
            finally:
                if cursor:
                    cursor.close()
                self.db.release_connection(conn)
                
        except Exception as e:
            self.logger.error(f"Error inesperado al agregar usuario: {str(e)}", exc_info=True)
            return False
    
    def update_user(self, user_id: int, username: str, password: str = None, profile: int = None) -> bool:
        """Actualiza un usuario existente"""
        try:
            conn = self.db.get_connection()
            if not conn:
                self.logger.error("No hay conexión a la base de datos")
                return False
                
            cursor = None
            try:
                cursor = conn.cursor()
                if password:
                    cursor.execute(
                        "UPDATE users SET username = %s, password = crypt(%s, gen_salt('bf')), perfil = %s WHERE id = %s",
                        (username, password, profile, user_id))
                else:
                    cursor.execute(
                        "UPDATE users SET username = %s, perfil = %s WHERE id = %s",
                        (username, profile, user_id))
                conn.commit()
                return cursor.rowcount > 0
            except DatabaseError as e:
                self.logger.error(f"Error al actualizar usuario: {str(e)}")
                conn.rollback()
                return False
            finally:
                if cursor:
                    cursor.close()
                self.db.release_connection(conn)
                
        except Exception as e:
            self.logger.error(f"Error inesperado al actualizar usuario: {str(e)}", exc_info=True)
            return False
    
    def delete_user(self, user_id: int) -> bool:
        """Elimina un usuario"""
        try:
            conn = self.db.get_connection()
            if not conn:
                self.logger.error("No hay conexión a la base de datos")
                return False
                
            cursor = None
            try:
                cursor = conn.cursor()
                cursor.execute("DELETE FROM users WHERE id = %s", (user_id,))
                conn.commit()
                return cursor.rowcount > 0
            except DatabaseError as e:
                self.logger.error(f"Error al eliminar usuario: {str(e)}")
                conn.rollback()
                return False
            finally:
                if cursor:
                    cursor.close()
                self.db.release_connection(conn)
                
        except Exception as e:
            self.logger.error(f"Error inesperado al eliminar usuario: {str(e)}", exc_info=True)
            return False