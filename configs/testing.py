"""
Testing Configuration - Settings for automated tests
"""
from configs.base import BaseConfig


class TestingConfig(BaseConfig):
    """
    Testing environment configuration
    
    Features:
    - Testing mode enabled
    - In-memory databases
    - Fast operations
    - No rate limiting
    - Isolated environment
    """
    
    # ==================== FLASK ====================
    
    DEBUG = False
    TESTING = True
    ENV = 'testing'
    
    # ==================== SECURITY ====================
    
    # Simplified security for testing
    SESSION_COOKIE_SECURE = False
    SSL_VERIFY = False
    
    SECRET_KEY = 'test-secret-key'
    ADMIN_API_KEY = 'test-admin-key'
    
    # ==================== CORS ====================
    
    CORS_ORIGINS = ['*']
    
    # ==================== REDIS ====================
    
    # Use fakeredis for testing (in-memory)
    REDIS_URL = 'redis://localhost:6379/15'  # Use DB 15 for testing
    REDIS_PASSWORD = None
    
    # ==================== LOGGING ====================
    
    LOG_LEVEL = 'DEBUG'
    LOG_FILE = None  # Console only for tests
    
    # ==================== DATABASE ====================
    
    # Use in-memory SQLite for testing
    SQLITE_DB_PATH = ':memory:'
    
    # ==================== FAISS ====================
    
    # Use temporary files for testing
    FAISS_INDEX_PATH = '/tmp/test_faiss_index.index'
    FAISS_METADATA_PATH = '/tmp/test_faiss_metadata.pkl'
    
    # Smaller dimension for faster tests
    FAISS_DIMENSION = 384
    
    # ==================== EMBEDDINGS ====================
    
    # Use smaller batch size for tests
    EMBEDDING_BATCH_SIZE = 8
    
    # ==================== RATE LIMITING ====================
    
    # Disable rate limiting for tests
    RATE_LIMIT_ENABLED = False
    
    # ==================== PERFORMANCE ====================
    
    # Lower limits for faster tests
    MAX_CONCURRENT_REQUESTS = 2
    REQUEST_TIMEOUT = 30
    
    # ==================== FEATURES ====================
    
    ENABLE_PROFILING = False
    
    # ==================== TESTING ====================
    
    # Preserve exceptions for better error reporting
    PRESERVE_CONTEXT_ON_EXCEPTION = False
    
    # Disable CSRF for easier API testing
    WTF_CSRF_ENABLED = False
    
    # Test data
    TEST_DATA_DIR = 'tests/fixtures'
    
    # ==================== CACHE ====================
    
    # Short TTL for tests
    CACHE_DEFAULT_TTL = 60  # 1 minute
    
    # ==================== DEDUPLICATION ====================
    
    # Smaller Bloom filter for tests
    BLOOM_FILTER_CAPACITY = 10000
    BLOOM_FILTER_ERROR_RATE = 0.01
    
    @classmethod
    def init_app(cls, app):
        """Initialize testing app"""
        super().init_app(app)
        
        # Testing-specific initialization
        import logging
        logging.basicConfig(
            level=logging.DEBUG,
            format='%(levelname)s - %(name)s - %(message)s'
        )
        
        # Suppress noisy loggers during tests
        logging.getLogger('urllib3').setLevel(logging.WARNING)
        logging.getLogger('httpx').setLevel(logging.WARNING)
        logging.getLogger('httpcore').setLevel(logging.WARNING)
        logging.getLogger('faiss').setLevel(logging.WARNING)
        
        print("\n" + "=" * 60)
        print("🧪 TESTING MODE")
        print("=" * 60)
        print(f"Database: {cls.SQLITE_DB_PATH}")
        print(f"Redis: {cls.REDIS_URL}")
        print(f"Rate Limiting: {cls.RATE_LIMIT_ENABLED}")
        print("=" * 60 + "\n")