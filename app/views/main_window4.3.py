# app/views/main_window.py
from PyQt6.QtWidgets import (QMainWindow, QVBoxLayout, QWidget, QLabel, 
                            QMenuBar, QMenu, QMessageBox)
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
        menu_archivo = QMenu("&Archivo", self)
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
            
            # Submenú Usuarios
            submenu_usuarios = QMenu("&Usuarios", self)
            
            # Acciones para usuarios
            accion_listar = QAction("&Listar Usuarios", self)
            accion_listar.triggered.connect(self.mostrar_lista_usuarios)
            
            accion_agregar = QAction("&Agregar Usuario", self)
            accion_agregar.triggered.connect(self.mostrar_formulario_agregar)
            
            accion_editar = QAction("&Editar Usuario", self)
            accion_editar.triggered.connect(self.mostrar_formulario_editar)
            
            accion_eliminar = QAction("&Eliminar Usuario", self)
            accion_eliminar.triggered.connect(self.mostrar_formulario_eliminar)
            
            # Agregar acciones al submenu
            submenu_usuarios.addAction(accion_listar)
            submenu_usuarios.addAction(accion_agregar)
            submenu_usuarios.addAction(accion_editar)
            submenu_usuarios.addAction(accion_eliminar)
            
            # Configuración general
            accion_config = QAction("&Configuración", self)
            
            # Agregar al menú principal
            menu_admin.addMenu(submenu_usuarios)
            menu_admin.addAction(accion_config)
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

    # Métodos para manejar las acciones de usuarios
    def mostrar_lista_usuarios(self):
        """Muestra la lista de usuarios"""
        from app.views.user_dialog import UserListDialog
        dialog = UserListDialog(self)
        dialog.exec()
        logger.info("Listado de usuarios mostrado")

    def mostrar_formulario_agregar(self):
        """Muestra formulario para agregar usuario"""
        from app.views.user_dialog import UserFormDialog
        dialog = UserFormDialog(self, mode='add')
        if dialog.exec():
            logger.info(f"Usuario agregado: {dialog.username}")
            QMessageBox.information(self, "Éxito", "Usuario agregado correctamente")

    def mostrar_formulario_editar(self):
        """Muestra formulario para editar usuario"""
        from app.views.user_dialog import UserFormDialog
        dialog = UserFormDialog(self, mode='edit')
        if dialog.exec():
            logger.info(f"Usuario editado: {dialog.username}")
            QMessageBox.information(self, "Éxito", "Usuario editado correctamente")

    def mostrar_formulario_eliminar(self):
        """Muestra formulario para eliminar usuario"""
        from app.views.user_dialog import UserDeleteDialog
        dialog = UserDeleteDialog(self)
        if dialog.exec():
            logger.info(f"Usuario eliminado: {dialog.username}")
            QMessageBox.information(self, "Éxito", "Usuario eliminado correctamente")

    def closeEvent(self, event):
        """Maneja el evento de cierre de la ventana"""
        logger.info(f"Ventana principal cerrada para usuario: {self.username}")
        super().closeEvent(event)