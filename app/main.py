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

def main():
    try:
        app = QApplication(sys.argv)
        db = Database()
        auth_controller = AuthController(db)
        login_window = LoginWindow(auth_controller)
        
        from app.views.main_window import MainWindow
        
        def on_login_success(auth_result: dict):
            """Manejador de login exitoso"""
            if auth_result.get('authenticated'):
                username = auth_result['username']
                profile = auth_result.get('profile', 1)
                
                logger.info(f"Usuario autenticado: {username} (Perfil: {profile})")
                login_window.close()
                
                main_window = MainWindow(username, profile)
                main_window.show()
                
                app.main_window = main_window
        
        login_window.login_success.connect(on_login_success)
        login_window.show()
        
        sys.exit(app.exec())
        
    except Exception as e:
        logger.critical(f"Error al iniciar aplicación: {str(e)}", exc_info=True)
        QMessageBox.critical(None, "Error fatal", f"No se pudo iniciar la aplicación:\n{str(e)}")
        return 1

if __name__ == "__main__":
    main()