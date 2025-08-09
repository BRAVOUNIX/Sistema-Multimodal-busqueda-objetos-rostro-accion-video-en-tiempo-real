# app/controllers/img_rostro_controller.py
import logging
from app.services.img_rostro_service import ImgRostroService

class ImgRostroController:
    def __init__(self, db):
        self.img_rostro_service = ImgRostroService(db)
        self.db = db
        self.logger = logging.getLogger("nova.img_rostro")
    
    def list_rostros(self):
        """Obtiene lista de rostros registrados"""
        return self.img_rostro_service.list_rostros()
    
    def add_rostro(self, nombre: str, alias: str, imagenes: list) -> bool:
        """Agrega un nuevo rostro con sus imágenes"""
        if not nombre or not alias or not imagenes:
            self.logger.warning("Intento de agregar rostro sin datos completos")
            return False
        return self.img_rostro_service.add_rostro(nombre, alias, imagenes)
    
    def update_rostro(self, id_rostro: int, nombre: str, alias: str) -> bool:
        """Actualiza un rostro existente"""
        if not id_rostro or not nombre or not alias:
            self.logger.warning("Intento de actualizar rostro sin datos completos")
            return False
        return self.img_rostro_service.update_rostro(id_rostro, nombre, alias)
    
    def delete_rostro(self, id_rostro: int) -> bool:
        """Elimina un rostro y sus imágenes asociadas"""
        if not id_rostro:
            self.logger.warning("Intento de eliminar rostro sin ID")
            return False
        return self.img_rostro_service.delete_rostro(id_rostro)
    
    def get_rostro_by_id(self, id_rostro: int):
        """Obtiene un rostro por su ID"""
        return self.img_rostro_service.get_rostro_by_id(id_rostro)
    
    def get_imagenes_by_rostro(self, id_rostro: int):
        """Obtiene las imágenes asociadas a un rostro"""
        return self.img_rostro_service.get_imagenes_by_rostro(id_rostro)