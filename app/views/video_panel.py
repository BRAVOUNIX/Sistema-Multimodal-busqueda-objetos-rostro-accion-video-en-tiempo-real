# app/views/video_panel.py
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QWidget, QLabel, QPushButton, QComboBox,
    QLineEdit, QHBoxLayout, QTextEdit, QGroupBox, QRadioButton,
    QButtonGroup
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QIcon, QColor
import cv2
import numpy as np
from PIL import Image
import io

class VideoPanel(QDialog):
    closed = pyqtSignal()
    
    def __init__(self, video_controller, username):
        super().__init__()
        self.video_controller = video_controller
        self.username = username
        self.selected_object = None
        self.setWindowTitle(f"Video Panel - {username}")
        self.setMinimumSize(1000, 800)
        self.init_ui()
    
    def init_ui(self):
        main_layout = QVBoxLayout()
        
        # ===== Sección de Modos de Video =====
        mode_group = QGroupBox("Modo de Video")
        mode_layout = QHBoxLayout()
        
        self.mode_group = QButtonGroup()
        
        self.obj_mode = QRadioButton("Video Objeto")
        self.obj_mode.setChecked(True)
        self.mode_group.addButton(self.obj_mode, 1)
        
        self.mask_mode = QRadioButton("Video Enmascarar")
        self.mode_group.addButton(self.mask_mode, 2)
        
        mode_layout.addWidget(self.obj_mode)
        mode_layout.addWidget(self.mask_mode)
        mode_group.setLayout(mode_layout)
        
        # ===== Opciones de Objetos =====
        self.obj_options_group = QGroupBox("Opciones de Objeto")
        obj_options_layout = QHBoxLayout()
        
        self.obj_combo = QComboBox()
        self.obj_combo.addItem("Persona", "person")
        self.obj_combo.addItem("Silla", "chair")
        self.obj_combo.addItem("Carro", "car")
        self.obj_combo.addItem("Botella", "bottle")
        self.obj_combo.currentIndexChanged.connect(self.change_object)
        
        obj_options_layout.addWidget(QLabel("Seleccionar objeto:"))
        obj_options_layout.addWidget(self.obj_combo)
        self.obj_options_group.setLayout(obj_options_layout)
        
        # ===== Opciones de Enmascaramiento =====
        self.mask_options_group = QGroupBox("Opciones de Enmascaramiento")
        mask_options_layout = QHBoxLayout()
        
        self.mask_combo = QComboBox()
        self.mask_combo.addItem("Sin enmascarar", 'm0')
        self.mask_combo.addItem("Pixelación", 'm2')
        self.mask_combo.addItem("Desenfoque Gaussiano", 'm1')
        self.mask_combo.addItem("Caja Negra", 'm3')
        self.mask_combo.addItem("Emoji", 'm4')
        self.mask_combo.currentIndexChanged.connect(self.change_mask_method)
        
        mask_options_layout.addWidget(QLabel("Método:"))
        mask_options_layout.addWidget(self.mask_combo)
        self.mask_options_group.setLayout(mask_options_layout)
        self.mask_options_group.setVisible(False)
        
        # ===== Controles de Video =====
        control_group = QGroupBox("Controles")
        control_layout = QHBoxLayout()
        
        self.btn_toggle = QPushButton()
        self.btn_toggle.setIcon(QIcon("assets/icons/camera.png"))
        self.btn_toggle.setText(" Iniciar Video")
        self.btn_toggle.clicked.connect(self.toggle_video)
        
        control_layout.addWidget(self.btn_toggle)
        control_group.setLayout(control_layout)
        
        # ===== Interacción con Nova =====
        nova_group = QGroupBox("Interacción con Nova")
        nova_layout = QVBoxLayout()
        
        # Opciones de interacción
        interac_layout = QHBoxLayout()
        
        self.voice_btn = QPushButton()
        self.voice_btn.setIcon(QIcon("assets/icons/microphone.png"))
        self.voice_btn.setText(" Voz")
        self.voice_btn.clicked.connect(self.toggle_voice)
        
        self.text_btn = QPushButton()
        self.text_btn.setIcon(QIcon("assets/icons/keyboard.png"))
        self.text_btn.setText(" Texto")
        self.text_btn.clicked.connect(self.activate_text_input)
        
        self.sound_btn = QPushButton()
        self.sound_btn.setIcon(QIcon("assets/icons/volume.png"))
        self.sound_btn.setText(" Sonido")
        self.sound_btn.setCheckable(True)
        self.sound_btn.setChecked(True)
        
        interac_layout.addWidget(self.voice_btn)
        interac_layout.addWidget(self.text_btn)
        interac_layout.addWidget(self.sound_btn)
        
        # Entrada de texto
        self.command_input = QLineEdit()
        self.command_input.setPlaceholderText("Escribe un comando para Nova...")
        self.command_input.returnPressed.connect(self.process_text_command)
        self.command_input.setEnabled(False)
        
        # Botón para enviar comando
        self.btn_send = QPushButton("Enviar")
        self.btn_send.clicked.connect(self.process_text_command)
        self.btn_send.setEnabled(False)
        
        input_layout = QHBoxLayout()
        input_layout.addWidget(self.command_input)
        input_layout.addWidget(self.btn_send)
        
        # Área de registro
        self.log_area = QTextEdit()
        self.log_area.setReadOnly(True)
        
        nova_layout.addLayout(interac_layout)
        nova_layout.addLayout(input_layout)
        nova_layout.addWidget(self.log_area)
        nova_group.setLayout(nova_layout)
        
        # ===== Ensamblar layout principal =====
        main_layout.addWidget(mode_group)
        main_layout.addWidget(self.obj_options_group)
        main_layout.addWidget(self.mask_options_group)
        main_layout.addWidget(control_group)
        main_layout.addWidget(nova_group)
        
        # Conectar cambios de modo
        self.obj_mode.toggled.connect(self.update_mode_display)
        self.mask_mode.toggled.connect(self.update_mode_display)
        
        # Configuración inicial
        self.change_object()  # Establecer objeto inicial
        self.change_mask_method()  # Establecer método inicial
        
        self.setLayout(main_layout)
    
    def change_object(self):
        """Cambia el objeto a detectar"""
        self.selected_object = self.obj_combo.currentData()
        self.video_controller.set_target_object(self.selected_object)
        self.log_message("Sistema", f"Objeto seleccionado: {self.obj_combo.currentText()}")
    
    def change_mask_method(self):
        """Cambia el método de enmascaramiento"""
        method = self.mask_combo.currentData()
        self.video_controller.set_mask_method(method)
        self.log_message("Sistema", f"Método de enmascaramiento: {self.mask_combo.currentText()}")
    
    def update_mode_display(self):
        """Actualiza la interfaz según el modo seleccionado"""
        try:
            if self.obj_mode.isChecked():
                self.obj_options_group.setVisible(True)
                self.mask_options_group.setVisible(False)
                self.video_controller.set_detection_mode('object')
                self.log_message("Sistema", "Modo: Detección de objetos")
            else:
                self.obj_options_group.setVisible(False)
                self.mask_options_group.setVisible(True)
                self.video_controller.set_detection_mode('face')
                self.log_message("Sistema", "Modo: Enmascaramiento de rostros")
        except Exception as e:
            self.log_message("Error", f"Error al cambiar modo: {str(e)}")
            raise
    
    def toggle_video(self):
        """Alterna el estado del video"""
        if "Iniciar" in self.btn_toggle.text():
            if self.video_controller.start_video(self.update_video_frame):
                self.btn_toggle.setIcon(QIcon("assets/icons/camera-off.png"))
                self.btn_toggle.setText(" Detener Video")
                self.log_message("Sistema", "Video iniciado")
        else:
            self.video_controller.stop_video()
            self.btn_toggle.setIcon(QIcon("assets/icons/camera.png"))
            self.btn_toggle.setText(" Iniciar Video")
            self.log_message("Sistema", "Video detenido")
    
    def update_video_frame(self, frame):
        """Actualiza el frame de video con las anotaciones"""
        try:
            cv2.imshow('Video Nova', frame)
            if cv2.waitKey(1) & 0xFF == ord('q'):
                self.toggle_video()
        except Exception as e:
            self.log_message("Error", f"Error mostrando video: {str(e)}")
    
    def toggle_voice(self):
        """Alterna el modo de voz"""
        if self.voice_btn.text().strip() == "Voz":
            self.voice_btn.setIcon(QIcon("assets/icons/microphone-active.png"))
            self.voice_btn.setText(" Escuchando...")
            self.command_input.setEnabled(False)
            self.btn_send.setEnabled(False)
            
            success, message = self.video_controller.toggle_voice_listening()
            if success:
                self.log_message("Voz", f"Comando: {message}")
                self.process_command(message)
            else:
                self.log_message("Error", message)
            
            self.voice_btn.setIcon(QIcon("assets/icons/microphone.png"))
            self.voice_btn.setText(" Voz")
        else:
            self.video_controller.stop_listening()
            self.voice_btn.setIcon(QIcon("assets/icons/microphone.png"))
            self.voice_btn.setText(" Voz")
    
    def activate_text_input(self):
        """Activa la entrada de texto"""
        self.command_input.setEnabled(True)
        self.btn_send.setEnabled(True)
        self.command_input.setFocus()
    
    def process_text_command(self):
        """Procesa un comando de texto"""
        command = self.command_input.text()
        if command:
            self.log_message("Usuario", command)
            self.command_input.clear()
            self.process_command(command)
    
    def process_command(self, command):
        """Procesa un comando (voz o texto)"""
        response = self.video_controller.process_command(command)
        self.log_message("Nova", response)
        
        if self.sound_btn.isChecked():
            self.video_controller.speak(response)
    
    def log_message(self, sender, message):
        """Registra un mensaje en el área de texto"""
        self.log_area.append(f"<b>{sender}:</b> {message}")
        self.log_area.verticalScrollBar().setValue(self.log_area.verticalScrollBar().maximum())
    
    def closeEvent(self, event):
        """Maneja el cierre de la ventana"""
        self.video_controller.stop_video()
        cv2.destroyAllWindows()
        self.closed.emit()
        super().closeEvent(event)