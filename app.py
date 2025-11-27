"""
Aplicación Flask REFACTORIZADA - Application Factory con Blueprints
"""
import asyncio
import time
import atexit
import os
import logging
from collections import defaultdict
from flask import Flask, g
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

from config import Config
from models import CircuitBreaker, PerformanceMetrics
from resources import init_resources, cleanup_resources
from faiss_service import init_faiss_index
from logging_config import setup_logging
from cors_config import setup_cors
from auth import validate_api_keys_on_startup

# Blueprints
from blueprints.search import search_bp, init_search_blueprint
from blueprints.faiss_bp import faiss_bp
from blueprints.admin import admin_bp, init_admin_blueprint
from blueprints.diagnostics import diagnostics_bp, init_diagnostics_blueprint

# Configuración de logging
logger = setup_logging()

# Variables globales (idealmente deberían estar en Redis, pero eso es fase 2)
circuit_breakers = defaultdict(CircuitBreaker)
metrics = PerformanceMetrics()
app_start_time = time.time()


def create_app():
    """
    Application Factory Pattern
    
    Returns:
        Flask app configurada y lista para usar
    """
    app = Flask(__name__)
    
    # ========== VALIDACIÓN DE CONFIGURACIÓN ==========
    warnings = validate_api_keys_on_startup()
    if warnings:
        logger.warning("Configuration warnings detected:")
        for warning in warnings:
            logger.warning(warning)
    
    # ========== CORS ==========
    setup_cors(app)
    
    # ========== RATE LIMITING ==========
    redis_url = None
    if os.getenv('REDIS_HOST'):
        redis_password = os.getenv('REDIS_PASSWORD', '')
        redis_host = os.getenv('REDIS_HOST')
        redis_port = os.getenv('REDIS_PORT', 6379)
        
        if redis_password:
            redis_url = f"redis://:{redis_password}@{redis_host}:{redis_port}"
        else:
            redis_url = f"redis://{redis_host}:{redis_port}"
    
    limiter = Limiter(
        key_func=get_remote_address,
        app=app,
        default_limits=["200 per day", "50 per hour"],
        storage_uri=redis_url or "memory://",
        storage_options={'socket_connect_timeout': 2}
    )
    
    # ========== INICIALIZAR RECURSOS ==========
    with app.app_context():
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            loop.run_until_complete(init_resources())
            init_faiss_index()
            logger.info("Sistema optimizado iniciado", extra={
                "model": Config.EMBEDDING_MODEL,
                "threshold": Config.SIMILARITY_THRESHOLD
            })
        except Exception as e:
            logger.error("Error inicializando recursos", extra={"error": str(e)})
        finally:
            # No cerrar el loop aquí, lo necesitamos para las requests
            pass
    
    # ========== MIDDLEWARE ==========
    
    @app.before_request
    def before_request():
        """Tracking de inicio de request"""
        g.start_time = time.time()
        g.cache_hit = False
    
    @app.after_request
    def after_request(response):
        """Tracking de métricas por request"""
        if hasattr(g, 'start_time'):
            latency = time.time() - g.start_time
            metrics.record_request(latency, response.status_code >= 400)
            
            if hasattr(g, 'cache_hit') and g.cache_hit:
                metrics.record_cache(hit=True)
        
        return response
    
    @app.errorhandler(429)
    def ratelimit_handler(e):
        """Handler para rate limit excedido"""
        logger.warning("Rate limit excedido", extra={
            "ip": get_remote_address(),
            "endpoint": str(e)
        })
        return {
            "error": "Rate limit excedido. Intente nuevamente más tarde.",
            "retry_after": str(e)
        }, 429
    
    @app.errorhandler(500)
    def internal_error_handler(e):
        """Handler para errores internos"""
        logger.error("Error interno del servidor", extra={
            "error": str(e)
        })
        return {
            "error": "Error interno del servidor",
            "message": "Por favor contacte al administrador"
        }, 500
    
    # ========== REGISTRAR BLUEPRINTS ==========
    
    # Inicializar blueprints que necesitan limiter
    init_search_blueprint(limiter)
    init_admin_blueprint(limiter)
    init_diagnostics_blueprint(metrics, circuit_breakers, app_start_time)
    
    # Registrar blueprints
    app.register_blueprint(search_bp)
    app.register_blueprint(faiss_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(diagnostics_bp)
    
    logger.info("Blueprints registrados", extra={
        "blueprints": [
            "search (/api/similarity-search, /api/plagiarism-check)",
            "faiss (/api/faiss/*)",
            "admin (/api/cache/clear, /api/reset-limits, /api/benchmark)",
            "diagnostics (/api/health, /api/metrics, /api/diagnostics/*)"
        ]
    })
    
    # ========== RUTA RAÍZ ==========
    
    @app.route('/')
    def index():
        """Página de bienvenida"""
        return {
            "message": "xplagiax_sourcex API",
            "version": "2.0.0-refactored",
            "documentation": "/api/health",
            "endpoints": {
                "search": "/api/similarity-search",
                "plagiarism": "/api/plagiarism-check",
                "health": "/api/health",
                "metrics": "/api/metrics",
                "faiss": "/api/faiss/stats"
            }
        }, 200
    
    return app


# ========== CLEANUP ==========

def shutdown():
    """Limpia recursos al cerrar"""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        loop.run_until_complete(cleanup_resources())
        
        # Cerrar deduplicator
        from deduplication_service import _deduplicator
        if _deduplicator:
            loop.run_until_complete(_deduplicator.close())
        
        logger.info("Recursos liberados")
    finally:
        loop.close()


atexit.register(shutdown)


if __name__ == '__main__':
    print("=" * 60)
    print("🚀 SERVIDOR REFACTORIZADO v2.0 INICIADO")
    print("=" * 60)
    print(f"📊 Modelo: {Config.EMBEDDING_MODEL}")
    print(f"🎯 Umbral de similitud: {Config.SIMILARITY_THRESHOLD * 100}%")
    print(f"📢 Batch size: {Config.EMBEDDING_BATCH_SIZE}")
    print(f"🌐 HTTP Pool: {Config.POOL_CONNECTIONS} conexiones")
    print(f"⚡ Circuit Breaker: ✅ Activo")
    print(f"🚀 Rate Limiting: ✅ Thread-safe")
    print(f"🔐 Auth: ✅ Admin endpoints protegidos")
    print("=" * 60)
    print("\n🔌 Endpoints disponibles:")
    print("   POST /api/similarity-search   - Búsqueda principal")
    print("   POST /api/plagiarism-check    - Detección de plagio")
    print("   GET  /api/health              - Estado del sistema")
    print("   GET  /api/metrics             - Métricas Prometheus")
    print("   POST /api/reset-limits        - Reiniciar límites (🔐 auth)")
    print("   POST /api/cache/clear         - Limpiar caché (🔐 auth)")
    print("   POST /api/benchmark           - Test de performance")
    print("   GET  /api/faiss/stats         - Estadísticas FAISS")
    print("   POST /api/faiss/clear         - Limpiar índice (🔐 auth)")
    print("   POST /api/faiss/save          - Guardar índice (🔐 auth)")
    print("   POST /api/faiss/backup        - Backup FAISS (🔐 auth)")
    print("   POST /api/validate-apis       - Validar APIs externas")
    print("   GET  /api/diagnostics/full    - Diagnóstico completo")
    print("=" * 60)
    print("\n⚠️  IMPORTANTE:")
    print("   - Configura ADMIN_API_KEY en .env para endpoints protegidos")
    print("   - Configura ALLOWED_ORIGINS para CORS en producción")
    print("   - Usa Gunicorn en producción, no este servidor de desarrollo")
    print("=" * 60)
    
    app = create_app()
    
    # Usar servidor de desarrollo (solo para testing local)
    app.run(
        host='0.0.0.0', 
        port=8000, 
        debug=True, 
        threaded=True
    )