"""
API Routes - Blueprints
"""
from app.api.routes.search_routes import search_bp
from app.api.routes.faiss_routes import faiss_bp
from app.api.routes.admin_routes import admin_bp
from app.api.routes.diagnostics_routes import diagnostics_bp

__all__ = [
    'search_bp',
    'faiss_bp',
    'admin_bp',
    'diagnostics_bp',
]