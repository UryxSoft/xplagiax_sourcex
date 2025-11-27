"""
Search Routes - Similarity search and plagiarism check endpoints
"""
from flask import Blueprint
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

from app.api.controllers.search_controller import search_controller

# Create blueprint
search_bp = Blueprint('search', __name__, url_prefix='/api')

# Rate limiter (will be initialized from app.py)
limiter = None


def init_search_routes(app_limiter: Limiter):
    """Initialize rate limiter for search routes"""
    global limiter
    limiter = app_limiter


@search_bp.route('/similarity-search', methods=['POST'])
@limiter.limit("10 per minute")
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
@limiter.limit("5 per minute")
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