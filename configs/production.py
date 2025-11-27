"""
Production Configuration - Settings for production deployment
"""
from configs.base import BaseConfig


class ProductionConfig(BaseConfig):
    """
    Production environment configuration
    
    Features:
    - Debug mode disabled
    - Strict security settings
    - Production-grade Redis
    - SSL verification enabled
    - Rate limiting enforced
    """
    
    # ==================== FLASK ====================
    
    DEBUG = False
    TESTING = False
    ENV = 'production'
    
    # ==================== SECURITY ====================
    
    # Strict security for production
    SESSION_COOKIE_SECURE = True  # HTTPS only
    SSL_VERIFY = True  # Verify SSL certificates
    
    # Require strong secrets in production
    @classmethod
    def validate_secrets(cls):
        """Validate that production secrets are set"""
        import os
        
        required_secrets = [
            'FLASK_SECRET_KEY',
            'ADMIN_API_KEY',
        ]
        
        missing = []
        weak = []
        
        for secret in required_secrets:
            value = os.getenv(secret)
            
            if not value:
                missing.append(secret)
            elif value in ['change-this-in-production', 'dev-secret-key', 'dev-admin-key']:
                weak.append(secret)
        
        if missing:
            raise ValueError(
                f"Missing required secrets in production: {', '.join(missing)}"
            )
        
        if weak:
            raise ValueError(
                f"Weak/default secrets detected in production: {', '.join(weak)}"
            )
    
    # ==================== CORS ====================
    
    # Strict CORS in production
    # Must be set via ALLOWED_ORIGINS environment variable
    
    # ==================== REDIS ====================
    
    # Production Redis typically requires password
    # REDIS_URL should include password: redis://:password@host:6379/0
    REDIS_MAX_CONNECTIONS = 100
    REDIS_SOCKET_TIMEOUT = 10
    
    # ==================== LOGGING ====================
    
    LOG_LEVEL = 'INFO'
    LOG_FILE = 'logs/production.log'
    
    # ==================== DATABASE ====================
    
    SQLITE_DB_PATH = 'data/xplagiax.db'
    
    # ==================== FAISS ====================
    
    FAISS_INDEX_PATH = 'data/faiss_index.index'
    FAISS_METADATA_PATH = 'data/faiss_index_metadata.pkl'
    
    # ==================== RATE LIMITING ====================
    
    RATE_LIMIT_ENABLED = True
    
    # Strict rate limits for production
    RATE_LIMITS = {
        'similarity_search': "10 per minute",
        'plagiarism_check': "5 per minute",
        'benchmark': "5 per hour",
    }
    
    # ==================== PERFORMANCE ====================
    
    MAX_CONCURRENT_REQUESTS = 20
    REQUEST_TIMEOUT = 300
    
    # ==================== FEATURES ====================
    
    ENABLE_PROFILING = False  # Disable profiling in production
    
    # ==================== MONITORING ====================
    
    # Sentry (error tracking)
    SENTRY_DSN = BaseConfig.os.getenv('SENTRY_DSN')
    SENTRY_ENVIRONMENT = 'production'
    
    # Prometheus metrics
    ENABLE_METRICS = True
    METRICS_PORT = int(BaseConfig.os.getenv('METRICS_PORT', '9090'))
    
    @classmethod
    def init_app(cls, app):
        """Initialize production app"""
        super().init_app(app)
        
        # Validate secrets
        cls.validate_secrets()
        
        # Production-specific initialization
        import logging
        from logging.handlers import RotatingFileHandler
        
        # File handler
        file_handler = RotatingFileHandler(
            cls.LOG_FILE,
            maxBytes=cls.LOG_MAX_BYTES,
            backupCount=cls.LOG_BACKUP_COUNT
        )
        
        file_handler.setLevel(logging.INFO)
        file_handler.setFormatter(logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        ))
        
        app.logger.addHandler(file_handler)
        app.logger.setLevel(logging.INFO)
        
        # Log startup
        app.logger.info("=" * 60)
        app.logger.info("🚀 PRODUCTION MODE")
        app.logger.info("=" * 60)
        app.logger.info(f"Version: {cls.VERSION}")
        app.logger.info(f"Debug: {cls.DEBUG}")
        app.logger.info(f"SSL Verify: {cls.SSL_VERIFY}")
        app.logger.info(f"Rate Limiting: {cls.RATE_LIMIT_ENABLED}")
        app.logger.info("=" * 60)
        
        # Setup Sentry if configured
        if cls.SENTRY_DSN:
            try:
                import sentry_sdk
                from sentry_sdk.integrations.flask import FlaskIntegration
                
                sentry_sdk.init(
                    dsn=cls.SENTRY_DSN,
                    integrations=[FlaskIntegration()],
                    environment=cls.SENTRY_ENVIRONMENT,
                    traces_sample_rate=0.1,  # Sample 10% of transactions
                )
                
                app.logger.info("✅ Sentry error tracking initialized")
            except ImportError:
                app.logger.warning("⚠️ Sentry SDK not installed")
            except Exception as e:
                app.logger.error(f"❌ Failed to initialize Sentry: {e}")