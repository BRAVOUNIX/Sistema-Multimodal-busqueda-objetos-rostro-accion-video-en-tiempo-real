# app/services/video_service.py
import cv2
import numpy as np
from ultralytics import YOLO
import threading
import pyttsx3
import speech_recognition as sr
from typing import List, Tuple, Optional, Callable
import os
from pathlib import Path

class VideoService:
    def __init__(self):
        self.camera = None
        self.window_active = False
        self.detected_objects = []
        self.model = YOLO('assets/models/yolov8n.pt')
        self.face_model = YOLO('assets/models/yolov8-face.pt')
        self.detection_mode = 'object'  # 'object' o 'face'
        self.target_object = None
        self._mask_method = 'm0'  # Usando property ahora
        self.listening = False
        self.recognizer = sr.Recognizer()
        self.voice_engine = pyttsx3.init()
        self.frame_callback = None
        self._load_emoji()  # Precargar recursos

    def _load_emoji(self):
        """Precarga el emoji para enmascaramiento"""
        self.emoji = None
        emoji_path = Path("assets/emojis/default.png")
        if emoji_path.exists():
            self.emoji = cv2.imread(str(emoji_path))

    @property
    def mask_method(self):
        return self._mask_method

    @mask_method.setter
    def mask_method(self, value):
        if value in ['m0', 'm1', 'm2', 'm3', 'm4']:
            self._mask_method = value
        else:
            raise ValueError("Método de enmascaramiento no válido")

    def set_frame_callback(self, callback: Callable):
        self.frame_callback = callback

    def set_detection_mode(self, mode: str):
        if mode in ['object', 'face']:
            self.detection_mode = mode
        else:
            raise ValueError("Modo de detección no válido")

    def set_target_object(self, object_name: str):
        self.target_object = object_name

    def start_camera(self) -> bool:
        if self.camera is None or not self.camera.isOpened():
            self.camera = cv2.VideoCapture(0)
            if self.camera.isOpened():
                self.window_active = True
                threading.Thread(
                    target=self._process_video, 
                    daemon=True,
                    name="VideoProcessingThread"
                ).start()
                return True
        return False

    def stop_camera(self):
        self.window_active = False
        if self.camera:
            self.camera.release()
            cv2.destroyAllWindows()
            self.camera = None

    def _process_video(self):
        try:
            while self.window_active:
                ret, frame = self.camera.read()
                if not ret:
                    break
                
                try:
                    processed_frame = self._process_frame(frame)
                    if self.frame_callback:
                        self.frame_callback(processed_frame)
                except Exception as e:
                    print(f"Error procesando frame: {str(e)}")
                    continue
                
                if cv2.waitKey(1) & 0xFF == ord('q'):
                    self.stop_camera()
                    break
        except Exception as e:
            print(f"Error en hilo de video: {str(e)}")

    def _process_frame(self, frame: np.ndarray) -> np.ndarray:
        if self.detection_mode == 'object':
            return self._detect_objects(frame)
        return self._detect_faces(frame)

    def _detect_objects(self, frame: np.ndarray) -> np.ndarray:
        results = self.model.predict(source=frame, save=False, verbose=False)
        self.detected_objects = []
        
        for r in results:
            for box in r.boxes:
                label = self.model.names[int(box.cls[0])]
                self.detected_objects.append(label)
                
                if self.target_object and label == self.target_object:
                    x1, y1, x2, y2 = map(int, box.xyxy[0])
                    cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 0, 255), 3)
        
        return results[0].plot()

    def _detect_faces(self, frame: np.ndarray) -> np.ndarray:
        results = self.face_model.predict(source=frame, save=False, verbose=False)
        
        for r in results:
            for box in r.boxes:
                x1, y1, x2, y2 = map(int, box.xyxy[0])
                face_roi = frame[y1:y2, x1:x2]
                
                if self.mask_method == 'm1':
                    masked = self._apply_blur(face_roi)
                elif self.mask_method == 'm2':
                    masked = self._apply_pixelation(face_roi)
                elif self.mask_method == 'm3':
                    masked = self._apply_black_box(face_roi)
                elif self.mask_method == 'm4':
                    masked = self._apply_emoji(face_roi)
                else:
                    masked = face_roi  # Sin enmascaramiento
                
                frame[y1:y2, x1:x2] = masked
        
        return frame

    # Métodos de enmascaramiento
    def _apply_blur(self, face_roi: np.ndarray) -> np.ndarray:
        """Aplica desenfoque gaussiano"""
        return cv2.GaussianBlur(face_roi, (99, 99), 30)

    def _apply_pixelation(self, face_roi: np.ndarray) -> np.ndarray:
        """Aplica efecto pixelado"""
        (h, w) = face_roi.shape[:2]
        temp = cv2.resize(face_roi, (16, 16), interpolation=cv2.INTER_LINEAR)
        return cv2.resize(temp, (w, h), interpolation=cv2.INTER_NEAREST)

    def _apply_black_box(self, face_roi: np.ndarray) -> np.ndarray:
        """Aplica caja negra"""
        return np.zeros_like(face_roi)

    def _apply_emoji(self, face_roi: np.ndarray) -> np.ndarray:
        """Aplica emoji precargado"""
        if self.emoji is not None:
            h, w = face_roi.shape[:2]
            emoji_resized = cv2.resize(self.emoji, (w, h))
            return emoji_resized
        return self._apply_black_box(face_roi)

    # Métodos de voz (existente)
    def toggle_listening(self):
        """Alterna el modo de escucha por voz"""
        if not self.listening:
            try:
                with sr.Microphone() as source:
                    self.recognizer.adjust_for_ambient_noise(source)
                    audio = self.recognizer.listen(source, timeout=5)
                    text = self.recognizer.recognize_google(audio, language='es-ES')
                    return True, text
            except Exception as e:
                return False, f"Error en reconocimiento de voz: {str(e)}"
        return False, "Escucha ya activa"

    def process_command(self, command: str) -> str:
        """Procesa comandos básicos"""
        command = command.lower()
        if "detener" in command or "parar" in command:
            self.stop_camera()
            return "Video detenido"
        elif "iniciar" in command or "comenzar" in command:
            if self.start_camera():
                return "Video iniciado"
            return "No se pudo iniciar el video"
        return f"Comando recibido: {command}"

    def speak(self, text: str):
        """Reproduce texto por voz"""
        self.voice_engine.say(text)
        self.voice_engine.runAndWait()