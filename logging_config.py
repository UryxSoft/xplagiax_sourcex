"""
Configuración de Logging Estructurado
"""
import logging
import sys
from datetime import datetime
try:
    from pythonjsonlogger import jsonlogger
    JSON_LOGGER_AVAILABLE = True
except ImportError:
    JSON_LOGGER_AVAILABLE = False


def setup_logging(level=logging.INFO, json_format=False):
    """
    Configura sistema de logging estructurado
    
    Args:
        level: Nivel de logging (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        json_format: Si True, usa formato JSON. Si False, formato texto
    
    Returns:
        Logger configurado
    """
    logger = logging.getLogger()
    logger.setLevel(level)
    
    # Remover handlers existentes
    for handler in logger.handlers[:]:
        logger.removeHandler(handler)
    
    # Handler para stdout
    handler = logging.StreamHandler(sys.stdout)
    
    if json_format and JSON_LOGGER_AVAILABLE:
        # Formato JSON estructurado (ideal para producción)
        formatter = jsonlogger.JsonFormatter(
            '%(timestamp)s %(level)s %(name)s %(message)s',
            rename_fields={'levelname': 'level', 'asctime': 'timestamp'}
        )
    else:
        # Formato texto legible (ideal para desarrollo)
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
    
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    
    # Handler adicional para archivo (opcional)
    try:
        import os
        os.makedirs('logs', exist_ok=True)
        
        file_handler = logging.FileHandler(
            f'logs/app_{datetime.now().strftime("%Y%m%d")}.log'
        )
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
    except Exception as e:
        logger.warning(f"No se pudo configurar file handler: {e}")
    
    return logger