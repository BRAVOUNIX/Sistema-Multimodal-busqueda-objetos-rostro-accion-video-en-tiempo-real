# app/views/img_rostro_window.py
from PyQt6.QtWidgets import (
    QMainWindow, QVBoxLayout, QWidget, QLabel, QMenuBar, QMenu,
    QDialog, QLineEdit, QPushButton, QMessageBox, QTableWidget,
    QTableWidgetItem, QHeaderView, QFileDialog, QHBoxLayout, 
    QListWidget, QListWidgetItem, QScrollArea
)
from PyQt6.QtGui import QAction, QIcon, QPixmap
from PyQt6.QtCore import Qt, pyqtSignal
from app.utils.logger import get_logger
from app.utils.database import Database
from app.controllers.img_rostro_controller import ImgRostroController
from pathlib import Path

logger = get_logger("nova.ui.img_rostro")

class ImgRostroFormDialog(QDialog):
    def __init__(self, parent=None, mode='add', rostro_data=None):
        super().__init__(parent)
        self.mode = mode
        self.rostro_data = rostro_data
        self.selected_images = []
        self.setWindowTitle("Agregar Rostro" if mode == 'add' else "Editar Rostro")
        self.setModal(True)
        self.setMinimumSize(600, 500)
        self.init_ui()
    
    def init_ui(self):
        layout = QVBoxLayout()
        
        # Campos del formulario
        form_layout = QVBoxLayout()
        
        self.lbl_nombre = QLabel("Nombre:")
        self.txt_nombre = QLineEdit()
        
        self.lbl_alias = QLabel("Alias (prefijo para imágenes):")
        self.txt_alias = QLineEdit()
        
        # Lista de imágenes
        self.lbl_imagenes = QLabel("Imágenes:")
        self.list_imagenes = QListWidget()
        self.list_imagenes.setMaximumHeight(150)
        
        # Botones para imágenes
        btn_img_layout = QHBoxLayout()
        self.btn_add_img = QPushButton("Agregar Imágenes")
        self.btn_add_img.clicked.connect(self.add_images)
        self.btn_remove_img = QPushButton("Quitar Seleccionadas")
        self.btn_remove_img.clicked.connect(self.remove_selected_images)
        
        btn_img_layout.addWidget(self.btn_add_img)
        btn_img_layout.addWidget(self.btn_remove_img)
        
        # Vista previa de imagen seleccionada
        self.lbl_preview = QLabel("Vista previa:")
        self.img_preview = QLabel()
        self.img_preview.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.img_preview.setFixedSize(200, 200)
        self.img_preview.setStyleSheet("border: 1px solid #ccc;")
        self.list_imagenes.itemSelectionChanged.connect(self.show_preview)
        
        # Botones de acción
        btn_layout = QHBoxLayout()
        self.btn_save = QPushButton("Guardar")
        self.btn_save.clicked.connect(self.accept)
        self.btn_cancel = QPushButton("Cancelar")
        self.btn_cancel.clicked.connect(self.reject)
        
        btn_layout.addWidget(self.btn_save)
        btn_layout.addWidget(self.btn_cancel)
        
        # Agregar al layout principal
        form_layout.addWidget(self.lbl_nombre)
        form_layout.addWidget(self.txt_nombre)
        form_layout.addWidget(self.lbl_alias)
        form_layout.addWidget(self.txt_alias)
        form_layout.addWidget(self.lbl_imagenes)
        form_layout.addWidget(self.list_imagenes)
        form_layout.addLayout(btn_img_layout)
        form_layout.addWidget(self.lbl_preview)
        form_layout.addWidget(self.img_preview)
        
        layout.addLayout(form_layout)
        layout.addLayout(btn_layout)
        
        self.setLayout(layout)
        
        # Si es modo edición, cargar datos
        if self.mode == 'edit' and self.rostro_data:
            self.txt_nombre.setText(self.rostro_data['nombre'])
            self.txt_alias.setText(self.rostro_data['alias'])
    
    def add_images(self):
        """Abre diálogo para seleccionar imágenes"""
        files, _ = QFileDialog.getOpenFileNames(
            self, "Seleccionar imágenes", "", 
            "Imágenes (*.png *.jpg *.jpeg *.bmp)")
        
        if files:
            self.selected_images.extend(files)
            self.update_images_list()
    
    def remove_selected_images(self):
        """Elimina las imágenes seleccionadas de la lista"""
        selected_items = self.list_imagenes.selectedItems()
        if not selected_items:
            return
            
        for item in selected_items:
            self.selected_images.remove(item.text())
            self.list_imagenes.takeItem(self.list_imagenes.row(item))
        
        self.img_preview.clear()
    
    def update_images_list(self):
        """Actualiza la lista de imágenes"""
        self.list_imagenes.clear()
        for img_path in self.selected_images:
            item = QListWidgetItem(img_path)
            self.list_imagenes.addItem(item)
    
    def show_preview(self):
        """Muestra vista previa de la imagen seleccionada"""
        selected_items = self.list_imagenes.selectedItems()
        if not selected_items:
            return
            
        img_path = selected_items[0].text()
        pixmap = QPixmap(img_path)
        if not pixmap.isNull():
            pixmap = pixmap.scaled(
                self.img_preview.width(), self.img_preview.height(),
                Qt.AspectRatioMode.KeepAspectRatio)
            self.img_preview.setPixmap(pixmap)
    
    def get_data(self):
        """Devuelve los datos del formulario"""
        return {
            'nombre': self.txt_nombre.text().strip(),
            'alias': self.txt_alias.text().strip(),
            'imagenes': self.selected_images
        }

class ImgRostroManagementDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.db = Database()
        self.img_rostro_controller = ImgRostroController(self.db)
        self.setWindowTitle("Gestión de Rostros")
        self.setModal(True)
        self.setMinimumSize(800, 600)
        self.init_ui()
        self.load_rostros()
    
    def init_ui(self):
        layout = QVBoxLayout()
        
        # Tabla de rostros
        self.table = QTableWidget()
        self.table.setColumnCount(3)
        self.table.setHorizontalHeaderLabels(["ID", "Nombre", "Alias"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        
        # Botones
        btn_layout = QHBoxLayout()
        
        self.btn_add = QPushButton("Agregar Rostro")
        self.btn_add.clicked.connect(self.add_rostro)
        
        self.btn_edit = QPushButton("Editar Rostro")
        self.btn_edit.clicked.connect(self.edit_rostro)
        
        self.btn_delete = QPushButton("Eliminar Rostro")
        self.btn_delete.clicked.connect(self.delete_rostro)
        
        self.btn_view = QPushButton("Ver Imágenes")
        self.btn_view.clicked.connect(self.view_images)
        
        btn_layout.addWidget(self.btn_add)
        btn_layout.addWidget(self.btn_edit)
        btn_layout.addWidget(self.btn_delete)
        btn_layout.addWidget(self.btn_view)
        
        layout.addWidget(self.table)
        layout.addLayout(btn_layout)
        
        self.setLayout(layout)
    
    def load_rostros(self):
        rostros = self.img_rostro_controller.list_rostros()
        self.table.setRowCount(len(rostros))
        
        for row, rostro in enumerate(rostros):
            self.table.setItem(row, 0, QTableWidgetItem(str(rostro['id_rostro'])))
            self.table.setItem(row, 1, QTableWidgetItem(rostro['nombre']))
            self.table.setItem(row, 2, QTableWidgetItem(rostro['alias']))
    
    def add_rostro(self):
        dialog = ImgRostroFormDialog(self, mode='add')
        if dialog.exec() == QDialog.DialogCode.Accepted:
            data = dialog.get_data()
            if not data['nombre'] or not data['alias']:
                QMessageBox.warning(self, "Error", "Nombre y alias son obligatorios")
                return
                
            if not data['imagenes']:
                QMessageBox.warning(self, "Error", "Debe agregar al menos una imagen")
                return
                
            if self.img_rostro_controller.add_rostro(data['nombre'], data['alias'], data['imagenes']):
                QMessageBox.information(self, "Éxito", "Rostro agregado correctamente")
                self.load_rostros()
            else:
                QMessageBox.critical(self, "Error", "No se pudo agregar el rostro")
    
    def edit_rostro(self):
        selected = self.table.currentRow()
        if selected < 0:
            QMessageBox.warning(self, "Error", "Seleccione un rostro")
            return
            
        id_rostro = int(self.table.item(selected, 0).text())
        rostro_data = self.img_rostro_controller.get_rostro_by_id(id_rostro)
        
        if not rostro_data:
            QMessageBox.critical(self, "Error", "No se pudo cargar el rostro")
            return
            
        dialog = ImgRostroFormDialog(self, mode='edit', rostro_data=rostro_data)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            data = dialog.get_data()
            if not data['nombre'] or not data['alias']:
                QMessageBox.warning(self, "Error", "Nombre y alias son obligatorios")
                return
                
            if self.img_rostro_controller.update_rostro(id_rostro, data['nombre'], data['alias']):
                QMessageBox.information(self, "Éxito", "Rostro actualizado correctamente")
                self.load_rostros()
            else:
                QMessageBox.critical(self, "Error", "No se pudo actualizar el rostro")
    
    def delete_rostro(self):
        selected = self.table.currentRow()
        if selected < 0:
            QMessageBox.warning(self, "Error", "Seleccione un rostro")
            return
            
        id_rostro = int(self.table.item(selected, 0).text())
        nombre = self.table.item(selected, 1).text()
        
        confirm = QMessageBox.question(
            self, "Confirmar", 
            f"¿Está seguro de eliminar el rostro {nombre}?\n¡Esta acción también eliminará todas sus imágenes asociadas!",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        
        if confirm == QMessageBox.StandardButton.Yes:
            if self.img_rostro_controller.delete_rostro(id_rostro):
                QMessageBox.information(self, "Éxito", "Rostro eliminado correctamente")
                self.load_rostros()
            else:
                QMessageBox.critical(self, "Error", "No se pudo eliminar el rostro")
    
    def view_images(self):
        selected = self.table.currentRow()
        if selected < 0:
            QMessageBox.warning(self, "Error", "Seleccione un rostro")
            return
            
        id_rostro = int(self.table.item(selected, 0).text())
        nombre = self.table.item(selected, 1).text()
        imagenes = self.img_rostro_controller.get_imagenes_by_rostro(id_rostro)
        
        if not imagenes:
            QMessageBox.information(self, "Información", f"El rostro {nombre} no tiene imágenes asociadas")
            return
            
        dialog = QDialog(self)
        dialog.setWindowTitle(f"Imágenes de {nombre}")
        dialog.setMinimumSize(600, 500)
        
        layout = QVBoxLayout()
        
        # Lista de imágenes con scroll
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        
        content = QWidget()
        content_layout = QVBoxLayout()
        
        for img_data in imagenes:
            img_path = img_data['imagen']
            lbl_img = QLabel()
            pixmap = QPixmap(img_path)
            
            if not pixmap.isNull():
                pixmap = pixmap.scaled(400, 400, Qt.AspectRatioMode.KeepAspectRatio)
                lbl_img.setPixmap(pixmap)
                lbl_img.setAlignment(Qt.AlignmentFlag.AlignCenter)
                content_layout.addWidget(lbl_img)
        
        content.setLayout(content_layout)
        scroll.setWidget(content)
        
        btn_close = QPushButton("Cerrar")
        btn_close.clicked.connect(dialog.close)
        
        layout.addWidget(scroll)
        layout.addWidget(btn_close, alignment=Qt.AlignmentFlag.AlignRight)
        
        dialog.setLayout(layout)
        dialog.exec()

class ImgRostroWindow(QMainWindow):
    def __init__(self, username, profile):
        super().__init__()
        self.username = username
        self.profile = profile  # 0=admin, 1=operador
        self.setWindowTitle(f"Nova AI - Gestión de Rostros - {username}")
        self.setGeometry(100, 100, 800, 600)
        self.init_ui()
        logger.info(f"Ventana de gestión de rostros creada para {username}")
    
    def init_ui(self):
        # Barra de estado
        self.statusBar().showMessage(f"Usuario: {self.username} | Perfil: {'Administrador' if self.profile == 0 else 'Operador'}")
        
        # Contenido principal
        central_widget = QWidget()
        layout = QVBoxLayout()
        
        # Mostrar diálogo de gestión directamente
        self.management_dialog = ImgRostroManagementDialog(self)
        
        layout.addWidget(self.management_dialog)
        central_widget.setLayout(layout)
        self.setCentralWidget(central_widget)