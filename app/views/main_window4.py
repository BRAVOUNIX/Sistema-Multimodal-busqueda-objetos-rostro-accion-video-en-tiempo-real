from PyQt6.QtWidgets import QMainWindow, QVBoxLayout, QWidget, QLabel
from PyQt6.QtCore import Qt
from app.utils.logger import get_logger

logger = get_logger("nova.ui")

class MainWindow(QMainWindow):
    def __init__(self, username):
        super().__init__()
        self.username = username
        self.setWindowTitle(f"Nova AI - Bienvenido {username}")
        self.setGeometry(100, 100, 800, 600)
        self.init_ui()
        logger.info(f"Ventana principal creada para {username}")
    
    def init_ui(self):
        central_widget = QWidget()
        layout = QVBoxLayout()
        
        welcome_label = QLabel(f"Bienvenido, {self.username}!")
        welcome_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        layout.addWidget(welcome_label)
        central_widget.setLayout(layout)
        self.setCentralWidget(central_widget)