"""
Docker Configuration - Settings for Docker deployment
"""
from configs.production import ProductionConfig


class DockerConfig(ProductionConfig):
    """
    Docker environment configuration
    
    Inherits from ProductionConfig but uses Docker-specific settings
    """
    
    # ==================== REDIS ====================
    
    # Docker Compose service name
    REDIS_URL = 'redis://redis:6379/0'
    
    # ==================== PATHS ====================
    
    # Docker volume paths
    DATA_DIR = '/app/data'
    LOGS_DIR = '/app/logs'
    BACKUPS_DIR = '/app/backups'
    
    SQLITE_DB_PATH = '/app/data/xplagiax.db'
    FAISS_INDEX_PATH = '/app/data/faiss_index.index'
    FAISS_METADATA_PATH = '/app/data/faiss_index_metadata.pkl'
    
    LOG_FILE = '/app/logs/app.log'
    
    @classmethod
    def init_app(cls, app):
        """Initialize Docker app"""
        ProductionConfig.init_app(app)
        
        app.logger.info("🐳 Docker deployment mode")
        