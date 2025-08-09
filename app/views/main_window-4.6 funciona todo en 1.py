# app/views/main_window.py
from PyQt6.QtWidgets import (
    QMainWindow, QVBoxLayout, QWidget, QLabel, QMenuBar, QMenu,
    QDialog, QLineEdit, QPushButton, QMessageBox, QTableWidget,
    QTableWidgetItem, QHeaderView, QComboBox
)
from PyQt6.QtGui import QAction
from PyQt6.QtCore import Qt, pyqtSignal
from app.utils.logger import get_logger
from app.utils.database import Database
from app.controllers.user_controller import UserController
import cv2
import numpy as np
from ultralytics import YOLO
import threading

logger = get_logger("nova.ui")

class VideoPanel(QDialog):
    closed = pyqtSignal()
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Detección de Video")
        self.setMinimumSize(800, 600)
        self.camera = None
        self.window_active = False
        self.model = YOLO('assets/models/yolov8n.pt')
        self.face_model = YOLO('assets/models/yolov8-face.pt')
        self.face_mode = False
        self.mask_method = 'm0'
        self.detected_objects = []
        self.init_ui()
    
    def init_ui(self):
        layout = QVBoxLayout()
        
        self.status_label = QLabel("Video no iniciado")
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        self.btn_toggle = QPushButton("Iniciar Video")
        self.btn_toggle.clicked.connect(self.toggle_video)
        
        self.mask_combo = QComboBox()
        self.mask_combo.addItem("Sin enmascarar", 'm0')
        self.mask_combo.addItem("Desenfoque Gaussiano", 'm1')
        self.mask_combo.addItem("Pixelación", 'm2')
        self.mask_combo.addItem("Caja Negra", 'm3')
        self.mask_combo.addItem("Emoji", 'm4')
        self.mask_combo.currentIndexChanged.connect(self.change_mask_method)
        
        layout.addWidget(self.status_label)
        layout.addWidget(self.btn_toggle)
        layout.addWidget(self.mask_combo)
        
        self.setLayout(layout)
    
    def toggle_video(self):
        if "Iniciar" in self.btn_toggle.text():
            if self.start_camera():
                self.btn_toggle.setText("Detener Video")
                self.status_label.setText("Video en ejecución")
        else:
            self.stop_camera()
            self.btn_toggle.setText("Iniciar Video")
            self.status_label.setText("Video detenido")
    
    def change_mask_method(self):
        self.mask_method = self.mask_combo.currentData()
    
    def start_camera(self):
        if self.camera is None or not self.camera.isOpened():
            self.camera = cv2.VideoCapture(0)
            if self.camera.isOpened():
                self.window_active = True
                threading.Thread(target=self.show_camera, daemon=True).start()
                return True
        return False
    
    def stop_camera(self):
        self.window_active = False
        if self.camera:
            self.camera.release()
            cv2.destroyAllWindows()
            self.camera = None
    
    def show_camera(self):
        while self.window_active:
            if self.camera and self.camera.isOpened():
                ret, frame = self.camera.read()
                if not ret:
                    break
                
                results = self.face_model.predict(source=frame, save=False) if self.face_mode else self.model.predict(source=frame, save=False)
                self.detected_objects = []
                
                for r in results:
                    for box in r.boxes:
                        x1, y1, x2, y2 = map(int, box.xyxy[0])
                        label = int(box.cls[0])
                        if not self.face_mode:
                            self.detected_objects.append(self.model.names[label])
                
                annotated = results[0].plot()
                cv2.imshow('Video Detection', annotated)
                
                if cv2.waitKey(1) & 0xFF == ord('q'):
                    self.stop_camera()
                    break
    
    def closeEvent(self, event):
        self.stop_camera()
        self.closed.emit()
        super().closeEvent(event)

class UserManagementDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.db = Database()
        self.user_controller = UserController(self.db)
        self.setWindowTitle("Gestión de Usuarios")
        self.setModal(True)
        self.setMinimumSize(600, 400)
        self.init_ui()
        self.load_users()
    
    def init_ui(self):
        layout = QVBoxLayout()
        
        # Tabla de usuarios
        self.table = QTableWidget()
        self.table.setColumnCount(3)
        self.table.setHorizontalHeaderLabels(["ID", "Usuario", "Perfil"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        
        # Botones
        btn_layout = QVBoxLayout()
        
        self.btn_add = QPushButton("Agregar Usuario")
        self.btn_add.clicked.connect(self.add_user)
        
        self.btn_edit = QPushButton("Editar Usuario")
        self.btn_edit.clicked.connect(self.edit_user)
        
        self.btn_delete = QPushButton("Eliminar Usuario")
        self.btn_delete.clicked.connect(self.delete_user)
        
        btn_layout.addWidget(self.btn_add)
        btn_layout.addWidget(self.btn_edit)
        btn_layout.addWidget(self.btn_delete)
        
        layout.addWidget(self.table)
        layout.addLayout(btn_layout)
        
        self.setLayout(layout)
    
    def load_users(self):
        users = self.user_controller.list_users()
        self.table.setRowCount(len(users))
        
        for row, user in enumerate(users):
            self.table.setItem(row, 0, QTableWidgetItem(str(user['id'])))
            self.table.setItem(row, 1, QTableWidgetItem(user['username']))
            profile_text = "Administrador" if user['profile'] == 0 else "Operador"
            self.table.setItem(row, 2, QTableWidgetItem(profile_text))
    
    def add_user(self):
        dialog = QDialog(self)
        dialog.setWindowTitle("Agregar Usuario")
        layout = QVBoxLayout()
        
        username_input = QLineEdit()
        username_input.setPlaceholderText("Nombre de usuario")
        
        password_input = QLineEdit()
        password_input.setPlaceholderText("Contraseña")
        password_input.setEchoMode(QLineEdit.EchoMode.Password)
        
        profile_combo = QComboBox()
        profile_combo.addItem("Administrador", 0)
        profile_combo.addItem("Operador", 1)
        
        btn_save = QPushButton("Guardar")
        
        def save_user():
            username = username_input.text().strip()
            password = password_input.text().strip()
            profile = profile_combo.currentData()
            
            if not username or not password:
                QMessageBox.warning(self, "Error", "Usuario y contraseña son obligatorios")
                return
                
            if self.user_controller.add_user(username, password, profile):
                QMessageBox.information(self, "Éxito", "Usuario agregado correctamente")
                self.load_users()
                dialog.close()
            else:
                QMessageBox.critical(self, "Error", "No se pudo agregar el usuario")
        
        btn_save.clicked.connect(save_user)
        
        layout.addWidget(username_input)
        layout.addWidget(password_input)
        layout.addWidget(profile_combo)
        layout.addWidget(btn_save)
        
        dialog.setLayout(layout)
        dialog.exec()
    
    def edit_user(self):
        selected = self.table.currentRow()
        if selected < 0:
            QMessageBox.warning(self, "Error", "Seleccione un usuario")
            return
            
        user_id = int(self.table.item(selected, 0).text())
        current_username = self.table.item(selected, 1).text()
        current_profile = 0 if self.table.item(selected, 2).text() == "Administrador" else 1
        
        dialog = QDialog(self)
        dialog.setWindowTitle("Editar Usuario")
        layout = QVBoxLayout()
        
        username_input = QLineEdit(current_username)
        
        password_input = QLineEdit()
        password_input.setPlaceholderText("Dejar vacío para no cambiar")
        password_input.setEchoMode(QLineEdit.EchoMode.Password)
        
        profile_combo = QComboBox()
        profile_combo.addItem("Administrador", 0)
        profile_combo.addItem("Operador", 1)
        profile_combo.setCurrentIndex(current_profile)
        
        btn_save = QPushButton("Guardar")
        
        def save_changes():
            new_username = username_input.text().strip()
            new_password = password_input.text().strip()
            new_profile = profile_combo.currentData()
            
            if not new_username:
                QMessageBox.warning(self, "Error", "El nombre de usuario es obligatorio")
                return
                
            if new_password:
                success = self.user_controller.update_user(user_id, new_username, new_password, new_profile)
            else:
                success = self.user_controller.update_user(user_id, new_username, None, new_profile)
            
            if success:
                QMessageBox.information(self, "Éxito", "Usuario actualizado correctamente")
                self.load_users()
                dialog.close()
            else:
                QMessageBox.critical(self, "Error", "No se pudo actualizar el usuario")
        
        btn_save.clicked.connect(save_changes)
        
        layout.addWidget(username_input)
        layout.addWidget(password_input)
        layout.addWidget(profile_combo)
        layout.addWidget(btn_save)
        
        dialog.setLayout(layout)
        dialog.exec()
    
    def delete_user(self):
        selected = self.table.currentRow()
        if selected < 0:
            QMessageBox.warning(self, "Error", "Seleccione un usuario")
            return
            
        user_id = int(self.table.item(selected, 0).text())
        username = self.table.item(selected, 1).text()
        
        confirm = QMessageBox.question(
            self, "Confirmar", 
            f"¿Está seguro de eliminar al usuario {username}?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        
        if confirm == QMessageBox.StandardButton.Yes:
            if self.user_controller.delete_user(user_id):
                QMessageBox.information(self, "Éxito", "Usuario eliminado correctamente")
                self.load_users()
            else:
                QMessageBox.critical(self, "Error", "No se pudo eliminar el usuario")

class MainWindow(QMainWindow):
    def __init__(self, username, profile):
        super().__init__()
        self.username = username
        self.profile = profile  # 0=admin, 1=operador
        self.setWindowTitle(f"Nova AI - Bienvenido {username}")
        self.setGeometry(100, 100, 800, 600)
        self.init_ui()
        logger.info(f"Ventana principal creada para {username} (Perfil: {profile})")
    
    def init_ui(self):
        # Configurar barra de menú
        menubar = self.menuBar()
        
        # Menú Archivo (común a todos los perfiles)
        menu_archivo = QMenu("&Archivo", self)
        
        # Acción Salir (Ctrl+Q como shortcut)
        accion_salir = QAction("&Salir", self)
        accion_salir.setShortcut("Ctrl+Q")
        accion_salir.setStatusTip("Cerrar la aplicación")
        accion_salir.triggered.connect(self.close)
        
        menu_archivo.addAction(accion_salir)
        menubar.addMenu(menu_archivo)
        
        # Menú Operación (modificado para incluir video)
        menu_operacion = QMenu("&Operación", self)
        
        # Acción para Video Detection
        accion_video = QAction("Video &Detection", self)
        accion_video.setStatusTip("Abrir panel de detección de video")
        accion_video.triggered.connect(self.show_video_panel)
        menu_operacion.addAction(accion_video)
        
        # Acción Opción 2 (se mantiene)
        accion_op2 = QAction("Opción &2", self)
        menu_operacion.addAction(accion_op2)
        
        menubar.addMenu(menu_operacion)
        
        # Menú Administración (solo para perfil 0 - admin)
        if self.profile == 0:
            menu_admin = QMenu("&Administración", self)
            
            # Acción Usuarios
            accion_usuarios = QAction("&Usuarios", self)
            accion_usuarios.triggered.connect(self.show_user_management)
            
            menu_admin.addAction(accion_usuarios)
            menubar.addMenu(menu_admin)
        
        # Barra de estado
        self.statusBar().showMessage(f"Usuario: {self.username} | Perfil: {'Administrador' if self.profile == 0 else 'Operador'}")
        
        # Contenido principal
        central_widget = QWidget()
        layout = QVBoxLayout()
        
        welcome_label = QLabel(f"Bienvenido, {self.username}!")
        welcome_label.setStyleSheet("font-size: 18px; font-weight: bold;")
        welcome_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        layout.addWidget(welcome_label)
        central_widget.setLayout(layout)
        self.setCentralWidget(central_widget)

    def show_video_panel(self):
        """Muestra el panel de detección de video"""
        self.video_panel = VideoPanel(self)
        self.video_panel.closed.connect(self.on_video_panel_closed)
        self.video_panel.show()

    def on_video_panel_closed(self):
        """Maneja el cierre del panel de video"""
        pass

    def show_user_management(self):
        """Muestra el diálogo de gestión de usuarios"""
        dialog = UserManagementDialog(self)
        dialog.exec()

    def closeEvent(self, event):
        """Maneja el evento de cierre de la ventana"""
        logger.info(f"Ventana principal cerrada para usuario: {self.username}")
        super().closeEvent(event)