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
        logger.info(f"Ventana principal creada para {username} (Perfil: {profile})")
    
    def init_ui(self):
        # Configurar barra de menú
        menubar = self.menuBar()
        
        # Menú Archivo (común a todos los perfiles)
        menu_archivo = QMenu("&Archivo", self)  # El & permite acceso rápido con Alt+A
        
        # Acción Salir (Ctrl+Q como shortcut)
        accion_salir = QAction("&Salir", self)
        accion_salir.setShortcut("Ctrl+Q")
        accion_salir.setStatusTip("Cerrar la aplicación")
        accion_salir.triggered.connect(self.close)
        
        menu_archivo.addAction(accion_salir)
        menubar.addMenu(menu_archivo)
        
        # Menú Operación (común a todos los perfiles)
        menu_operacion = QMenu("&Operación", self)
        accion_op1 = QAction("Opción &1", self)
        accion_op2 = QAction("Opción &2", self)
        menu_operacion.addAction(accion_op1)
        menu_operacion.addAction(accion_op2)
        menubar.addMenu(menu_operacion)
        
        # Menú Administración (solo para perfil 0 - admin)
        if self.profile == 0:
            menu_admin = QMenu("&Administración", self)
            accion_config = QAction("&Configuración", self)
            accion_usuarios = QAction("&Usuarios", self)
            menu_admin.addAction(accion_config)
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

    def closeEvent(self, event):
        """Maneja el evento de cierre de la ventana"""
        logger.info(f"Ventana principal cerrada para usuario: {self.username}")
        super().closeEvent(event)