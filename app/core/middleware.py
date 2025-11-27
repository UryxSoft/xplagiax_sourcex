"""
Flask middleware (before_request, after_request, error handlers)
"""
import time
import logging
from flask import Flask, g, request

from app.models.performance_metrics import PerformanceMetrics

logger = logging.getLogger(__name__)

# Global metrics instance
metrics = PerformanceMetrics()


def setup_middleware(app: Flask):
    """
    Setup all middleware
    
    Args:
        app: Flask app instance
    """
    
    @app.before_request
    def before_request():
        """Track request start time"""
        g.start_time = time.time()
        g.cache_hit = False
    
    @app.after_request
    def after_request(response):
        """Track request metrics"""
        if hasattr(g, 'start_time'):
            latency = time.time() - g.start_time
            is_error = response.status_code >= 400
            
            metrics.record_request(latency, is_error)
            
            # Track cache hits
            if hasattr(g, 'cache_hit') and g.cache_hit:
                metrics.record_cache(hit=True)
            
            # Add custom headers
            response.headers['X-Response-Time'] = f"{latency * 1000:.2f}ms"
            response.headers['X-API-Version'] = "2.1.0"
        
        return response
    
    @app.teardown_appcontext
    def teardown(error=None):
        """Cleanup after request"""
        if error:
            logger.error(f"Request error: {error}")
    
    logger.info("✅ Middleware configured")


def get_metrics() -> PerformanceMetrics:
    """Get global metrics instance"""
    return metrics