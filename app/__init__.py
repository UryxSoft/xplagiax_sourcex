"""
xplagiax_sourcex - Application Factory
"""
import asyncio
import atexit
import logging
from flask import Flask

from app.core.config import Config
from app.core.extensions import init_extensions, cleanup_extensions
from app.core.middleware import setup_middleware
from app.core.errors import register_error_handlers
from app.core.security import validate_security_config

# Blueprints
from app.api.routes.search_routes import search_bp
from app.api.routes.faiss_routes import faiss_bp
from app.api.routes.admin_routes import admin_bp
from app.api.routes.diagnostics_routes import diagnostics_bp

logger = logging.getLogger(__name__)

__version__ = "2.1.0"


def create_app(config_name: str = 'production') -> Flask:
    """
    Application Factory Pattern
    
    Args:
        config_name: 'development' | 'production' | 'testing'
    
    Returns:
        Configured Flask app
    """
    app = Flask(__name__)
    
    # 1. Load configuration
    config_class = Config.get_config(config_name)
    app.config.from_object(config_class)
    
    # 2. Validate security configuration (FAIL FAST)
    warnings = validate_security_config()
    if any(w.startswith("🔴") for w in warnings):
        for warning in warnings:
            if warning.startswith("🔴"):
                logger.error(warning)
            else:
                logger.warning(warning)
        
        raise RuntimeError(
            "❌ Critical security configuration errors detected. "
            "Fix environment variables before starting. "
            "See logs above for details."
        )
    
    # 3. Initialize extensions (Redis, HTTP client, FAISS)
    with app.app_context():
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            loop.run_until_complete(init_extensions(app))
            logger.info("✅ Extensions initialized successfully")
        except Exception as e:
            logger.error(f"❌ Failed to initialize extensions: {e}")
            raise
        finally:
            # Don't close loop yet, needed for requests
            pass
    
    # 4. Setup middleware
    setup_middleware(app)
    
    # 5. Register error handlers
    register_error_handlers(app)
    
    # 6. Register blueprints
    app.register_blueprint(search_bp)
    app.register_blueprint(faiss_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(diagnostics_bp)
    
    logger.info(
        f"🚀 Application created successfully",
        extra={
            "config": config_name,
            "blueprints": ["search", "faiss", "admin", "diagnostics"],
            "version": __version__
        }
    )
    
    # 7. Register cleanup handler
    atexit.register(lambda: _cleanup_app())
    
    return app


def _cleanup_app():
    """Cleanup resources on shutdown"""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        loop.run_until_complete(cleanup_extensions())
        logger.info("✅ Extensions cleaned up")
    finally:
        loop.close()