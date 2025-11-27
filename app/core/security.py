"""
Security utilities and authentication decorators
"""
import os
import logging
from functools import wraps
from flask import request, jsonify

logger = logging.getLogger(__name__)


def require_api_key(f):
    """
    Decorator to protect admin endpoints
    
    Usage:
        @admin_bp.route('/cache/clear', methods=['POST'])
        @require_api_key
        def clear_cache():
            ...
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        api_key = request.headers.get('X-API-Key')
        expected_key = os.getenv('ADMIN_API_KEY')
        
        # Validate key is configured
        if not expected_key:
            logger.error("ADMIN_API_KEY not configured")
            return jsonify({
                "error": "Server misconfiguration",
                "message": "Contact administrator"
            }), 500
        
        # Validate key was sent
        if not api_key:
            logger.warning(
                "Unauthorized admin access attempt",
                extra={"ip": request.remote_addr}
            )
            return jsonify({
                "error": "Unauthorized",
                "message": "X-API-Key header required"
            }), 401
        
        # Validate key is correct
        if api_key != expected_key:
            logger.warning(
                "Invalid API key attempt",
                extra={"ip": request.remote_addr}
            )
            return jsonify({
                "error": "Forbidden",
                "message": "Invalid API key"
            }), 403
        
        # Authorized
        logger.info(
            "Admin endpoint accessed",
            extra={"endpoint": request.endpoint, "ip": request.remote_addr}
        )
        
        return f(*args, **kwargs)
    
    return decorated_function


def validate_security_config() -> list:
    """
    Validate security configuration at startup
    
    Returns:
        List of warnings (🔴 = critical, 🟠 = important, ℹ️ = info)
    """
    warnings = []
    
    # 1. ADMIN_API_KEY (critical)
    admin_key = os.getenv('ADMIN_API_KEY')
    if not admin_key:
        warnings.append("🔴 ADMIN_API_KEY not set - admin endpoints will fail")
    elif admin_key in ['your-key-here', 'changeme', 'admin', 'test', '']:
        warnings.append("🔴 ADMIN_API_KEY is a placeholder - set a secure key")
    elif len(admin_key) < 32:
        warnings.append("🟠 ADMIN_API_KEY is too short (< 32 chars)")
    
    # 2. FLASK_SECRET_KEY (critical in production)
    flask_env = os.getenv('FLASK_ENV', 'production')
    secret_key = os.getenv('FLASK_SECRET_KEY')
    
    if not secret_key or secret_key in ['dev-secret-change-in-production']:
        if flask_env == 'production':
            warnings.append("🔴 FLASK_SECRET_KEY not set - sessions are insecure in production")
        else:
            warnings.append("🟠 FLASK_SECRET_KEY not set - sessions are insecure")
    
    # 3. REDIS_PASSWORD (recommended)
    if not os.getenv('REDIS_PASSWORD'):
        warnings.append("🟠 REDIS_PASSWORD not set - using Redis without authentication")
    
    # 4. CORE_API_KEY (optional but validate if set)
    core_key = os.getenv('CORE_API_KEY')
    if core_key and core_key in ['YOUR_API_KEY', 'your-api-key-here']:
        warnings.append("🟠 CORE_API_KEY is a placeholder - CORE search will fail")
    
    # 5. SSL verification in production
    if flask_env == 'production' and os.getenv('SSL_VERIFY', 'true').lower() == 'false':
        warnings.append("🔴 SSL_VERIFY disabled in production - security risk!")
    
    return warnings