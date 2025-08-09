# app/views/login_window.py
from PyQt6.QtWidgets import QDialog, QVBoxLayout, QLabel, QLineEdit, QPushButton, QMessageBox
from PyQt6.QtCore import pyqtSignal, Qt
from PyQt6.QtGui import QIcon
import logging

class LoginWindow(QDialog):
    login_success = pyqtSignal(dict)  # Emite un diccionario con los resultados
    login_failed = pyqtSignal()
    
    def __init__(self, auth_controller):
        super().__init__()
        self.auth_controller = auth_controller
        self.logger = logging.getLogger("nova.ui.login")
        self.setWindowTitle("Nova AI - Login")
        self.setFixedSize(350, 220)
        self.setWindowIcon(QIcon("assets/icons/app_icon.ico"))
        self.init_ui()
    
    def init_ui(self):
        """Inicializa la interfaz de usuario del login"""
        layout = QVBoxLayout()
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.setSpacing(15)
        
        # Widgets
        self.lbl_title = QLabel("Bienvenido a Nova AI")
        self.lbl_title.setStyleSheet("font-size: 16px; font-weight: bold;")
        
        self.lbl_username = QLabel("Usuario:")
        self.username_input = QLineEdit()
        self.username_input.setPlaceholderText("Ingrese su usuario")
        self.username_input.setMinimumHeight(30)
        
        self.lbl_password = QLabel("Contraseña:")
        self.password_input = QLineEdit()
        self.password_input.setPlaceholderText("Ingrese su contraseña")
        self.password_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.password_input.setMinimumHeight(30)
        
        self.btn_login = QPushButton("Ingresar")
        self.btn_login.setMinimumHeight(35)
        self.btn_login.clicked.connect(self.authenticate)
        
        # Agregar widgets al layout
        layout.addWidget(self.lbl_title)
        layout.addStretch(1)
        layout.addWidget(self.lbl_username)
        layout.addWidget(self.username_input)
        layout.addWidget(self.lbl_password)
        layout.addWidget(self.password_input)
        layout.addStretch(1)
        layout.addWidget(self.btn_login)
        
        self.setLayout(layout)
    
    def authenticate(self):
        """Maneja el proceso de autenticación"""
        username = self.username_input.text().strip()
        password = self.password_input.text().strip()
        
        if not username or not password:
            self._show_warning("Campos requeridos", "Usuario y contraseña son obligatorios")
            return
            
        try:
            if not self.auth_controller.ensure_connection():
                self._show_error("Error de conexión", "No se pudo conectar a la base de datos")
                return
                
            auth_result = self.auth_controller.authenticate(username, password)
            
            if auth_result['authenticated']:
                self.logger.info(f"Usuario autenticado: {username}")
                self.login_success.emit(auth_result)
            else:
                self.logger.warning(f"Intento fallido para usuario: {username}")
                self.login_failed.emit()
                self._show_warning("Credenciales inválidas", "Usuario o contraseña incorrectos")
                
        except Exception as e:
            self.logger.error(f"Error en autenticación: {str(e)}", exc_info=True)
            self._show_error("Error técnico", f"No se pudo completar la autenticación: {str(e)}")
    
    def _show_warning(self, title, message):
        """Muestra un mensaje de advertencia"""
        QMessageBox.warning(self, title, message)
    
    def _show_error(self, title, message):
        """Muestra un mensaje de error"""
        QMessageBox.critical(self, title, message)
    
    def closeEvent(self, event):
        """Maneja el cierre de la ventana"""
        self.logger.info("Ventana de login cerrada")
        super().closeEvent(event)