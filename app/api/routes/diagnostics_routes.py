"""
Diagnostics Routes - Health checks and monitoring
"""
from flask import Blueprint

from app.api.controllers.diagnostics_controller import diagnostics_controller

# Create blueprint
diagnostics_bp = Blueprint('diagnostics', __name__, url_prefix='/api')


@diagnostics_bp.route('/health', methods=['GET'])
def health():
    """
    GET /api/health
    
    Health check with basic metrics
    
    Returns:
        {
            "status": "healthy",
            "version": "2.1.0",
            "redis": "connected",
            "http_pool": "active",
            "faiss": {...},
            "metrics": {...}
        }
    """
    return diagnostics_controller.health()


@diagnostics_bp.route('/metrics', methods=['GET'])
def metrics():
    """
    GET /api/metrics
    
    Prometheus-compatible metrics
    
    Returns:
        Plain text metrics in Prometheus format
    """
    return diagnostics_controller.metrics()


@diagnostics_bp.route('/diagnostics/full', methods=['GET'])
def full_diagnostics():
    """
    GET /api/diagnostics/full
    
    Complete system diagnostics
    
    Returns:
        {
            "timestamp": ...,
            "overall_health": "healthy",
            "components": {...},
            "recommendations": [...]
        }
    """
    return diagnostics_controller.full_diagnostics()


@diagnostics_bp.route('/validate-apis', methods=['POST'])
def validate_apis():
    """
    POST /api/validate-apis
    
    Validate external APIs
    
    Request Body:
        {
            "sources": ["crossref", "pubmed", ...]  // optional
        }
    
    Returns:
        {
            "summary": {...},
            "apis": {...}
        }
    """
    return diagnostics_controller.validate_apis()


@diagnostics_bp.route('/', methods=['GET'])
def index():
    """
    GET /
    
    API welcome page
    
    Returns:
        {
            "message": "xplagiax_sourcex API",
            "version": "2.1.0",
            "documentation": "/api/health",
            "endpoints": {...}
        }
    """
    return {
        "message": "xplagiax_sourcex API",
        "version": "2.1.0",
        "documentation": "/api/health",
        "endpoints": {
            "search": "/api/similarity-search",
            "plagiarism": "/api/plagiarism-check",
            "health": "/api/health",
            "metrics": "/api/metrics",
            "faiss": "/api/faiss/stats"
        }
    }, 200