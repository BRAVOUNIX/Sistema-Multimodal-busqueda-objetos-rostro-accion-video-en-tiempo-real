import sys
import cv2
import torch
import numpy as np
from ultralytics import YOLO
from facenet_pytorch import InceptionResnetV1, fixed_image_standardization
from torchvision import transforms
from scipy.spatial.distance import cosine
import os
from PIL import Image
import time
import pyttsx3
import speech_recognition as sr
import threading
import yt_dlp as youtube_dl
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QVBoxLayout, QHBoxLayout, 
    QWidget, QTextEdit, QPushButton, QLabel, QFrame, 
    QInputDialog, QCheckBox
)
from PyQt6.QtCore import Qt, QTimer, pyqtSignal, QObject, QEvent
from PyQt6.QtGui import QImage, QPixmap

class VideoStream(QObject):
    update_frame_signal = pyqtSignal(QImage)
    
    def __init__(self):
        super().__init__()
        self.camara = None
        self.ventana_activa = False
        self.cerrar_todo = False
        self.modo_rostros = False
        self.video_source = 0
        self.last_frame_time = 0
        self.frame_interval = 0.2
        self.target_width = 640
        self.target_height = 480
        self.mostrar_detecciones = True
        
        # Configuración inicial
        print("[INFO] Inicializando sistema de reconocimiento facial...")
        
        # 1. Cargar YOLOv8-face
        print("[INFO] Cargando modelo YOLOv8-face...")
        self.yolo_model = YOLO("VISION_LLM/yolov8-face.pt")

        # 2. Cargar FaceNet (modelo preentrenado)
        print("[INFO] Cargando modelo FaceNet...")
        self.facenet = InceptionResnetV1(pretrained='vggface2').eval()

        # Configurar dispositivo (GPU si está disponible)
        self.device = 'cuda' if torch.cuda.is_available() else 'cpu'
        print(f"[INFO] Usando dispositivo: {self.device}")
        self.facenet = self.facenet.to(self.device)

        # 3. Preprocesamiento para FaceNet
        self.transform = transforms.Compose([
            transforms.Resize((160, 160)),
            transforms.ToTensor(),
            transforms.Lambda(lambda x: x * 255.0),
            fixed_image_standardization,
            transforms.Normalize(mean=[0.5, 0.5, 0.5], std=[0.5, 0.5, 0.5])
        ])

        # Cargar rostros conocidos
        self.known_embeddings = self.load_known_faces()

    def load_known_faces(self, folder='VISION_LLM/known_faces'):
        """Cargar rostros conocidos desde la carpeta especificada"""
        print(f"\n[INFO] Cargando rostros conocidos de {folder}...")
        db = {}
        if not os.path.exists(folder):
            print(f"[ERROR] No se encontró la carpeta {folder}")
            return db
            
        for filename in os.listdir(folder):
            if filename.lower().endswith((".jpg", ".jpeg", ".png")):
                name = os.path.splitext(filename)[0]
                try:
                    img_path = os.path.join(folder, filename)
                    img = Image.open(img_path).convert('RGB')
                    
                    print(f"[LOAD] Procesando: {filename} - Tamaño: {img.size}")
                    
                    tensor = self.transform(img).unsqueeze(0).to(self.device)
                    with torch.no_grad():
                        embedding = self.facenet(tensor).cpu().detach().numpy()[0]
                    
                    embedding = embedding / np.linalg.norm(embedding)
                    db[name] = embedding
                    
                except Exception as e:
                    print(f"[ERROR] Error procesando {filename}: {str(e)}")
        
        print(f"[INFO] Base de datos cargada con {len(db)} rostros conocidos")
        return db

    def identify_face(self, embedding, threshold=0.6):
        min_dist = float('inf')
        best_match = "Desconocido"
        
        embedding = embedding / np.linalg.norm(embedding)
        
        for name, db_emb in self.known_embeddings.items():
            dist = cosine(embedding, db_emb)
            print(f"[COMP] {name}: distancia={dist:.4f}")
            
            if dist < threshold and dist < min_dist:
                min_dist = dist
                best_match = name
        
        return (best_match, min_dist) if best_match != "Desconocido" else ("Desconocido", None)

    def set_video_source(self, source):
        try:
            self.video_source = int(source) if source.isdigit() else source
            print(f"[INFO] Fuente de video configurada a: {self.video_source}")
        except Exception as e:
            print(f"[ERROR] Error configurando fuente de video: {e}")
            self.video_source = source

    def activar_camara(self):
        if self.camara is None or not self.camara.isOpened():
            try:
                if isinstance(self.video_source, str) and any(x in self.video_source.lower() for x in ['youtube.com', 'youtu.be']):
                    print("[INFO] Configurando fuente de video desde YouTube")
                    ydl_opts = {
                        'quiet': True,
                        'no_warnings': True,
                        'format': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best',
                        'socket_timeout': 10,
                        'force_ipv4': True,
                        'nocheckcertificate': True
                    }
                    
                    with youtube_dl.YoutubeDL(ydl_opts) as ydl:
                        try:
                            info = ydl.extract_info(self.video_source, download=False)
                            if 'entries' in info:
                                info = info['entries'][0]
                            url = info['url']
                            self.camara = cv2.VideoCapture(url)
                            if not self.camara.isOpened():
                                raise Exception("No se pudo abrir el stream")
                        except Exception as e:
                            print(f"[ERROR] YouTube: {str(e)}")
                            return False
                else:
                    print(f"[INFO] Configurando fuente de video: {self.video_source}")
                    self.camara = cv2.VideoCapture(self.video_source)
                    if isinstance(self.video_source, int):
                        self.camara.set(cv2.CAP_PROP_FRAME_WIDTH, self.target_width)
                        self.camara.set(cv2.CAP_PROP_FRAME_HEIGHT, self.target_height)
                
                if self.camara.isOpened():
                    self.ventana_activa = True
                    source_type = "YouTube" if isinstance(self.video_source, str) and any(x in self.video_source.lower() for x in ['youtube.com', 'youtu.be']) else \
                                "cámara web" if self.video_source == 0 else f"stream ({self.video_source})"
                    print(f"[INFO] Video activado desde {source_type}")
                    return True
                else:
                    print(f"[ERROR] No se pudo abrir la fuente: {self.video_source}")
                    return False
            except Exception as e:
                print(f"[ERROR] Error al configurar video: {str(e)[:200]}")
                return False
        else:
            print("[INFO] La fuente de video ya está activa.")
            return True

    def desactivar_camara(self):
        self.ventana_activa = False
        self.modo_rostros = False
        if self.camara:
            self.camara.release()
            self.camara = None
            print("[INFO] Video desactivado.")

    def habla(self, texto: str, voice_index: int = 0):
        motor = pyttsx3.init()
        voces = motor.getProperty('voices')
        if voice_index < len(voces):
            motor.setProperty('voice', voces[voice_index].id)
        motor.setProperty('rate', 150)
        motor.say(texto)
        motor.runAndWait()

    def run(self):
        while self.ventana_activa and not self.cerrar_todo:
            current_time = time.time()
            if current_time - self.last_frame_time < self.frame_interval:
                time.sleep(0.01)
                continue
                
            self.last_frame_time = current_time
            
            if self.camara and self.camara.isOpened():
                ret, frame = self.camara.read()
                if not ret:
                    time.sleep(0.1)
                    continue
                
                frame = cv2.resize(frame, (self.target_width, self.target_height))
                
                if self.modo_rostros and self.mostrar_detecciones:
                    rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                    
                    start_time = time.time()
                    results = self.yolo_model.predict(rgb_frame, conf=0.6, verbose=False)[0]
                    detection_time = time.time() - start_time
                    
                    print(f"\n[DETECT] Tiempo: {detection_time:.3f}s - Rostros: {len(results.boxes)}")
                    
                    for box in results.boxes.xyxy:
                        x1, y1, x2, y2 = map(int, box[:4])
                        face = frame[y1:y2, x1:x2]

                        if face.shape[0] > 20 and face.shape[1] > 20:
                            try:
                                face_pil = Image.fromarray(cv2.cvtColor(face, cv2.COLOR_BGR2RGB))
                                tensor = self.transform(face_pil).unsqueeze(0).to(self.device)
                                
                                start_time = time.time()
                                with torch.no_grad():
                                    emb = self.facenet(tensor).cpu().detach().numpy()[0]
                                embedding_time = time.time() - start_time
                                
                                print(f"[EMBED] Tiempo: {embedding_time:.3f}s")
                                
                                name, dist = self.identify_face(emb)
                                print(f"[RESULT] Identificado como: {name} (distancia: {dist if dist else 'N/A'})")
                                
                                color = (0, 255, 0) if name != "Desconocido" else (0, 0, 255)
                                cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)
                                label = f"{name}" + (f" ({dist:.2f})" if dist else "")
                                cv2.putText(frame, label, (x1, y1 - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255,255,255), 2)
                                
                            except Exception as e:
                                print(f"[ERROR] Procesamiento de rostro: {str(e)}")
                        else:
                            print(f"[WARN] Rostro demasiado pequeño: {face.shape}")
                
                rgb_image = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                h, w, ch = rgb_image.shape
                qt_image = QImage(rgb_image.data, w, h, ch * w, QImage.Format.Format_RGB888)
                self.update_frame_signal.emit(qt_image)

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("NOVA - ASISTENTE IA")
        self.resize(800, 600)
        
        main_widget = QWidget()
        main_layout = QVBoxLayout()
        
        self.video_frame = QLabel()
        self.video_frame.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.video_frame.setStyleSheet("background-color: black;")
        main_layout.addWidget(self.video_frame, stretch=3)
        
        chat_frame = QFrame()
        chat_frame.setFrameShape(QFrame.Shape.StyledPanel)
        chat_layout = QVBoxLayout()
        
        self.chat_display = QTextEdit()
        self.chat_display.setReadOnly(True)
        chat_layout.addWidget(self.chat_display)
        
        self.user_input = QTextEdit()
        self.user_input.setMaximumHeight(100)
        self.user_input.setPlaceholderText("Escribe aquí o ingresa URL (YouTube, RTSP, etc.)")
        chat_layout.addWidget(self.user_input)
        
        button_layout = QHBoxLayout()
        self.send_button = QPushButton("Enviar (Texto)")
        self.voice_button = QPushButton("Hablar (Voz)")
        self.voice_button.installEventFilter(self)
        self.voice_button.setStyleSheet("QPushButton { background-color: lightgray; }")
        self.camera_button = QPushButton("Activar Video")
        self.sound_checkbox = QCheckBox("Sonido")
        self.sound_checkbox.setChecked(True)
        
        button_layout.addWidget(self.send_button)
        button_layout.addWidget(self.voice_button)
        button_layout.addWidget(self.camera_button)
        button_layout.addWidget(self.sound_checkbox)
        
        chat_layout.addLayout(button_layout)
        chat_frame.setLayout(chat_layout)
        main_layout.addWidget(chat_frame, stretch=1)
        
        main_widget.setLayout(main_layout)
        self.setCentralWidget(main_widget)
        
        self.lista_salir = ["DETENER", "SALIR", "ABORTAR", "QUITAR", "ADIOS", "TERMINAR", "HASTA LUEGO"]
        self.usuario = "USUARIO"
        self.cerrar_todo = False
        self.listening = False
        self.reconoce_habla = sr.Recognizer()
        
        self.video_stream = VideoStream()
        self.video_stream.update_frame_signal.connect(self.update_frame)
        self.video_thread = None
        
        self.send_button.clicked.connect(self.send_text_message)
        self.camera_button.clicked.connect(self.toggle_camera)
        
        self.get_user_name()
    
    def eventFilter(self, obj, event):
        if obj == self.voice_button:
            if event.type() == QEvent.Type.MouseButtonPress:
                self.start_voice_recording()
                return True
            elif event.type() == QEvent.Type.MouseButtonRelease:
                self.stop_voice_recording()
                return True
        return super().eventFilter(obj, event)
    
    def start_voice_recording(self):
        self.voice_button.setStyleSheet("QPushButton { background-color: lightgreen; }")
        self.voice_button.setText("Escuchando...")
        QApplication.processEvents()
        
        self.listening = True
        self.voice_thread = threading.Thread(target=self.process_voice_input, daemon=True)
        self.voice_thread.start()
    
    def stop_voice_recording(self):
        self.voice_button.setStyleSheet("QPushButton { background-color: lightgray; }")
        self.voice_button.setText("Hablar (Voz)")
        self.listening = False
    

    def get_user_name(self):
        """Obtener nombre de usuario y perfil de los argumentos"""
        import argparse
        parser = argparse.ArgumentParser()
        parser.add_argument("--username", default="USUARIO")
        parser.add_argument("--profile", default="1")  # 0=admin, 1=operador
        args = parser.parse_args()
    
        self.usuario = args.username.upper()
        self.profile = int(args.profile)
    
        # Mensaje de bienvenida adaptado al perfil
        perfil_texto = "Administrador" if self.profile == 0 else "Operador"
        self.chat_display.append(f"Hola {self.usuario} ({perfil_texto})")
        self.chat_display.append(f"Escribe {', '.join(self.lista_salir)} para detener.")


    
    def update_frame(self, image):
        pixmap = QPixmap.fromImage(image)
        self.video_frame.setPixmap(pixmap.scaled(
            self.video_frame.size(), 
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation
        ))
    
    def toggle_camera(self):
        if not self.video_stream.ventana_activa:
            input_text = self.user_input.toPlainText().strip()
            
            if any(x in input_text.lower() for x in ['youtube.com', 'youtu.be']):
                self.video_stream.set_video_source(input_text)
                self.chat_display.append(f"NOVA: Configurando video desde YouTube")
            elif input_text.startswith(('rtsp://', 'http://', 'https://')):
                self.video_stream.set_video_source(input_text)
                self.chat_display.append(f"NOVA: Configurando video desde URL")
            elif input_text.isdigit():
                self.video_stream.set_video_source(int(input_text))
                self.chat_display.append(f"NOVA: Configurando cámara {input_text}")
            
            if self.video_stream.activar_camara():
                self.video_thread = threading.Thread(target=self.video_stream.run, daemon=True)
                self.video_thread.start()
                self.camera_button.setText("Desactivar Video")
        else:
            self.video_stream.desactivar_camara()
            self.video_frame.clear()
            self.video_frame.setStyleSheet("background-color: black;")
            self.camera_button.setText("Activar Video")
    
    def habla(self, texto: str, voice_index: int = 0):
        if not self.sound_checkbox.isChecked():
            return
            
        motor = pyttsx3.init()
        voces = motor.getProperty('voices')
        if voice_index < len(voces):
            motor.setProperty('voice', voces[voice_index].id)
        motor.setProperty('rate', 150)
        motor.say(texto)
        motor.runAndWait()
    
    def transcribir_audio(self, audio):
        try:
            texto_transcrito = self.reconoce_habla.recognize_google(audio, language="es-MX")
            print("Has dicho: " + texto_transcrito)
            return texto_transcrito
        except sr.UnknownValueError:
            print("Lo siento, no entendí.")
            return 'Lo siento, no entendí.'
        except sr.RequestError as e:
            print("Error de conexión con el servicio de voz; {0}".format(e))
            return 'Lo siento, no me pude conectar al servicio de reconocimiento de voz.'
    
    def process_voice_input(self):
        with sr.Microphone() as fuente_audio:
            try:
                start_time = time.time()
                while self.listening and (time.time() - start_time) < 10:
                    print("[VOICE] Escuchando...")
                    audio = self.reconoce_habla.listen(fuente_audio, phrase_time_limit=5)
                    pregunta = self.transcribir_audio(audio)
                    
                    if pregunta and pregunta != 'Lo siento, no entendí.':
                        self.chat_display.append(f"{self.usuario} (voz): {pregunta}")
                        respuesta = self.genera_respuesta(pregunta)
                        self.chat_display.append(f"NOVA: {respuesta}")
                        self.habla(respuesta)
                        break
                        
            except Exception as e:
                print(f"[ERROR] Reconocimiento de voz: {e}")
    
    def genera_respuesta(self, pregunta):
        if 'rostro' in pregunta.lower() or 'caras' in pregunta.lower():
            if not self.video_stream.ventana_activa:
                return "Para la búsqueda de rostros es necesario que active la cámara primero"
            
            if not self.video_stream.known_embeddings:
                return "No hay rostros conocidos en la carpeta 'known_faces' para buscar"
            
            self.video_stream.modo_rostros = True
            self.video_stream.mostrar_detecciones = True
            self.habla("Buscando rostros conocidos")
            return "Buscando rostros conocidos en la escena"
        
        if "detener búsqueda" in pregunta.lower() or "detener busqueda" in pregunta.lower():
            self.video_stream.modo_rostros = False
            self.video_stream.mostrar_detecciones = False
            return "Búsqueda detenida. Visualización de detecciones desactivada."
        
        if pregunta.upper() in self.lista_salir:
            self.close()
            return ""
            
        return "Comando no reconocido. Prueba con 'buscar rostro' o 'detener búsqueda'"
    
    def send_text_message(self):
        pregunta = self.user_input.toPlainText().strip()
        if not pregunta:
            return
            
        self.chat_display.append(f"{self.usuario}: {pregunta}")
        self.user_input.clear()
        
        if pregunta.upper() in self.lista_salir:
            self.close()
            return
        
        respuesta = self.genera_respuesta(pregunta)
        if respuesta:
            self.chat_display.append(f"NOVA: {respuesta}")
            self.habla(respuesta)
    
    def closeEvent(self, event):
        print("[INFO] Cerrando aplicación...")
        self.video_stream.cerrar_todo = True
        self.video_stream.desactivar_camara()
        self.listening = False
        event.accept()

if __name__ == "__main__":
    print("[INFO] Inicializando interfaz gráfica...")
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    print("[INFO] Interfaz gráfica inicializada correctamente")
    sys.exit(app.exec())