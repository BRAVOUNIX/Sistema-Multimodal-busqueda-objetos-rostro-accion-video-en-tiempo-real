import sys
import time
import pyttsx3
import speech_recognition as sr
import openai
from openai import OpenAI
import cv2
import threading
import numpy as np
from ultralytics import YOLO
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QVBoxLayout, QHBoxLayout, 
    QWidget, QTextEdit, QPushButton, QLabel, QFrame, 
    QInputDialog, QCheckBox
)
from PyQt6.QtCore import Qt, QTimer, pyqtSignal, QObject, QEvent
from PyQt6.QtGui import QImage, QPixmap
import yt_dlp as youtube_dl

class VideoStream(QObject):
    update_frame_signal = pyqtSignal(QImage)
    
    def __init__(self):
        super().__init__()
        self.camara = None
        self.ventana_activa = False
        self.cerrar_todo = False
        self.objetos_detectados = []
        self.modelo_yolo = YOLO('VISION_LLM/yolov8n.pt')
        self.modo_rostros = False
        self.metodo_enmascaramiento = 'm0'
        self.masking_methods = {
            'm1': ("Desenfoque Gaussiano", self.apply_blur),
            'm2': ("Pixelación/Mosaico", self.apply_pixelation),
            'm3': ("Caja Negra", self.apply_black_box),
            'm4': ("Emoji (emoji.png)", self.apply_emoji),
            'm0': ("Sin enmascarar", None)
        }
        self.video_source = 0
        self.last_frame_time = 0
        self.frame_interval = 0.2
        self.target_width = 640
        self.target_height = 480
        
        self.buscar_clase = None
        self.buscar_color = None
        self.mostrar_detecciones = True
        
        self.class_mapping = {
            'persona': 'person', 'bicicleta': 'bicycle', 'carro': 'car', 
            'motocicleta': 'motorcycle', 'avion': 'airplane', 'autobus': 'bus',
            'tren': 'train', 'camión': 'truck', 'barco': 'boat',
            'semaforo': 'traffic light', 'hidrante': 'fire hydrant',
            'señal': 'stop sign', 'banco': 'bench', 'pajaro': 'bird',
            'gato': 'cat', 'perro': 'dog', 'caballo': 'horse',
            'oveja': 'sheep', 'vaca': 'cow', 'elefante': 'elephant',
            'oso': 'bear', 'cebra': 'zebra', 'jirafa': 'giraffe',
            'mochila': 'backpack', 'paraguas': 'umbrella', 'bolso': 'handbag',
            'corbata': 'tie', 'maleta': 'suitcase', 'pelota': 'sports ball',
            'botella': 'bottle', 'copa': 'wine glass', 'taza': 'cup',
            'tenedor': 'fork', 'cuchillo': 'knife', 'cuchara': 'spoon',
            'plato': 'bowl', 'platano': 'banana', 'manzana': 'apple',
            'naranja': 'orange', 'silla': 'chair', 'sofá': 'couch',
            'cama': 'bed', 'mesa': 'dining table', 'tv': 'tv',
            'computadora': 'laptop', 'celular': 'cell phone',
            'libro': 'book', 'reloj': 'clock', 'jarra': 'vase'
        }
        
        self.color_ranges = {
            'rojo': [(0, 100, 100), (10, 255, 255), (160, 100, 100), (179, 255, 255)],
            'verde': [(40, 50, 50), (80, 255, 255)],
            'azul': [(100, 50, 50), (130, 255, 255)],
            'amarillo': [(20, 100, 100), (30, 255, 255)],
            'naranja': [(10, 100, 100), (20, 255, 255)],
            'rosa': [(150, 50, 50), (170, 255, 255)],
            'morado': [(130, 50, 50), (150, 255, 255)],
            'blanco': [(0, 0, 200), (180, 30, 255)],
            'negro': [(0, 0, 0), (180, 255, 30)],
            'gris': [(0, 0, 50), (180, 50, 200)],
            'cyan': [(85, 100, 100), (95, 255, 255)],
            'marron': [(10, 100, 50), (20, 255, 150)]
        }

    def set_video_source(self, source):
        try:
            self.video_source = int(source) if source.isdigit() else source
        except:
            self.video_source = source

    def apply_blur(self, face_roi, intensity=30):
        ksize = intensity * 2 + 1
        return cv2.GaussianBlur(face_roi, (ksize, ksize), intensity)

    def apply_pixelation(self, face_roi, pixel_size=10):
        height, width = face_roi.shape[:2]
        small = cv2.resize(face_roi, (pixel_size, pixel_size), interpolation=cv2.INTER_LINEAR)
        return cv2.resize(small, (width, height), interpolation=cv2.INTER_NEAREST)

    def apply_black_box(self, face_roi):
        return np.zeros_like(face_roi)

    def apply_emoji(self, face_roi, emoji_path="VISION_LLM/emoji.png"):
        try:
            emoji = cv2.imread(emoji_path)
            if emoji is None:
                raise FileNotFoundError
            emoji = cv2.resize(emoji, (face_roi.shape[1], face_roi.shape[0]))
            return emoji
        except:
            return self.apply_black_box(face_roi)

    def activar_camara(self):
        if self.camara is None or not self.camara.isOpened():
            try:
                if isinstance(self.video_source, str) and any(x in self.video_source.lower() for x in ['youtube.com', 'youtu.be']):
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
                            print(f"Error YouTube: {str(e)}")
                            self.habla("Error al conectar con YouTube")
                            return
                else:
                    self.camara = cv2.VideoCapture(self.video_source)
                    if isinstance(self.video_source, int):
                        self.camara.set(cv2.CAP_PROP_FRAME_WIDTH, self.target_width)
                        self.camara.set(cv2.CAP_PROP_FRAME_HEIGHT, self.target_height)
                
                if self.camara.isOpened():
                    self.ventana_activa = True
                    source_type = "YouTube" if isinstance(self.video_source, str) and any(x in self.video_source.lower() for x in ['youtube.com', 'youtu.be']) else \
                                "cámara web" if self.video_source == 0 else f"stream ({self.video_source})"
                    print(f"Video activado desde {source_type}")
                    self.habla(f"Video activado desde {source_type}")
                else:
                    print(f"No se pudo abrir la fuente: {self.video_source}")
            except Exception as e:
                print(f"Error al configurar video: {str(e)[:200]}")
        else:
            print("La fuente de video ya está activa.")

    def desactivar_camara(self):
        self.ventana_activa = False
        if self.camara:
            self.camara.release()
            self.camara = None
            print("Video desactivado.")
            self.habla("Video desactivado")

    def habla(self, texto: str, voice_index: int = 0):
        motor = pyttsx3.init()
        voces = motor.getProperty('voices')
        if voice_index < len(voces):
            motor.setProperty('voice', voces[voice_index].id)
        motor.setProperty('rate', 150)
        motor.say(texto)
        motor.runAndWait()

    def buscar_por_color(self, roi, color_name):
        if color_name not in self.color_ranges:
            return False
            
        hsv = cv2.cvtColor(roi, cv2.COLOR_BGR2HSV)
        
        if len(self.color_ranges[color_name]) == 4:
            lower1, upper1, lower2, upper2 = self.color_ranges[color_name]
            mask1 = cv2.inRange(hsv, lower1, upper1)
            mask2 = cv2.inRange(hsv, lower2, upper2)
            mask = cv2.bitwise_or(mask1, mask2)
        else:
            lower, upper = self.color_ranges[color_name]
            mask = cv2.inRange(hsv, lower, upper)
        
        color_ratio = cv2.countNonZero(mask) / (roi.shape[0] * roi.shape[1])
        return color_ratio > 0.1

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
                
                predict_kwargs = {
                    'source': frame, 
                    'save': False, 
                    'verbose': False,
                    'imgsz': 320,
                    'device': 'cpu'
                }
                
                if self.buscar_clase is not None:
                    class_names = [k for k, v in self.modelo_yolo.names.items() if v.lower() == self.buscar_clase.lower()]
                    if class_names:
                        predict_kwargs['classes'] = [int(class_names[0])]
                
                resultados = self.modelo_yolo.predict(**predict_kwargs)
                self.objetos_detectados = []
                display_frame = frame.copy()
                
                for r in resultados:
                    for box in r.boxes:
                        x1, y1, x2, y2 = map(int, box.xyxy[0])
                        label = int(box.cls[0])
                        objeto = self.modelo_yolo.names[label]
                        
                        if self.modo_rostros:
                            metodo = self.masking_methods.get(self.metodo_enmascaramiento, (None, None))[1]
                            if metodo:
                                face_roi = display_frame[y1:y2, x1:x2]
                                enmascarado = metodo(face_roi)
                                display_frame[y1:y2, x1:x2] = enmascarado
                        else:
                            self.objetos_detectados.append(objeto)
                            
                            if self.mostrar_detecciones:
                                if self.buscar_clase and objeto.lower() == self.buscar_clase.lower():
                                    color = (0, 255, 255)  # Amarillo para búsqueda por clase
                                    grosor = 2
                                    
                                    if self.buscar_color:
                                        roi = frame[y1:y2, x1:x2]
                                        if self.buscar_por_color(roi, self.buscar_color):
                                            color = (0, 255, 0)  # Verde si coincide con el color
                                            grosor = 3
                                            cv2.putText(display_frame, f"{objeto} {self.buscar_color}", (x1, y1 - 10),
                                                       cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)
                                    
                                    cv2.rectangle(display_frame, (x1, y1), (x2, y2), color, grosor)
                                    if not self.buscar_color:
                                        cv2.putText(display_frame, f"{objeto}", (x1, y1 - 10),
                                                   cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)
                
                rgb_image = cv2.cvtColor(display_frame, cv2.COLOR_BGR2RGB)
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
        
        try:
            with open("API_KEY", 'r') as f:
                api_key = f.read().strip()
            self.client = OpenAI(api_key=api_key)
        except Exception as e:
            print(f"Error inicializando OpenAI: {e}")
            exit()
        
        self.MODELO = "gpt-4"
        
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
            
            self.video_stream.activar_camara()
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
                    print("Escuchando...")
                    audio = self.reconoce_habla.listen(fuente_audio, phrase_time_limit=5)
                    pregunta = self.transcribir_audio(audio)
                    
                    if pregunta and pregunta != 'Lo siento, no entendí.':
                        self.chat_display.append(f"{self.usuario} (voz): {pregunta}")
                        respuesta = self.genera_respuesta(pregunta)
                        self.chat_display.append(f"NOVA: {respuesta}")
                        self.habla(respuesta)
                        break
                        
            except Exception as e:
                print(f"Error en reconocimiento de voz: {e}")
    
    def genera_respuesta(self, pregunta):
        if "buscar" in pregunta.lower() or "encontrar" in pregunta.lower():
            self.video_stream.buscar_clase = None
            self.video_stream.buscar_color = None
            self.video_stream.mostrar_detecciones = True
            
            if " con " in pregunta.lower():
                partes = pregunta.lower().split(" con ")
                if len(partes) == 2:
                    clase_espanol = partes[0].replace("buscar", "").replace("encontrar", "").strip()
                    clase = self.video_stream.class_mapping.get(clase_espanol, clase_espanol)
                    color = partes[1].strip()
                    self.video_stream.buscar_clase = clase
                    self.video_stream.buscar_color = color
                    return f"Buscando {clase_espanol} con color {color}"
            else:
                clase_espanol = pregunta.lower().replace("buscar", "").replace("encontrar", "").strip()
                clase = self.video_stream.class_mapping.get(clase_espanol, clase_espanol)
                self.video_stream.buscar_clase = clase
                return f"Buscando {clase_espanol}"
        
        if "detener búsqueda" in pregunta.lower() or "detener busqueda" in pregunta.lower():
            self.video_stream.buscar_clase = None
            self.video_stream.buscar_color = None
            self.video_stream.mostrar_detecciones = False
            return "Búsqueda detenida. Visualización de detecciones desactivada."
        
        if "qué ves" in pregunta.lower() or "objetos" in pregunta.lower():
            if self.video_stream.objetos_detectados:
                return f"Veo estos objetos: {', '.join(set(self.video_stream.objetos_detectados))}"
            else:
                return "No detecto objetos por ahora."
        
        if 'rostro' in pregunta.lower() or 'caras' in pregunta.lower():
            self.video_stream.modelo_yolo = YOLO('VISION_LLM/yolov8-face.pt')
            self.video_stream.modo_rostros = True
            self.habla("Cambiando a modo detección de rostros")
            return "Cambiando a modo detección de rostros"
        
        if pregunta.lower() in ['m0', 'm1', 'm2', 'm3', 'm4']:
            self.video_stream.metodo_enmascaramiento = pregunta.lower()
            nombre, _ = self.video_stream.masking_methods[pregunta.lower()]
            self.habla(f"Método de enmascaramiento: {nombre}")
            return f"Método de enmascaramiento: {nombre}"
        
        return self.client.chat.completions.create(
            model=self.MODELO,
            messages=[
                {"role": "system", "content": "Eres Nova, un asistente amable y breve."},
                {"role": "user", "content": pregunta}
            ]
        ).choices[0].message.content.strip()
    
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
        self.chat_display.append(f"NOVA: {respuesta}")
        self.habla(respuesta)
    
    def closeEvent(self, event):
        self.video_stream.cerrar_todo = True
        self.video_stream.desactivar_camara()
        self.listening = False
        event.accept()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())