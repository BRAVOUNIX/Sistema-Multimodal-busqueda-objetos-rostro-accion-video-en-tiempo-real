# app/views/main_window.py
from PyQt6.QtWidgets import QMainWindow, QVBoxLayout, QWidget, QLabel, QMenuBar, QMenu
from PyQt6.QtGui import QAction
from PyQt6.QtCore import Qt
from app.utils.logger import get_logger

logger = get_logger("nova.ui")

class MainWindow(QMainWindow):
    def __init__(self, username, profile):
        super().__init__()
        self.username = username
        self.profile = profile  # 0=admin, 1=operador
        self.setWindowTitle(f"Nova AI - Bienvenido {username}")
        self.setGeometry(100, 100, 800, 600)
        self.init_ui()
    
    def init_ui(self):
        # Configurar menús según perfil
        menubar = self.menuBar()
        
        # Menú de Operación (para todos)
        menu_operacion = QMenu("Operación", self)
        menu_operacion.addAction(QAction("Opción 1", self))
        menu_operacion.addAction(QAction("Opción 2", self))
        menubar.addMenu(menu_operacion)
        
        # Menú de Administración (solo perfil 0)
        if self.profile == 0:
            menu_admin = QMenu("Administración", self)
            menu_admin.addAction(QAction("Configuración", self))
            menu_admin.addAction(QAction("Usuarios", self))
            menubar.addMenu(menu_admin)
        
        # Contenido principal
        central_widget = QWidget()
        layout = QVBoxLayout()
        welcome_label = QLabel(f"Bienvenido, {self.username}!")
        welcome_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(welcome_label)
        central_widget.setLayout(layout)
        self.setCentralWidget(central_widget)