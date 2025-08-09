# app/views/login_window.py
from PyQt6.QtWidgets import QDialog, QVBoxLayout, QLabel, QLineEdit, QPushButton, QMessageBox
from PyQt6.QtCore import pyqtSignal, Qt
from PyQt6.QtGui import QIcon
import logging

class LoginWindow(QDialog):
    login_success = pyqtSignal(dict)  # Ahora emite un dict
    login_failed = pyqtSignal()
    
    def __init__(self, auth_controller):
        super().__init__()
        self.auth_controller = auth_controller
        self.logger = logging.getLogger("nova.ui.login")
        self.setWindowTitle("Nova AI - Login")
        self.setFixedSize(350, 220)
        self.setWindowIcon(QIcon("assets/icons/app_icon.ico"))
        self.init_ui()
    
    def authenticate(self):
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
                self.login_success.emit(auth_result)  # Emitir dict completo
            else:
                self.logger.warning(f"Intento fallido para usuario: {username}")
                self.login_failed.emit()
                self._show_warning("Credenciales inválidas", "Usuario o contraseña incorrectos")
                
        except Exception as e:
            self.logger.error(f"Error en autenticación: {str(e)}", exc_info=True)
            self._show_error("Error técnico", f"No se pudo completar la autenticación: {str(e)}")
    
    # ... [resto del código permanece igual] ...