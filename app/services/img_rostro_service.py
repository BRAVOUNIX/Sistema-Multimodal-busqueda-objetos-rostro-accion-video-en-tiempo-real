# app/services/img_rostro_service.py
import logging
import os
import shutil
from psycopg2 import DatabaseError
from pathlib import Path

logger = logging.getLogger("nova.img_rostro")

class ImgRostroService:
    def __init__(self, db):
        self.db = db
        self.logger = logger
        self.known_faces_dir = Path("VISION_LLM/known_faces")
        self.known_faces_dir.mkdir(parents=True, exist_ok=True)
    
    def list_rostros(self):
        """Lista todos los rostros registrados"""
        rostros = []
        try:
            conn = self.db.get_connection()
            if not conn:
                self.logger.error("No hay conexión a la base de datos")
                return rostros
                
            cursor = None
            try:
                cursor = conn.cursor()
                cursor.execute("SELECT id_rostro, nombre, alias FROM buscar_rostro ORDER BY id_rostro")
                rostros = [{'id_rostro': row[0], 'nombre': row[1], 'alias': row[2]} for row in cursor.fetchall()]
            except DatabaseError as e:
                self.logger.error(f"Error al listar rostros: {str(e)}")
                conn.rollback()
            finally:
                if cursor:
                    cursor.close()
                self.db.release_connection(conn)
                
        except Exception as e:
            self.logger.error(f"Error inesperado al listar rostros: {str(e)}", exc_info=True)
        
        return rostros
    
    def add_rostro(self, nombre: str, alias: str, imagenes: list) -> bool:
        """Agrega un nuevo rostro con sus imágenes"""
        try:
            conn = self.db.get_connection()
            if not conn:
                self.logger.error("No hay conexión a la base de datos")
                return False
                
            cursor = None
            try:
                cursor = conn.cursor()
                
                # Insertar en tabla buscar_rostro
                cursor.execute(
                    "INSERT INTO buscar_rostro (nombre, alias) VALUES (%s, %s) RETURNING id_rostro",
                    (nombre, alias))
                
                id_rostro = cursor.fetchone()[0]
                
                # Guardar imágenes en sistema de archivos y en BD
                for img_path in imagenes:
                    img_name = f"{alias}_{Path(img_path).name}"
                    dest_path = self.known_faces_dir / img_name
                    
                    # Copiar imagen al directorio de rostros conocidos
                    shutil.copy(img_path, dest_path)
                    
                    # Insertar en tabla imagen
                    cursor.execute(
                        "INSERT INTO imagen (id_rostro, imagen) VALUES (%s, %s)",
                        (id_rostro, str(dest_path)))
                
                conn.commit()
                return True
                
            except DatabaseError as e:
                self.logger.error(f"Error al agregar rostro: {str(e)}")
                conn.rollback()
                return False
            finally:
                if cursor:
                    cursor.close()
                self.db.release_connection(conn)
                
        except Exception as e:
            self.logger.error(f"Error inesperado al agregar rostro: {str(e)}", exc_info=True)
            return False
    
    def update_rostro(self, id_rostro: int, nombre: str, alias: str) -> bool:
        """Actualiza un rostro existente"""
        try:
            conn = self.db.get_connection()
            if not conn:
                self.logger.error("No hay conexión a la base de datos")
                return False
                
            cursor = None
            try:
                cursor = conn.cursor()
                cursor.execute(
                    "UPDATE buscar_rostro SET nombre = %s, alias = %s WHERE id_rostro = %s",
                    (nombre, alias, id_rostro))
                conn.commit()
                return cursor.rowcount > 0
            except DatabaseError as e:
                self.logger.error(f"Error al actualizar rostro: {str(e)}")
                conn.rollback()
                return False
            finally:
                if cursor:
                    cursor.close()
                self.db.release_connection(conn)
                
        except Exception as e:
            self.logger.error(f"Error inesperado al actualizar rostro: {str(e)}", exc_info=True)
            return False
    
    def delete_rostro(self, id_rostro: int) -> bool:
        """Elimina un rostro y sus imágenes asociadas"""
        try:
            conn = self.db.get_connection()
            if not conn:
                self.logger.error("No hay conexión a la base de datos")
                return False
                
            cursor = None
            try:
                cursor = conn.cursor()
                
                # Obtener imágenes asociadas
                cursor.execute("SELECT imagen FROM imagen WHERE id_rostro = %s", (id_rostro,))
                imagenes = [row[0] for row in cursor.fetchall()]
                
                # Eliminar de tabla imagen
                cursor.execute("DELETE FROM imagen WHERE id_rostro = %s", (id_rostro,))
                
                # Eliminar de tabla buscar_rostro
                cursor.execute("DELETE FROM buscar_rostro WHERE id_rostro = %s", (id_rostro,))
                
                conn.commit()
                
                # Eliminar archivos de imágenes
                for img_path in imagenes:
                    try:
                        os.remove(img_path)
                    except OSError as e:
                        self.logger.warning(f"No se pudo eliminar imagen {img_path}: {str(e)}")
                
                return True
                
            except DatabaseError as e:
                self.logger.error(f"Error al eliminar rostro: {str(e)}")
                conn.rollback()
                return False
            finally:
                if cursor:
                    cursor.close()
                self.db.release_connection(conn)
                
        except Exception as e:
            self.logger.error(f"Error inesperado al eliminar rostro: {str(e)}", exc_info=True)
            return False
    
    def get_rostro_by_id(self, id_rostro: int):
        """Obtiene un rostro por su ID"""
        try:
            conn = self.db.get_connection()
            if not conn:
                self.logger.error("No hay conexión a la base de datos")
                return None
                
            cursor = None
            try:
                cursor = conn.cursor()
                cursor.execute("SELECT id_rostro, nombre, alias FROM buscar_rostro WHERE id_rostro = %s", (id_rostro,))
                row = cursor.fetchone()
                return {'id_rostro': row[0], 'nombre': row[1], 'alias': row[2]} if row else None
            except DatabaseError as e:
                self.logger.error(f"Error al obtener rostro: {str(e)}")
                conn.rollback()
                return None
            finally:
                if cursor:
                    cursor.close()
                self.db.release_connection(conn)
                
        except Exception as e:
            self.logger.error(f"Error inesperado al obtener rostro: {str(e)}", exc_info=True)
            return None
    
    def get_imagenes_by_rostro(self, id_rostro: int):
        """Obtiene las imágenes asociadas a un rostro"""
        imagenes = []
        try:
            conn = self.db.get_connection()
            if not conn:
                self.logger.error("No hay conexión a la base de datos")
                return imagenes
                
            cursor = None
            try:
                cursor = conn.cursor()
                cursor.execute("SELECT id, imagen FROM imagen WHERE id_rostro = %s", (id_rostro,))
                imagenes = [{'id': row[0], 'imagen': row[1]} for row in cursor.fetchall()]
            except DatabaseError as e:
                self.logger.error(f"Error al obtener imágenes: {str(e)}")
                conn.rollback()
            finally:
                if cursor:
                    cursor.close()
                self.db.release_connection(conn)
                
        except Exception as e:
            self.logger.error(f"Error inesperado al obtener imágenes: {str(e)}", exc_info=True)
        
        return imagenes