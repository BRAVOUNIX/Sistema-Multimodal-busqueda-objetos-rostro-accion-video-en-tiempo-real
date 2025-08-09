# app/views/user_dialog.py
from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
                            QLineEdit, QPushButton, QTableWidget, 
                            QTableWidgetItem, QMessageBox, QComboBox)
from PyQt6.QtCore import Qt
from app.utils.logger import get_logger

logger = get_logger("nova.ui")

class UserListDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Listado de Usuarios")
        self.setModal(True)
        self.resize(600, 400)
        self.init_ui()
        
    def init_ui(self):
        layout = QVBoxLayout()
        
        # Tabla de usuarios
        self.table = QTableWidget()
        self.table.setColumnCount(4)
        self.table.setHorizontalHeaderLabels(["ID", "Usuario", "Perfil", "Estado"])
        self.table.setRowCount(0)  # Se llenará con datos reales
        
        # Botones
        btn_close = QPushButton("Cerrar")
        btn_close.clicked.connect(self.close)
        
        layout.addWidget(self.table)
        layout.addWidget(btn_close, alignment=Qt.AlignmentFlag.AlignRight)
        self.setLayout(layout)
        
        # Cargar datos (simulado)
        self.load_users()
    
    def load_users(self):
        """Carga datos de usuarios (ejemplo)"""
        try:
            # Aquí iría la conexión real a la base de datos
            users = [
                {"id": 1, "username": "admin", "profile": 0, "active": True},
                {"id": 2, "username": "operador1", "profile": 1, "active": True},
            ]
            
            self.table.setRowCount(len(users))
            for row, user in enumerate(users):
                self.table.setItem(row, 0, QTableWidgetItem(str(user["id"])))
                self.table.setItem(row, 1, QTableWidgetItem(user["username"]))
                self.table.setItem(row, 2, QTableWidgetItem(
                    "Administrador" if user["profile"] == 0 else "Operador"))
                self.table.setItem(row, 3, QTableWidgetItem(
                    "Activo" if user["active"] else "Inactivo"))
                    
        except Exception as e:
            logger.error(f"Error al cargar usuarios: {str(e)}")
            QMessageBox.critical(self, "Error", "No se pudieron cargar los usuarios")

class UserFormDialog(QDialog):
    def __init__(self, parent=None, mode='add'):
        super().__init__(parent)
        self.mode = mode
        self.setWindowTitle("Agregar Usuario" if mode == 'add' else "Editar Usuario")
        self.setModal(True)
        self.resize(400, 300)
        self.init_ui()
        
    def init_ui(self):
        layout = QVBoxLayout()
        
        # Campos del formulario
        self.lbl_username = QLabel("Usuario:")
        self.txt_username = QLineEdit()
        
        self.lbl_password = QLabel("Contraseña:")
        self.txt_password = QLineEdit()
        self.txt_password.setEchoMode(QLineEdit.EchoMode.Password)
        
        self.lbl_profile = QLabel("Perfil:")
        self.cmb_profile = QComboBox()
        self.cmb_profile.addItems(["Administrador", "Operador"])
        
        # Botones
        btn_layout = QHBoxLayout()
        btn_save = QPushButton("Guardar")
        btn_save.clicked.connect(self.accept)
        btn_cancel = QPushButton("Cancelar")
        btn_cancel.clicked.connect(self.reject)
        
        btn_layout.addWidget(btn_save)
        btn_layout.addWidget(btn_cancel)
        
        # Agregar al layout principal
        layout.addWidget(self.lbl_username)
        layout.addWidget(self.txt_username)
        layout.addWidget(self.lbl_password)
        layout.addWidget(self.txt_password)
        layout.addWidget(self.lbl_profile)
        layout.addWidget(self.cmb_profile)
        layout.addLayout(btn_layout)
        
        self.setLayout(layout)
    
    @property
    def username(self):
        return self.txt_username.text()
    
    @property
    def profile(self):
        return 0 if self.cmb_profile.currentText() == "Administrador" else 1

class UserDeleteDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Eliminar Usuario")
        self.setModal(True)
        self.resize(400, 200)
        self.init_ui()
        
    def init_ui(self):
        layout = QVBoxLayout()
        
        # Selección de usuario
        self.lbl_select = QLabel("Seleccionar usuario a eliminar:")
        self.cmb_users = QComboBox()
        self.cmb_users.addItems(["admin", "operador1"])  # Ejemplo
        
        # Botones
        btn_layout = QHBoxLayout()
        btn_delete = QPushButton("Eliminar")
        btn_delete.clicked.connect(self.accept)
        btn_cancel = QPushButton("Cancelar")
        btn_cancel.clicked.connect(self.reject)
        
        btn_layout.addWidget(btn_delete)
        btn_layout.addWidget(btn_cancel)
        
        layout.addWidget(self.lbl_select)
        layout.addWidget(self.cmb_users)
        layout.addLayout(btn_layout)
        
        self.setLayout(layout)
    
    @property
    def username(self):
        return self.cmb_users.currentText()