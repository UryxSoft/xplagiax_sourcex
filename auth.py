"""
Decoradores de autenticación y autorización
"""
import os
import logging
from functools import wraps
from flask import request, jsonify

logger = logging.getLogger(__name__)


def require_api_key(f):
    """
    Decorador para proteger endpoints administrativos
    Requiere header: X-API-Key
    
    Uso:
        @app.route('/api/admin/clear')
        @require_api_key
        def clear_cache():
            ...
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        api_key = request.headers.get('X-API-Key')
        expected_key = os.getenv('ADMIN_API_KEY')
        
        # Validar que la key esté configurada
        if not expected_key:
            logger.error("ADMIN_API_KEY not configured in environment")
            return jsonify({
                "error": "Server misconfiguration",
                "message": "Contact administrator"
            }), 500
        
        # Validar que se envió la key
        if not api_key:
            logger.warning("Unauthorized admin access attempt", extra={
                "ip": request.remote_addr,
                "endpoint": request.endpoint
            })
            return jsonify({
                "error": "Unauthorized",
                "message": "X-API-Key header required"
            }), 401
        
        # Validar que la key sea correcta
        if api_key != expected_key:
            logger.warning("Invalid API key attempt", extra={
                "ip": request.remote_addr,
                "endpoint": request.endpoint
            })
            return jsonify({
                "error": "Forbidden",
                "message": "Invalid API key"
            }), 403
        
        # Key válida, continuar
        logger.info("Admin endpoint accessed", extra={
            "endpoint": request.endpoint,
            "ip": request.remote_addr
        })
        
        return f(*args, **kwargs)
    
    return decorated_function


def validate_api_keys_on_startup():
    """
    Valida que todas las API keys necesarias estén configuradas
    Llamar en create_app()
    
    Returns:
        List[str]: Warnings sobre keys faltantes
    """
    warnings = []
    
    # Admin API Key (crítico)
    if not os.getenv('ADMIN_API_KEY'):
        warnings.append("⚠️  ADMIN_API_KEY not set - admin endpoints will fail")
    
    # Redis password (recomendado)
    if not os.getenv('REDIS_PASSWORD'):
        warnings.append("⚠️  REDIS_PASSWORD not set - using Redis without authentication")
    
    # Flask secret key (crítico en producción)
    if not os.getenv('FLASK_SECRET_KEY'):
        warnings.append("⚠️  FLASK_SECRET_KEY not set - sessions are insecure")
    
    # API keys opcionales
    optional_keys = {
        'CORE_API_KEY': 'CORE search will be disabled',
        'UNPAYWALL_EMAIL': 'Unpaywall search will be disabled',
    }
    
    for key, message in optional_keys.items():
        if not os.getenv(key):
            warnings.append(f"ℹ️  {key} not set - {message}")
    
    return warnings