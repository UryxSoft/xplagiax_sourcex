"""
Configuración segura de CORS
"""
import os
import logging
from flask_cors import CORS

logger = logging.getLogger(__name__)


def setup_cors(app):
    """
    Configura CORS de forma segura
    
    Args:
        app: Flask app instance
    
    Returns:
        CORS instance
    """
    allowed_origins = os.getenv("ALLOWED_ORIGINS")
    
    # Default seguro si no está configurado
    if not allowed_origins:
        logger.warning(
            "ALLOWED_ORIGINS not set, using secure defaults (localhost only). "
            "Set ALLOWED_ORIGINS env var for production."
        )
        allowed_origins = [
            "http://localhost:3000",
            "http://localhost:5000",
            "http://127.0.0.1:3000",
            "http://127.0.0.1:5000"
        ]
    else:
        allowed_origins = [origin.strip() for origin in allowed_origins.split(",")]
    
    # Validar que no haya "*" en producción
    if "*" in allowed_origins and os.getenv("FLASK_ENV") == "production":
        logger.error(
            "SECURITY WARNING: CORS configured with '*' in production! "
            "This is a security risk. Set specific domains in ALLOWED_ORIGINS."
        )
    
    logger.info("CORS configured", extra={"allowed_origins": allowed_origins})
    
    return CORS(app, resources={
        r"/api/*": {
            "origins": allowed_origins,
            "methods": ["GET", "POST", "OPTIONS"],
            "allow_headers": ["Content-Type", "Authorization", "X-API-Key"],
            "expose_headers": ["Content-Type", "X-Total-Count"],
            "max_age": 3600,
            "supports_credentials": False  # Más seguro
        }
    })