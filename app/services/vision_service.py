import cv2
import numpy as np
from ultralytics import YOLO
from typing import List
import logging

logger = logging.getLogger("nova.vision")

class VisionService:
    def __init__(self):
        try:
            logger.info("Inicializando VisionService")
            self.object_model = YOLO('assets/models/yolov8n.pt')
            self.face_model = YOLO('assets/models/yolov8-face.pt')
            logger.info("Modelos YOLO cargados exitosamente")
        except Exception as e:
            logger.error(f"Error al cargar modelos YOLO: {str(e)}")
            raise
    
    def detect_objects(self, frame: np.ndarray) -> List[str]:
        try:
            logger.debug("Iniciando detección de objetos")
            results = self.object_model(frame)
            detected = [self.object_model.names[int(box.cls)] for box in results[0].boxes]
            logger.debug(f"Objetos detectados: {detected}")
            return detected
        except Exception as e:
            logger.error(f"Error en detección de objetos: {str(e)}", exc_info=True)
            return []