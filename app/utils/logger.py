# app/utils/logger.py
import logging
import logging.config
from pathlib import Path
from datetime import datetime
import json
import sys
import os
from typing import Optional

class JSONFormatter(logging.Formatter):
    """Formateador personalizado para logs en formato JSON"""
    def format(self, record):
        log_record = {
            "timestamp": datetime.now().isoformat(),
            "level": record.levelname,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
            "thread": record.threadName,
        }
        
        # Agregar información de excepción si existe
        if record.exc_info:
            log_record["exception"] = self.formatException(record.exc_info)
        
        # Agregar nombre de usuario si está disponible
        if hasattr(record, 'username'):
            log_record["username"] = record.username
            
        return json.dumps(log_record, ensure_ascii=False)

def setup_logging(logs_dir: str = "logs", log_level: str = "DEBUG") -> logging.Logger:
    """
    Configura el sistema de logging para la aplicación
    
    Args:
        logs_dir: Directorio donde se guardarán los archivos de log
        log_level: Nivel de logging (DEBUG, INFO, WARNING, ERROR, CRITICAL)
    
    Returns:
        Logger configurado
    """
    # Crear directorio de logs si no existe
    logs_path = Path(logs_dir)
    logs_path.mkdir(exist_ok=True)
    
    # Nombre del archivo de log con fecha actual
    current_date = datetime.now().strftime("%Y-%m-%d")
    log_file = logs_path / f"nova_{current_date}.log"
    
    # Configuración del logging
    config = {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "json": {
                "()": JSONFormatter
            },
            "simple": {
                "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
            },
            "colored": {
                "()": "colorlog.ColoredFormatter",
                "format": "%(log_color)s%(asctime)s - %(name)s - %(levelname)s - %(message)s",
                "log_colors": {
                    'DEBUG': 'cyan',
                    'INFO': 'green',
                    'WARNING': 'yellow',
                    'ERROR': 'red',
                    'CRITICAL': 'red,bg_white',
                }
            }
        },
        "handlers": {
            "file": {
                "class": "logging.handlers.RotatingFileHandler",
                "formatter": "json",
                "filename": log_file,
                "maxBytes": 10 * 1024 * 1024,  # 10 MB
                "backupCount": 5,
                "encoding": "utf-8",
                "delay": True
            },
            "console": {
                "class": "logging.StreamHandler",
                "formatter": "colored" if "colorlog" in sys.modules else "simple",
                "level": "INFO",
                "stream": sys.stdout
            },
            "error_console": {
                "class": "logging.StreamHandler",
                "formatter": "colored" if "colorlog" in sys.modules else "simple",
                "level": "ERROR",
                "stream": sys.stderr
            }
        },
        "loggers": {
            "nova": {
                "handlers": ["file", "console"],
                "level": log_level,
                "propagate": False
            },
            "nova.auth": {
                "handlers": ["file", "console"],
                "level": "INFO",
                "propagate": False
            },
            "nova.vision": {
                "handlers": ["file", "console"],
                "level": "DEBUG",
                "propagate": False
            },
            "nova.ui": {
                "handlers": ["file", "console"],
                "level": "INFO",
                "propagate": False
            }
        },
        "root": {
            "handlers": ["file", "error_console"],
            "level": "WARNING"
        }
    }
    
    try:
        import colorlog  # Para logs coloridos en consola
    except ImportError:
        pass  # Usará el formateador simple si colorlog no está instalado
    
    # Aplicar configuración
    logging.config.dictConfig(config)
    
    # Configurar excepción global
    def handle_exception(exc_type, exc_value, exc_traceback):
        logger = logging.getLogger("nova")
        logger.critical(
            "Excepción no capturada",
            exc_info=(exc_type, exc_value, exc_traceback)
        )
    
    sys.excepthook = handle_exception
    
    return logging.getLogger("nova")

def get_logger(name: str = "nova", username: Optional[str] = None) -> logging.Logger:
    """
    Obtiene un logger configurado con el nombre especificado
    
    Args:
        name: Nombre del logger (ej. 'nova.auth')
        username: Nombre de usuario opcional para incluir en los logs
    
    Returns:
        Logger configurado
    """
    logger = logging.getLogger(name)
    
    if username:
        # Agregar username al registro de logs
        old_factory = logging.getLogRecordFactory()
        
        def record_factory(*args, **kwargs):
            record = old_factory(*args, **kwargs)
            record.username = username
            return record
            
        logging.setLogRecordFactory(record_factory)
    
    return logger

# Logger global inicializado
logger = setup_logging()