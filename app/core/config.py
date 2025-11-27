"""
Configuration classes for different environments
"""
import os
from typing import Dict, Type


class BaseConfig:
    """Base configuration"""
    
    # Flask
    SECRET_KEY = os.getenv('FLASK_SECRET_KEY', 'dev-secret-change-in-production')
    DEBUG = False
    TESTING = False
    
    # Embedding Model
    EMBEDDING_MODEL = "sentence-transformers/all-MiniLM-L6-v2"
    EMBEDDING_DIMENSION = 384
    SIMILARITY_THRESHOLD = 0.70
    EMBEDDING_BATCH_SIZE = 32
    
    # HTTP Client
    REQUEST_TIMEOUT = 8.0
    POOL_CONNECTIONS = 20
    POOL_MAXSIZE = 50
    MAX_RESULTS_PER_SOURCE = 5
    HTTP2_ENABLED = os.getenv('HTTP2_ENABLED', 'false').lower() == 'true'
    
    # Cache (Redis)
    REDIS_HOST = os.getenv('REDIS_HOST', 'localhost')
    REDIS_PORT = int(os.getenv('REDIS_PORT', 6379))
    REDIS_PASSWORD = os.getenv('REDIS_PASSWORD')
    REDIS_DB = 0
    CACHE_TTL = 86400  # 24 hours
    
    # FAISS
    FAISS_INDEX_PATH = "data/faiss_index"
    FAISS_BACKUP_DIR = "backups"
    
    # SQLite (Deduplication)
    SQLITE_DB_PATH = "data/papers.db"
    
    # Rate Limiting (per minute)
    RATE_LIMITS = {
        "crossref": 50,
        "europepmc": 50,
        "pubmed": 10,
        "openalex": 100,
        "semantic_scholar": 100,
        "arxiv": 30,
        "doaj": 30,
        "core": 30,
        "biorxiv": 30,
        "zenodo": 60,
        "osf": 50,
        "base": 50,
        "internet_archive": 30,
        "hal": 50,
    }
    
    # Circuit Breaker
    CIRCUIT_FAILURE_THRESHOLD = 3
    CIRCUIT_TIMEOUT = 60
    
    # Security
    ADMIN_API_KEY = os.getenv('ADMIN_API_KEY')
    ALLOWED_ORIGINS = os.getenv('ALLOWED_ORIGINS', 'http://localhost:3000').split(',')
    
    # Logging
    LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')
    LOG_FORMAT = 'json'  # 'json' or 'text'
    
    # Performance
    MAX_WORKERS = 4


class DevelopmentConfig(BaseConfig):
    """Development configuration"""
    DEBUG = True
    LOG_LEVEL = 'DEBUG'
    
    # Disable SSL verification in development only
    SSL_VERIFY = False
    
    # More permissive CORS
    ALLOWED_ORIGINS = ['http://localhost:3000', 'http://localhost:5000', 'http://127.0.0.1:3000']


class ProductionConfig(BaseConfig):
    """Production configuration"""
    DEBUG = False
    TESTING = False
    
    # Enforce SSL verification
    SSL_VERIFY = True
    
    # Require secure secret keys
    if not os.getenv('FLASK_SECRET_KEY') or os.getenv('FLASK_SECRET_KEY') in ['dev-secret-change-in-production']:
        raise ValueError("FLASK_SECRET_KEY must be set in production")
    
    if not os.getenv('ADMIN_API_KEY'):
        raise ValueError("ADMIN_API_KEY must be set in production")


class TestingConfig(BaseConfig):
    """Testing configuration"""
    TESTING = True
    DEBUG = True
    
    # In-memory Redis for tests
    REDIS_HOST = 'localhost'
    REDIS_PORT = 6379
    REDIS_DB = 1  # Use different DB for tests
    
    # Fast tests
    CACHE_TTL = 10
    EMBEDDING_BATCH_SIZE = 8
    
    # Disable rate limiting for tests
    RATE_LIMITS = {k: 1000 for k in BaseConfig.RATE_LIMITS.keys()}


class Config:
    """Config factory"""
    
    configs: Dict[str, Type[BaseConfig]] = {
        'development': DevelopmentConfig,
        'production': ProductionConfig,
        'testing': TestingConfig,
    }
    
    @classmethod
    def get_config(cls, config_name: str) -> Type[BaseConfig]:
        """Get config class by name"""
        return cls.configs.get(config_name, ProductionConfig)