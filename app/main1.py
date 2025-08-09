# app/main.py
import sys
from pathlib import Path
from PyQt6.QtWidgets import QApplication, QMessageBox
from PyQt6.QtCore import Qt
import logging

# Configurar path para imports
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.append(str(PROJECT_ROOT))

from app.utils.logger import setup_logging
from app.utils.database import Database
from app.controllers.auth_controller import AuthController
from app.views.login_window import LoginWindow

logger = setup_logging()

def handle_exception(exc_type, exc_value, exc_traceback):
    """Manejador global de excepciones"""
    logger.critical("Excepción no capturada", exc_info=(exc_type, exc_value, exc_traceback))
    QMessageBox.critical(None, "Error crítico", f"Ocurrió un error inesperado:\n{str(exc_value)}")

def create_application():
    """Configura y retorna la aplicación QApplication"""
    # Configuración HiDPI para PyQt6
    try:
        from PyQt6.QtCore import QCoreApplication
        QCoreApplication.setAttribute(Qt.ApplicationAttribute.AA_EnableHighDpiScaling)
        QCoreApplication.setAttribute(Qt.ApplicationAttribute.AA_UseHighDpiPixmaps)
    except Exception as e:
        logger.warning(f"No se pudo configurar HiDPI: {str(e)}")

    app = QApplication(sys.argv)
    app.setStyle('Fusion')
    app.setApplicationName("Nova Desktop")
    app.setApplicationVersion("1.0.0")
    return app

def main():
    """Punto de entrada principal de la aplicación"""
    try:
        sys.excepthook = handle_exception
        logger.info("Iniciando aplicación Nova Desktop")
        
        app = create_application()
        
        # Inicializar componentes
        db = Database()
        auth_controller = AuthController(db)
        login_window = LoginWindow(auth_controller)
        
        def on_login_success(username):
            logger.info(f"Usuario autenticado: {username}")
            login_window.close()
            # Aquí deberías abrir tu ventana principal
            from app.views.main_window import MainWindow
            main_window = MainWindow(username)
            main_window.show()
        
        login_window.login_success.connect(on_login_success)
        
        login_window.show()
        logger.info("Interfaz de login mostrada")
        
        sys.exit(app.exec())
        
    except Exception as e:
        logger.critical(f"Error al iniciar aplicación: {str(e)}", exc_info=True)
        QMessageBox.critical(None, "Error fatal", f"No se pudo iniciar la aplicación:\n{str(e)}")
        return 1

if __name__ == "__main__":
    main()