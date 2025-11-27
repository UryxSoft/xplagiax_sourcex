"""
Flask extensions initialization (Redis, HTTP client, FAISS)
"""
import os
import logging
from typing import Optional

import httpx
from flask import Flask

logger = logging.getLogger(__name__)

# Global instances
redis_client: Optional['aioredis.Redis'] = None
http_client: Optional[httpx.AsyncClient] = None
faiss_index: Optional['FAISSIndex'] = None


async def init_extensions(app: Flask):
    """
    Initialize all extensions
    
    Args:
        app: Flask app instance
    """
    global redis_client, http_client, faiss_index
    
    config = app.config
    
    # 1. Initialize Redis
    await init_redis(config)
    
    # 2. Initialize HTTP Client
    await init_http_client(config)
    
    # 3. Initialize FAISS
    init_faiss(config)
    
    logger.info("✅ All extensions initialized")


async def init_redis(config):
    """Initialize Redis connection"""
    global redis_client
    
    try:
        import redis.asyncio as aioredis
        
        redis_client = aioredis.Redis(
            host=config['REDIS_HOST'],
            port=config['REDIS_PORT'],
            password=config.get('REDIS_PASSWORD'),
            db=config.get('REDIS_DB', 0),
            decode_responses=False,
            max_connections=50,
            socket_connect_timeout=5,
            socket_timeout=5
        )
        
        # Test connection
        await redis_client.ping()
        
        logger.info(
            "✅ Redis connected",
            extra={
                "host": config['REDIS_HOST'],
                "port": config['REDIS_PORT']
            }
        )
    
    except Exception as e:
        logger.warning(
            f"⚠️  Redis not available, running without cache: {e}"
        )
        redis_client = None


async def init_http_client(config):
    """Initialize HTTP client pool"""
    global http_client
    
    try:
        ssl_verify = config.get('SSL_VERIFY', True)
        http2_enabled = config.get('HTTP2_ENABLED', False)
        
        if not ssl_verify:
            logger.warning("⚠️  SSL verification disabled (development mode)")
        
        http_client = httpx.AsyncClient(
            limits=httpx.Limits(
                max_connections=config['POOL_CONNECTIONS'],
                max_keepalive_connections=config['POOL_MAXSIZE']
            ),
            timeout=httpx.Timeout(config['REQUEST_TIMEOUT']),
            http2=http2_enabled,
            follow_redirects=True,
            verify=ssl_verify
        )
        
        logger.info(
            "✅ HTTP client initialized",
            extra={
                "max_connections": config['POOL_CONNECTIONS'],
                "http2": http2_enabled,
                "ssl_verify": ssl_verify
            }
        )
    
    except Exception as e:
        logger.error(f"❌ Failed to initialize HTTP client: {e}")
        raise


def init_faiss(config):
    """Initialize FAISS index"""
    global faiss_index
    
    try:
        from app.services.faiss_service import FAISSIndex
        
        faiss_index = FAISSIndex(
            dimension=config['EMBEDDING_DIMENSION'],
            index_path=config['FAISS_INDEX_PATH']
        )
        
        logger.info(
            "✅ FAISS initialized",
            extra={
                "papers": faiss_index.index.ntotal,
                "dimension": config['EMBEDDING_DIMENSION']
            }
        )
    
    except ImportError:
        logger.warning("⚠️  FAISS not available (faiss-cpu not installed)")
        faiss_index = None
    
    except Exception as e:
        logger.error(f"❌ FAISS initialization failed: {e}")
        faiss_index = None


async def cleanup_extensions():
    """Cleanup all extensions"""
    global http_client, redis_client
    
    # Close HTTP client
    if http_client:
        try:
            await http_client.aclose()
            logger.info("✅ HTTP client closed")
        except Exception as e:
            logger.error(f"Error closing HTTP client: {e}")
    
    # Close Redis
    if redis_client:
        try:
            await redis_client.close()
            logger.info("✅ Redis closed")
        except Exception as e:
            logger.error(f"Error closing Redis: {e}")
    
    # Save FAISS index
    if faiss_index:
        try:
            faiss_index.save()
            logger.info("✅ FAISS index saved")
        except Exception as e:
            logger.error(f"Error saving FAISS: {e}")


# Getters
def get_redis_client():
    """Get Redis client instance"""
    return redis_client


def get_http_client():
    """Get HTTP client instance"""
    return http_client


def get_faiss_index():
    """Get FAISS index instance"""
    return faiss_index