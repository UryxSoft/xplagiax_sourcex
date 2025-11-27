"""
FAISS Routes - Vector index management endpoints
"""
from flask import Blueprint

from app.core.security import require_api_key
from app.api.controllers.faiss_controller import faiss_controller

# Create blueprint
faiss_bp = Blueprint('faiss', __name__, url_prefix='/api/faiss')


@faiss_bp.route('/stats', methods=['GET'])
def stats():
    """
    GET /api/faiss/stats
    
    Get FAISS index statistics
    
    Returns:
        {
            "total_papers": N,
            "dimension": 384,
            "metadata_count": N,
            "unique_hashes": M,
            "strategy": "flat_idmap",
            "corrupted": false,
            "has_duplicates": false
        }
    """
    return faiss_controller.get_stats()


@faiss_bp.route('/search', methods=['POST'])
def search():
    """
    POST /api/faiss/search
    
    Direct FAISS search
    
    Request Body:
        {
            "query": "machine learning",
            "k": 10,
            "threshold": 0.7
        }
    
    Returns:
        {
            "query": "...",
            "results": [...],
            "count": N
        }
    """
    return faiss_controller.search()


@faiss_bp.route('/save', methods=['POST'])
@require_api_key
def save():
    """
    POST /api/faiss/save
    
    Save FAISS index to disk (requires API key)
    
    Returns:
        {
            "message": "Index saved successfully",
            "stats": {...}
        }
    """
    return faiss_controller.save()


@faiss_bp.route('/clear', methods=['POST'])
@require_api_key
def clear():
    """
    POST /api/faiss/clear
    
    Clear entire FAISS index (DESTRUCTIVE, requires API key)
    
    Returns:
        {
            "message": "Index cleared successfully"
        }
    """
    return faiss_controller.clear()


@faiss_bp.route('/backup', methods=['POST'])
@require_api_key
def backup():
    """
    POST /api/faiss/backup
    
    Create backup of FAISS index (requires API key)
    
    Returns:
        {
            "message": "Backup created successfully",
            "backup_path": "backups/faiss_20241128_123456",
            "papers": N
        }
    """
    return faiss_controller.backup()


@faiss_bp.route('/remove-duplicates', methods=['POST'])
@require_api_key
def remove_duplicates():
    """
    POST /api/faiss/remove-duplicates
    
    Remove duplicates from index (requires API key)
    
    Returns:
        {
            "message": "Duplicates removed",
            "duplicates_removed": N,
            "stats": {...}
        }
    """
    return faiss_controller.remove_duplicates()