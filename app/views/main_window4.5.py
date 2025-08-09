# app/views/main_window.py
from PyQt6.QtWidgets import (
    QMainWindow, QVBoxLayout, QWidget, QLabel, QMenuBar, QMenu,
    QDialog, QLineEdit, QPushButton, QMessageBox, QTableWidget,
    QTableWidgetItem, QHeaderView, QComboBox
)
from PyQt6.QtGui import QAction
from PyQt6.QtCore import Qt
from app.utils.logger import get_logger
from app.utils.database import Database
from app.controllers.user_controller import UserController

logger = get_logger("nova.ui")

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
            
            # Acción Usuarios (nueva funcionalidad)
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

    def show_user_management(self):
        """Muestra el diálogo de gestión de usuarios"""
        dialog = UserManagementDialog(self)
        dialog.exec()

    def closeEvent(self, event):
        """Maneja el evento de cierre de la ventana"""
        logger.info(f"Ventana principal cerrada para usuario: {self.username}")
        super().closeEvent(event)