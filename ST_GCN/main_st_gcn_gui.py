import os
import sys
import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F
import cv2
import time
import threading
import pyttsx3
import speech_recognition as sr
import yt_dlp as youtube_dl
from ultralytics import YOLO
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QVBoxLayout, QHBoxLayout, 
    QWidget, QTextEdit, QPushButton, QLabel, QFrame, 
    QInputDialog, QCheckBox
)
from PyQt6.QtCore import Qt, pyqtSignal, QObject, QEvent
from PyQt6.QtGui import QImage, QPixmap

# Configurar rutas
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Configuración de dispositivo
device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
print(f"Using device: {device}")

# ================== CLASE Graph (OpenPose - 17 keypoints) ==================
class Graph:
    def __init__(self, layout='openpose', strategy='spatial'):
        self.num_node = 17  # Keypoints de OpenPose/YOLOv8
        self_link = [(i, i) for i in range(self.num_node)]
        neighbor_link = [
            (0, 1), (0, 2), (1, 3), (2, 4),  # Cabeza
            (3, 5), (4, 6), (5, 7), (6, 8),  # Brazos
            (5, 11), (6, 12), (11, 13), (12, 14),  # Piernas
            (13, 15), (14, 16), (5, 6), (11, 12)  # Pies y conexiones
        ]
        self.edge = self_link + neighbor_link
        self.center = 1  # Cuello como punto central
        
        # Matriz de adyacencia (3, 17, 17)
        self.A = self.get_adjacency_matrix()
    
    def get_adjacency_matrix(self):
        A = np.zeros((3, self.num_node, self.num_node))
        
        # Conexiones normales (A[0])
        for i, j in self.edge:
            A[0, i, j] = 1
            A[0, j, i] = 1
        
        # Conexiones espaciales (A[1] y A[2])
        for i, j in self.edge:
            if i == self.center or j == self.center:
                A[1, i, j] = 1
                A[1, j, i] = 1
            elif (i in [5,6,7,8,9,10] and j in [5,6,7,8,9,10]):  # Torso
                A[2, i, j] = 1
                A[2, j, i] = 1
        
        return A

# ================== CLASES del Modelo ST-GCN ==================
class ConvTemporalGraphical(nn.Module):
    def __init__(self, in_channels, out_channels, kernel_size):
        super().__init__()
        self.kernel_size = kernel_size
        self.conv = nn.Conv2d(in_channels, out_channels * kernel_size, 
                             kernel_size=(1, 1), padding=(0, 0), stride=(1, 1), 
                             dilation=(1, 1), bias=True)

    def forward(self, x, A):
        x = self.conv(x)
        n, kc, t, v = x.size()
        x = x.view(n, self.kernel_size, kc//self.kernel_size, t, v)
        x = torch.einsum('nkctv,kvw->nctw', (x, A))
        return x.contiguous(), A

class STGCNBlock(nn.Module):
    def __init__(self, in_channels, out_channels, kernel_size, stride=1, dropout=0, residual=True):
        super().__init__()
        padding = ((kernel_size[0] - 1) // 2, 0)
        
        self.gcn = ConvTemporalGraphical(in_channels, out_channels, kernel_size[1])
        
        self.tcn = nn.Sequential(
            nn.BatchNorm2d(out_channels),
            nn.ReLU(inplace=True),
            nn.Conv2d(
                out_channels,
                out_channels,
                (kernel_size[0], 1),
                (stride, 1),
                padding,
            ),
            nn.BatchNorm2d(out_channels),
            nn.Dropout(dropout, inplace=True),
        )

        if not residual:
            self.residual = lambda x: 0
        elif (in_channels == out_channels) and (stride == 1):
            self.residual = lambda x: x
        else:
            self.residual = nn.Sequential(
                nn.Conv2d(
                    in_channels,
                    out_channels,
                    kernel_size=1,
                    stride=(stride, 1)),
                nn.BatchNorm2d(out_channels),
            )

        self.relu = nn.ReLU(inplace=True)

    def forward(self, x, A):
        res = self.residual(x)
        x, A = self.gcn(x, A)
        x = self.tcn(x) + res
        return self.relu(x), A

class STGCN(nn.Module):
    def __init__(self, in_channels, num_class, graph_args, edge_importance_weighting=True):
        super().__init__()
        
        # Cargar grafo OpenPose
        self.graph = Graph(**graph_args)
        A = torch.tensor(self.graph.A, dtype=torch.float32, requires_grad=False)
        self.register_buffer('A', A)

        # Construir red
        spatial_kernel_size = A.size(0)
        temporal_kernel_size = 9
        kernel_size = (temporal_kernel_size, spatial_kernel_size)
        
        self.data_bn = nn.BatchNorm1d(in_channels * A.size(1))
        
        self.st_gcn_networks = nn.ModuleList([
            STGCNBlock(in_channels, 64, kernel_size, 1, residual=False),
            STGCNBlock(64, 64, kernel_size, 1),
            STGCNBlock(64, 64, kernel_size, 1),
            STGCNBlock(64, 64, kernel_size, 1),
            STGCNBlock(64, 128, kernel_size, 2),
            STGCNBlock(128, 128, kernel_size, 1),
            STGCNBlock(128, 128, kernel_size, 1),
            STGCNBlock(128, 256, kernel_size, 2),
            STGCNBlock(256, 256, kernel_size, 1),
            STGCNBlock(256, 256, kernel_size, 1)
        ])

        # Edge importance weighting
        if edge_importance_weighting:
            self.edge_importance = nn.ParameterList([
                nn.Parameter(torch.ones(A.size())) for _ in self.st_gcn_networks
            ])
        else:
            self.edge_importance = [1] * len(self.st_gcn_networks)

        # Capa de predicción
        self.fcn = nn.Conv2d(256, num_class, kernel_size=1)

    def forward(self, x):
        # Normalización de datos
        N, C, T, V, M = x.size()
        x = x.permute(0, 4, 3, 1, 2).contiguous()
        x = x.view(N * M, V * C, T)
        x = self.data_bn(x)
        x = x.view(N, M, V, C, T)
        x = x.permute(0, 1, 3, 4, 2).contiguous()
        x = x.view(N * M, C, T, V)

        # Forward pass
        for gcn, importance in zip(self.st_gcn_networks, self.edge_importance):
            x, _ = gcn(x, self.A * importance)

        # Global pooling
        x = F.avg_pool2d(x, x.size()[2:])
        x = x.view(N, M, -1, 1, 1).mean(dim=1)

        # Predicción
        x = self.fcn(x)
        x = x.view(x.size(0), -1)

        return x

# ================== FUNCIÓN load_model ==================
def load_model(checkpoint_path):
    # Configurar modelo con OpenPose (17 keypoints)
    model = STGCN(
        in_channels=3,
        num_class=60,
        graph_args={"layout": "openpose", "strategy": "spatial"},
        edge_importance_weighting=True
    ).to(device)
    
    # Cargar pesos con seguridad (weights_only=True)
    checkpoint = torch.load(checkpoint_path, map_location=device, weights_only=True)
    
    if 'state_dict' in checkpoint:
        # Adaptar pesos de MMAction2
        from collections import OrderedDict
        new_state_dict = OrderedDict()
        for k, v in checkpoint['state_dict'].items():
            if k.startswith('backbone.'):
                name = k[9:]  # Eliminar 'backbone.'
                new_state_dict[name] = v
        model.load_state_dict(new_state_dict, strict=False)
    else:
        model.load_state_dict(checkpoint, strict=False)
    
    model.eval()
    return model

class VideoStream(QObject):
    update_frame_signal = pyqtSignal(QImage)
    
    def __init__(self):
        super().__init__()
        self.camara = None
        self.ventana_activa = False
        self.cerrar_todo = False
        self.video_source = 0
        self.last_frame_time = 0
        self.frame_interval = 0.2
        self.target_width = 640
        self.target_height = 480
        self.action_to_search = None
        self.search_active = False
        
        # Configuración inicial
        print("[INFO] Inicializando sistema de reconocimiento de acciones...")
        
        # 1. Cargar YOLOv8 Pose (17 keypoints)
        print("[INFO] Cargando modelo YOLOv8-pose...")
        self.pose_model = YOLO('ST_GCN/yolov8n-pose.pt').to(device)
        
        # 2. Cargar ST-GCN
        print("[INFO] Cargando modelo ST-GCN...")
        self.stgcn_model = load_model('ST_GCN/st_gcn/weights/stgcn_ntu60_xsub_3d-5ae5b994.pth')
        
        # Definir acciones (español -> inglés)
        self.actions_es_en = {
            "caminando": "walking",
            "sentado": "sitting", 
            "sentada": "sitting",
            "de pie": "standing",
            "aplaudiendo": "clapping",
            "saludando": "waving",
            "golpeando": "punching",
            "pateando": "kicking",
            "empujando": "pushing",
            "saltando": "jumping",
            "señalando": "pointing",
            "abrazando": "hugging",
            "cayendo": "falling"
        }
        
        self.actions_en = list(set(self.actions_es_en.values()))

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
        if self.camara:
            self.camara.release()
            self.camara = None
            print("[INFO] Video desactivado.")

    def buscar_accion(self, accion_es):
        """Configura la acción a buscar en español"""
        accion_en = self.actions_es_en.get(accion_es.lower())
        if accion_en:
            self.action_to_search = accion_en
            self.search_active = True
            print(f"[INFO] Buscando acción: {accion_es} ({accion_en})")
            return True
        else:
            print(f"[ERROR] Acción no reconocida: {accion_es}")
            self.action_to_search = None
            self.search_active = False
            return False

    def detener_busqueda(self):
        """Detiene la búsqueda específica de acciones"""
        self.action_to_search = None
        self.search_active = False
        print("[INFO] Búsqueda de acción detenida")

    def run(self):
        while not self.cerrar_todo:
            if not self.ventana_activa:
                time.sleep(0.1)
                continue
                
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
                
                # Detección de pose para múltiples personas
                results = self.pose_model(frame, verbose=False)
                
                if len(results[0].keypoints) > 0:
                    # Procesar cada persona detectada
                    for i, keypoints in enumerate(results[0].keypoints.data.cpu().numpy()):
                        # Preparar keypoints para ST-GCN (3, 1, 17, 1)
                        keypoints_stgcn = np.zeros((3, 1, 17, 1))
                        keypoints_stgcn[0, 0, :, 0] = keypoints[:, 0]  # x
                        keypoints_stgcn[1, 0, :, 0] = keypoints[:, 1]  # y
                        keypoints_stgcn[2, 0, :, 0] = keypoints[:, 2]  # conf
                        
                        # Predicción de acción
                        with torch.no_grad():
                            input_tensor = torch.from_numpy(keypoints_stgcn).float().to(device)
                            output = self.stgcn_model(input_tensor.unsqueeze(0))
                            action_idx = torch.argmax(output).item()
                        
                        # Obtener acción predicha
                        action_en = self.actions_en[action_idx % len(self.actions_en)]
                        action_es = next((k for k, v in self.actions_es_en.items() if v == action_en), action_en)
                        
                        # Obtener caja delimitadora de la persona
                        box = results[0].boxes.xyxy[i].cpu().numpy()
                        x1, y1, x2, y2 = map(int, box[:4])
                        
                        # Determinar color y estilo según si estamos buscando esta acción
                        if self.search_active and self.action_to_search == action_en:
                            color = (0, 0, 255)  # Rojo para acción buscada
                            thickness = 3
                            action_text = f"ACCION ENCONTRADA: {action_es}"
                        else:
                            color = (0, 255, 0)  # Verde normal
                            thickness = 2
                            action_text = f"Persona {i+1}: {action_es}"
                        
                        # Visualización
                        cv2.rectangle(frame, (x1, y1), (x2, y2), color, thickness)
                        cv2.putText(frame, action_text, (x1, y1 - 10), 
                                   cv2.FONT_HERSHEY_SIMPLEX, 0.7, color, 2)
                
                # Mostrar frame con todas las detecciones
                rgb_image = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                h, w, ch = rgb_image.shape
                qt_image = QImage(rgb_image.data, w, h, ch * w, QImage.Format.Format_RGB888)
                self.update_frame_signal.emit(qt_image)

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("NOVA - Reconocimiento de Acciones (Búsqueda)")
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
        self.chat_display.append("Comandos disponibles:")
        self.chat_display.append("- buscar accion [nombre]: Busca una acción específica")
        self.chat_display.append("- detener busqueda: Detiene la búsqueda específica")
        self.chat_display.append("Acciones disponibles: caminando, sentado, de pie, aplaudiendo, saludando, golpeando, pateando, empujando, saltando, señalando, abrazando, cayendo")






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
                if self.video_thread is None or not self.video_thread.is_alive():
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
        # Comando para buscar acción específica
        if pregunta.lower().startswith("buscar accion"):
            accion = pregunta[13:].strip().lower()
            if self.video_stream.buscar_accion(accion):
                return f"Buscando acción: {accion}"
            else:
                return f"Acción no reconocida: {accion}. Acciones válidas: caminando, sentado, de pie, aplaudiendo, saludando, golpeando, pateando, empujando, saltando, señalando, abrazando, cayendo"
        
        if "detener busqueda" in pregunta.lower() or "detener busqueda" in pregunta.lower():
            self.video_stream.detener_busqueda()
            return "Búsqueda detenida. Visualización normal."
        
        if pregunta.upper() in self.lista_salir:
            self.close()
            return ""
            
        return "Comando no reconocido. Prueba con 'buscar accion [nombre]' o 'detener busqueda'"
    
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
        if self.video_thread and self.video_thread.is_alive():
            self.video_thread.join(timeout=1.0)
        event.accept()

if __name__ == "__main__":
    print("[INFO] Inicializando interfaz gráfica...")
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    print("[INFO] Interfaz gráfica inicializada correctamente")
    sys.exit(app.exec())