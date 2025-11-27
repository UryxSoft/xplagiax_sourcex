"""
Admin Routes - Administrative operations
"""
from flask import Blueprint
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

from app.core.security import require_api_key
from app.api.controllers.admin_controller import admin_controller

# Create blueprint
admin_bp = Blueprint('admin', __name__, url_prefix='/api')

# Rate limiter
limiter = None


def init_admin_routes(app_limiter: Limiter):
    """Initialize rate limiter for admin routes"""
    global limiter
    limiter = app_limiter


@admin_bp.route('/reset-limits', methods=['POST'])
@require_api_key
def reset_limits():
    """
    POST /api/reset-limits
    
    Reset rate limits and circuit breakers (requires API key)
    
    Returns:
        {
            "message": "Limits and circuit breakers reset successfully"
        }
    """
    return admin_controller.reset_limits()


@admin_bp.route('/cache/clear', methods=['POST'])
@require_api_key
def clear_cache():
    """
    POST /api/cache/clear
    
    Clear Redis cache (DESTRUCTIVE, requires API key)
    
    Returns:
        {
            "message": "Cache cleared successfully"
        }
    """
    return admin_controller.clear_cache()


@admin_bp.route('/benchmark', methods=['POST'])
@limiter.limit("5 per hour")
def benchmark():
    """
    POST /api/benchmark
    
    Run performance benchmark (rate limited)
    
    Request Body:
        {
            "num_texts": 10
        }
    
    Returns:
        {
            "benchmark_type": "faiss_only",
            "num_queries": 10,
            "elapsed_seconds": 0.123,
            "throughput_queries_per_sec": 81.3,
            ...
        }
    """
    return admin_controller.benchmark()


@admin_bp.route('/deduplication/stats', methods=['GET'])
def deduplication_stats():
    """
    GET /api/deduplication/stats
    
    Get deduplication statistics
    
    Returns:
        {
            "total_papers": N,
            "unique_sources": M,
            "bloom_filter_size_mb": X
        }
    """
    return admin_controller.deduplication_stats()