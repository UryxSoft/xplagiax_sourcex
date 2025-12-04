"""
Search Routes - Similarity search and plagiarism check endpoints
"""
from functools import wraps
from flask import Blueprint,g
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
import time

from app.api.controllers.search_controller import search_controller

# Create blueprint
search_bp = Blueprint('search', __name__, url_prefix='/api')

# Rate limiter (will be initialized from app.py)
_limiter = None


def init_search_routes(app_limiter: Limiter):
    """Initialize rate limiter for search routes"""
    global _limiter 
    _limiter = app_limiter

def rate_limit(limit_string):
    """Lazy rate limit decorator"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if _limiter is None:
                raise RuntimeError("Limiter not initialized. Call init_search_routes() first.")
            # Aplicar rate limiting dinámicamente
            return _limiter.limit(limit_string)(f)(*args, **kwargs)
        return decorated_function
    return decorator


def async_rate_limit(limit_per_minute: int):
    """Rate limiter asíncrono que no bloquea"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            # Usar Redis para rate limiting distribuido
            key = f"ratelimit:{request.remote_addr}:{f.__name__}"
            redis_client = get_redis_client()
            
            if redis_client:
                current = redis_client.incr(key)
                if current == 1:
                    redis_client.expire(key, 60)
                
                if current > limit_per_minute:
                    return jsonify({
                        "error": "Rate limit exceeded",
                        "retry_after": redis_client.ttl(key)
                    }), 429
            
            return f(*args, **kwargs)
        return decorated_function
    return decorator

@search_bp.route('/similarity-search', methods=['POST'])
#@rate_limit.limit("10 per minute")
@async_rate_limit(10) 
def similarity_search():
    """
    POST /api/similarity-search
    
    Search for similar academic papers
    
    Request Body:
        {
            "data": [theme, idiom, [[page, para, text], ...]],
            "threshold": 0.70,
            "use_faiss": true,
            "sources": ["crossref", "pubmed", ...]
        }
    
    Returns:
        {
            "results": [...],
            "count": N,
            "threshold_used": 0.70,
            "faiss_enabled": true
        }
    """
    return search_controller.similarity_search()


@search_bp.route('/plagiarism-check', methods=['POST'])
@rate_limit.limit("5 per minute")
def plagiarism_check():
    """
    POST /api/plagiarism-check
    
    Comprehensive plagiarism detection with text chunking
    
    Request Body:
        {
            "data": [theme, idiom, [[page, para, text], ...]],
            "threshold": 0.70,
            "chunk_mode": "sentences",
            "min_chunk_words": 15,
            "sources": [...]
        }
    
    Returns:
        {
            "plagiarism_detected": true/false,
            "chunks_analyzed": N,
            "total_matches": M,
            "summary": {...},
            "by_level": {...}
        }
    """
    return search_controller.plagiarism_check()