# app/views/video_panel.py
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QLabel, QPushButton, QComboBox,
    QLineEdit, QHBoxLayout, QTextEdit
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QIcon

class VideoPanel(QDialog):
    closed = pyqtSignal()
    
    def __init__(self, video_controller, username):
        super().__init__()
        self.video_controller = video_controller
        self.username = username
        self.setWindowTitle(f"Video Detection - {username}")
        self.setMinimumSize(800, 600)
        self.init_ui()
    
    def init_ui(self):
        layout = QVBoxLayout()
        
        # Estado del video
        self.status_label = QLabel("Video no iniciado")
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        # Botones de control de video
        self.btn_toggle = QPushButton("Iniciar Video")
        self.btn_toggle.clicked.connect(self.toggle_video)
        
        # Métodos de enmascaramiento
        self.mask_combo = QComboBox()
        self.mask_combo.addItem("Sin enmascarar", 'm0')
        self.mask_combo.addItem("Desenfoque Gaussiano", 'm1')
        self.mask_combo.addItem("Pixelación", 'm2')
        self.mask_combo.addItem("Caja Negra", 'm3')
        self.mask_combo.addItem("Emoji", 'm4')
        self.mask_combo.currentIndexChanged.connect(self.change_mask_method)
        
        # Control de voz
        self.btn_voice = QPushButton()
        self.btn_voice.setIcon(QIcon("assets/icons/microphone.png"))
        self.btn_voice.setText(" Activar Voz")
        self.btn_voice.clicked.connect(self.toggle_voice)
        
        # Entrada de texto
        self.command_input = QLineEdit()
        self.command_input.setPlaceholderText("Escribe un comando para Nova...")
        self.command_input.returnPressed.connect(self.process_text_command)
        
        # Botón para enviar comando
        self.btn_send = QPushButton("Enviar")
        self.btn_send.clicked.connect(self.process_text_command)
        
        # Área de registro
        self.log_area = QTextEdit()
        self.log_area.setReadOnly(True)
        
        # Diseño de controles
        controls_layout = QHBoxLayout()
        controls_layout.addWidget(self.btn_toggle)
        controls_layout.addWidget(self.mask_combo)
        controls_layout.addWidget(self.btn_voice)
        
        input_layout = QHBoxLayout()
        input_layout.addWidget(self.command_input)
        input_layout.addWidget(self.btn_send)
        
        # Agregar todos los widgets al layout principal
        layout.addWidget(self.status_label)
        layout.addLayout(controls_layout)
        layout.addLayout(input_layout)
        layout.addWidget(self.log_area)
        
        self.setLayout(layout)
    
    def toggle_video(self):
        if "Iniciar" in self.btn_toggle.text():
            if self.video_controller.start_video():
                self.btn_toggle.setText("Detener Video")
                self.status_label.setText("Video en ejecución")
                self.log_message("Sistema", "Video iniciado")
        else:
            self.video_controller.stop_video()
            self.btn_toggle.setText("Iniciar Video")
            self.status_label.setText("Video detenido")
            self.log_message("Sistema", "Video detenido")
    
    def change_mask_method(self):
        method = self.mask_combo.currentData()
        self.video_controller.set_mask_method(method)
        self.log_message("Sistema", f"Método de enmascaramiento cambiado a: {self.mask_combo.currentText()}")
    
    def toggle_voice(self):
        success, message = self.video_controller.toggle_voice_listening()
        if success:
            self.btn_voice.setIcon(QIcon("assets/icons/microphone-active.png"))
            self.btn_voice.setText(" Escuchando...")
            self.log_message("Voz", f"Comando de voz: {message}")
            response = self.video_controller.process_text_command(message)
            self.video_controller.speak_response(response)
            self.log_message("Nova", response)
        else:
            self.btn_voice.setIcon(QIcon("assets/icons/microphone.png"))
            self.btn_voice.setText(" Activar Voz")
            if "Error" not in message:
                self.log_message("Sistema", message)
            else:
                self.log_message("Error", message)
    
    def process_text_command(self):
        command = self.command_input.text()
        if command:
            self.log_message("Usuario", command)
            self.command_input.clear()
            response = self.video_controller.process_text_command(command)
            self.video_controller.speak_response(response)
            self.log_message("Nova", response)
    
    def log_message(self, sender: str, message: str):
        """Agrega un mensaje al área de registro"""
        self.log_area.append(f"<b>{sender}:</b> {message}")
    
    def closeEvent(self, event):
        self.video_controller.stop_video()
        self.closed.emit()
        super().closeEvent(event)