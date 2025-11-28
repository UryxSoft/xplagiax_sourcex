# app/__init__.py
import os
import logging
from flask import Flask
from flask_cors import CORS
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

# Setup logging
from app.utils.logging_config import setup_logging
setup_logging()

logger = logging.getLogger(__name__)


def create_app(config_name=None):
    """
    Application factory
    
    Args:
        config_name: Environment name (development, production, testing)
    
    Returns:
        Flask app instance
    """
    app = Flask(__name__)
    
    # 1. Load configuration
    if config_name is None:
        config_name = os.getenv('FLASK_ENV', 'development')
    
    from configs import get_config
    
    config_class = get_config(config_name)
    app.config.from_object(config_class)
    
    logger.info(f"🚀 Starting {app.config['APP_NAME']} v{app.config['VERSION']}")
    logger.info(f"📍 Environment: {config_name}")
    
    # 2. Initialize extensions BEFORE registering blueprints
    limiter = Limiter(
        app=app,
        key_func=get_remote_address,
        storage_uri=app.config.get('REDIS_URL', 'memory://')
    )


    # CORS
    #CORS(app, origins=app.config.get('CORS_ORIGINS', ['*']))
    CORS(app, resources={r"/api/*": {"origins": app.config.get('CORS_ORIGINS', ['*'])}})

    # 3. Initialize Flask extensions (Redis, HTTP, FAISS)
    with app.app_context():
        from app.core.extensions import init_extensions
        import asyncio
        
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop.run_until_complete(init_extensions(app))
        finally:
            loop.close()
    
    # 4. Register blueprints with rate limiter
    from app.api.routes import search_bp, faiss_bp, admin_bp, diagnostics_bp
    from app.api.routes.search_routes import init_search_routes
    from app.api.routes.admin_routes import init_admin_routes
    
    # Initialize route modules with limiter
    init_search_routes(limiter)
    init_admin_routes(limiter)
    
    # Register blueprints
    app.register_blueprint(search_bp)
    app.register_blueprint(faiss_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(diagnostics_bp)

    #  Aplicar rate limiting DESPUÉS del registro
    limiter.limit("10 per minute")(app.view_functions['search.similarity_search'])
    limiter.limit("5 per minute")(app.view_functions['search.plagiarism_check'])
    limiter.limit("5 per hour")(app.view_functions['admin.benchmark'])
    
    # 5. Setup middleware
    from app.core.middleware import setup_middleware
    setup_middleware(app)
    
    # 6. Register error handlers
    from app.core.errors import register_error_handlers
    register_error_handlers(app)
    
    # 7. Validate security config
    from app.core.security import validate_security_config
    warnings = validate_security_config()
    
    if warnings:
        logger.warning("⚠️  Security warnings:")
        for warning in warnings:
            logger.warning(f"  {warning}")
    
    logger.info("✅ Application initialized successfully")
    
    return app