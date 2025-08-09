# app/__init__.py
"""
Paquete principal de la aplicación Nova Desktop System

Este paquete contiene:
- El punto de entrada principal (main.py)
- Módulos de vistas (views/)
- Utilidades compartidas (utils/)
- Controladores (controllers/)
"""

__version__ = "1.0.0"
__author__ = "Tu Nombre"
__email__ = "tu@email.com"

# Exportar los módulos principales para facilitar el acceso
from .main import main  # noqa