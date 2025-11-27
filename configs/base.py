"""
Base Configuration - Shared settings across all environments
"""
import os
from datetime import timedelta


class BaseConfig:
    """
    Base configuration class with shared settings
    
    All environment-specific configs inherit from this
    """
    
    # ==================== APPLICATION ====================
    
    APP_NAME = "xplagiax_sourcex"
    VERSION = "2.1.0"
    
    # Flask secret key
    SECRET_KEY = os.getenv('FLASK_SECRET_KEY', os.urandom(32).hex())
    
    # JSON settings
    JSON_SORT_KEYS = False
    JSONIFY_PRETTYPRINT_REGULAR = False
    
    # ==================== SECURITY ====================
    
    # Admin API key
    ADMIN_API_KEY = os.getenv('ADMIN_API_KEY', 'change-this-in-production')
    
    # Session config
    SESSION_COOKIE_SECURE = True  # HTTPS only
    SESSION_COOKIE_HTTPONLY = True  # No JavaScript access
    SESSION_COOKIE_SAMESITE = 'Lax'
    PERMANENT_SESSION_LIFETIME = timedelta(hours=24)
    
    # CORS
    CORS_ORIGINS = os.getenv(
        'ALLOWED_ORIGINS',
        'http://localhost:3000,http://localhost:5000'
    ).split(',')
    
    # SSL/TLS
    SSL_VERIFY = os.getenv('SSL_VERIFY', 'true').lower() == 'true'
    
    # ==================== REDIS ====================
    
    REDIS_URL = os.getenv('REDIS_URL', 'redis://localhost:6379/0')
    REDIS_PASSWORD = os.getenv('REDIS_PASSWORD')
    REDIS_MAX_CONNECTIONS = int(os.getenv('REDIS_MAX_CONNECTIONS', '50'))
    REDIS_SOCKET_TIMEOUT = int(os.getenv('REDIS_SOCKET_TIMEOUT', '5'))
    
    # Cache TTL (seconds)
    CACHE_DEFAULT_TTL = int(os.getenv('CACHE_TTL', '3600'))  # 1 hour
    
    # ==================== DATABASE ====================
    
    SQLITE_DB_PATH = os.getenv('SQLITE_DB_PATH', 'data/xplagiax.db')
    
    # ==================== FAISS ====================
    
    FAISS_INDEX_PATH = os.getenv('FAISS_INDEX_PATH', 'data/faiss_index.index')
    FAISS_METADATA_PATH = os.getenv('FAISS_METADATA_PATH', 'data/faiss_index_metadata.pkl')
    FAISS_DIMENSION = int(os.getenv('FAISS_DIMENSION', '384'))
    FAISS_STRATEGY = os.getenv('FAISS_STRATEGY', 'flat_idmap')
    
    # ==================== EMBEDDINGS ====================
    
    EMBEDDING_MODEL = os.getenv('EMBEDDING_MODEL', 'all-MiniLM-L6-v2')
    EMBEDDING_DEVICE = os.getenv('EMBEDDING_DEVICE', 'cpu')  # 'cpu' or 'cuda'
    EMBEDDING_BATCH_SIZE = int(os.getenv('EMBEDDING_BATCH_SIZE', '32'))
    
    # ==================== TEXT PROCESSING ====================
    
    MIN_TEXT_LENGTH = 10
    MAX_TEXT_LENGTH = 10000
    DEFAULT_SIMILARITY_THRESHOLD = 0.70
    
    # ==================== EXTERNAL APIs ====================
    
    # API Keys (configure via environment variables)
    CORE_API_KEY = os.getenv('CORE_API_KEY', 'YOUR_API_KEY')
    SEMANTIC_SCHOLAR_API_KEY = os.getenv('SEMANTIC_SCHOLAR_API_KEY')
    
    # API Timeouts
    API_TIMEOUT = float(os.getenv('API_TIMEOUT', '10.0'))
    API_LONG_TIMEOUT = float(os.getenv('API_LONG_TIMEOUT', '30.0'))
    
    # HTTP/2 support
    HTTP2_ENABLED = os.getenv('HTTP2_ENABLED', 'false').lower() == 'true'
    
    # ==================== RATE LIMITING ====================
    
    RATE_LIMIT_ENABLED = True
    RATE_LIMIT_DEFAULT = "10 per minute"
    RATE_LIMIT_STORAGE_URL = REDIS_URL
    
    # Per-endpoint limits
    RATE_LIMITS = {
        'similarity_search': "10 per minute",
        'plagiarism_check': "5 per minute",
        'benchmark': "5 per hour",
    }
    
    # ==================== LOGGING ====================
    
    LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')
    LOG_FILE = os.getenv('LOG_FILE')  # None = console only
    LOG_MAX_BYTES = 10 * 1024 * 1024  # 10MB
    LOG_BACKUP_COUNT = 5
    
    # ==================== DEDUPLICATION ====================
    
    BLOOM_FILTER_CAPACITY = int(os.getenv('BLOOM_FILTER_CAPACITY', '1000000'))
    BLOOM_FILTER_ERROR_RATE = float(os.getenv('BLOOM_FILTER_ERROR_RATE', '0.001'))
    
    # ==================== PERFORMANCE ====================
    
    # Max concurrent API requests
    MAX_CONCURRENT_REQUESTS = int(os.getenv('MAX_CONCURRENT_REQUESTS', '10'))
    
    # Request timeout
    REQUEST_TIMEOUT = int(os.getenv('REQUEST_TIMEOUT', '300'))  # 5 minutes
    
    # ==================== FEATURES ====================
    
    # Feature flags
    ENABLE_FAISS = os.getenv('ENABLE_FAISS', 'true').lower() == 'true'
    ENABLE_CACHE = os.getenv('ENABLE_CACHE', 'true').lower() == 'true'
    ENABLE_PROFILING = os.getenv('ENABLE_PROFILING', 'false').lower() == 'true'
    
    # ==================== PATHS ====================
    
    BASE_DIR = os.path.abspath(os.path.dirname(os.path.dirname(__file__)))
    DATA_DIR = os.path.join(BASE_DIR, 'data')
    LOGS_DIR = os.path.join(BASE_DIR, 'logs')
    BACKUPS_DIR = os.path.join(BASE_DIR, 'backups')
    
    @classmethod
    def init_app(cls, app):
        """
        Initialize application with config
        
        Args:
            app: Flask application instance
        """
        # Create directories if they don't exist
        import os
        os.makedirs(cls.DATA_DIR, exist_ok=True)
        os.makedirs(cls.LOGS_DIR, exist_ok=True)
        os.makedirs(cls.BACKUPS_DIR, exist_ok=True)