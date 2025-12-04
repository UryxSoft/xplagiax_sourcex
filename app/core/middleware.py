"""
Flask middleware - Ultra-optimizado y selectivo
"""
import time
import logging
from flask import Flask, g, request
from app.models.performance_metrics import PerformanceMetrics

logger = logging.getLogger(__name__)

# Global metrics
metrics = PerformanceMetrics()

# ✅ Solo medir estos endpoints (críticos)
MONITORED_ENDPOINTS = {
    'search.similarity_search',
    'search.plagiarism_check',
    'admin.benchmark',
    'faiss.search'
}

# ✅ Endpoints que no necesitan logging
SILENT_ENDPOINTS = {
    'diagnostics.health',
    'diagnostics.metrics',
    'static'
}


def setup_middleware(app: Flask):
    """
    Setup ultra-lightweight middleware
    """
    
    @app.before_request
    def before_request():
        """
        Middleware ultra-ligero - solo trackea endpoints críticos
        """
        # ✅ Solo medir tiempo en endpoints monitoreados
        if request.endpoint in MONITORED_ENDPOINTS:
            g.start_time = time.perf_counter()  # Más preciso
            g.cache_hit = False
            g.monitored = True
        else:
            g.monitored = False
    
    @app.after_request
    def after_request(response):
        """
        After request con optimizaciones
        """
        # Solo procesar si se monitoreó
        if hasattr(g, 'monitored') and g.monitored:
            if hasattr(g, 'start_time'):
                latency = time.perf_counter() - g.start_time
                is_error = response.status_code >= 400
                
                # Record metrics
                metrics.record_request(latency, is_error)
                
                # Track cache hits
                if hasattr(g, 'cache_hit') and g.cache_hit:
                    metrics.record_cache(hit=True)
                
                # ✅ Header de timing (útil para debugging)
                response.headers['X-Response-Time'] = f"{latency * 1000:.2f}ms"
        
        # ✅ Headers de cache según endpoint
        if request.endpoint:
            if 'static' in request.endpoint:
                # Cache agresivo para estáticos
                response.headers['Cache-Control'] = 'public, max-age=31536000, immutable'
                response.headers['Vary'] = 'Accept-Encoding'
            
            elif request.endpoint in ['diagnostics.health', 'diagnostics.metrics']:
                # No cache para monitoring
                response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
                response.headers['Pragma'] = 'no-cache'
                response.headers['Expires'] = '0'
            
            elif request.endpoint in MONITORED_ENDPOINTS:
                # Cache moderado para búsquedas
                response.headers['Cache-Control'] = 'private, max-age=300'  # 5 min
        
        # ✅ Compresión hint solo para respuestas grandes
        if len(response.get_data()) > 1024:  # >1KB
            response.headers['Vary'] = 'Accept-Encoding'
        
        # ✅ Security headers (sin overhead)
        response.headers['X-Content-Type-Options'] = 'nosniff'
        response.headers['X-Frame-Options'] = 'SAMEORIGIN'
        response.headers['X-API-Version'] = '2.1.0'
        
        return response
    
    @app.teardown_appcontext
    def teardown(error=None):
        """Cleanup after request"""
        if error:
            logger.error(f"Request error: {error}")
    
    logger.info("✅ Lightweight middleware configured")


def get_metrics() -> PerformanceMetrics:
    """Get global metrics instance"""
    return metrics