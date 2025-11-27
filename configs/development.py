"""
Development Configuration - Settings for local development
"""
from configs.base import BaseConfig


class DevelopmentConfig(BaseConfig):
    """
    Development environment configuration
    
    Features:
    - Debug mode enabled
    - Verbose logging
    - Local Redis
    - SSL verification disabled
    - Hot reload enabled
    """
    
    # ==================== FLASK ====================
    
    DEBUG = True
    TESTING = False
    ENV = 'development'
    
    # ==================== SECURITY ====================
    
    # Relaxed security for development
    SESSION_COOKIE_SECURE = False  # Allow HTTP
    SSL_VERIFY = False  # Disable SSL verification
    
    # Use simple secret key in development
    SECRET_KEY = 'dev-secret-key-change-in-production'
    ADMIN_API_KEY = 'dev-admin-key'
    
    # ==================== CORS ====================
    
    # Allow all origins in development
    CORS_ORIGINS = ['*']
    
    # ==================== REDIS ====================
    
    REDIS_URL = 'redis://localhost:6379/0'
    REDIS_PASSWORD = None
    
    # ==================== LOGGING ====================
    
    LOG_LEVEL = 'DEBUG'
    LOG_FILE = 'logs/development.log'
    
    # ==================== DATABASE ====================
    
    SQLITE_DB_PATH = 'data/dev_xplagiax.db'
    
    # ==================== FAISS ====================
    
    FAISS_INDEX_PATH = 'data/dev_faiss_index.index'
    FAISS_METADATA_PATH = 'data/dev_faiss_index_metadata.pkl'
    
    # ==================== RATE LIMITING ====================
    
    # More lenient rate limits for development
    RATE_LIMIT_ENABLED = False  # Disable for easier testing
    
    RATE_LIMITS = {
        'similarity_search': "100 per minute",
        'plagiarism_check': "50 per minute",
        'benchmark': "50 per hour",
    }
    
    # ==================== PERFORMANCE ====================
    
    # Lower limits for development
    MAX_CONCURRENT_REQUESTS = 5
    
    # ==================== FEATURES ====================
    
    ENABLE_PROFILING = True  # Enable performance profiling
    
    # ==================== DEVELOPMENT TOOLS ====================
    
    # Flask-DebugToolbar (if installed)
    DEBUG_TB_ENABLED = True
    DEBUG_TB_INTERCEPT_REDIRECTS = False
    
    # Pretty print JSON responses
    JSONIFY_PRETTYPRINT_REGULAR = True
    
    @classmethod
    def init_app(cls, app):
        """Initialize development app"""
        super().init_app(app)
        
        # Development-specific initialization
        import logging
        logging.basicConfig(
            level=logging.DEBUG,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        
        print("=" * 60)
        print("🔧 DEVELOPMENT MODE")
        print("=" * 60)
        print(f"Debug: {cls.DEBUG}")
        print(f"Redis: {cls.REDIS_URL}")
        print(f"Database: {cls.SQLITE_DB_PATH}")
        print(f"Log Level: {cls.LOG_LEVEL}")
        print(f"Rate Limiting: {cls.RATE_LIMIT_ENABLED}")
        print("=" * 60)