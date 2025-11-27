"""
Cache Manager - Redis caching utilities
"""
import json
import hashlib
import logging
from typing import Any, Optional, List
from app.core.extensions import get_redis_client

logger = logging.getLogger(__name__)


class CacheManager:
    """Manage Redis caching"""
    
    def __init__(self, ttl: int = 3600):
        self.ttl = ttl  # Time to live in seconds (default: 1 hour)
    
    def generate_key(
        self,
        theme: str,
        text: str,
        threshold: float,
        sources: List[str]
    ) -> str:
        """
        Generate cache key from search parameters
        
        Args:
            theme: Search theme
            text: Processed text
            threshold: Similarity threshold
            sources: List of sources
        
        Returns:
            Cache key string
        """
        # Create unique key from parameters
        key_data = f"{theme}:{text}:{threshold}:{','.join(sorted(sources))}"
        
        # Hash for consistent length
        key_hash = hashlib.sha256(key_data.encode()).hexdigest()[:16]
        
        return f"search:{key_hash}"
    
    async def get_from_cache(self, key: str) -> Optional[Any]:
        """
        Get value from cache
        
        Args:
            key: Cache key
        
        Returns:
            Cached value or None if not found
        """
        redis_client = get_redis_client()
        
        if not redis_client:
            return None
        
        try:
            value = await redis_client.get(key)
            
            if value:
                logger.debug(f"Cache HIT: {key}")
                return json.loads(value)
            
            logger.debug(f"Cache MISS: {key}")
            return None
        
        except Exception as e:
            logger.error(f"Cache get error: {e}")
            return None
    
    async def save_to_cache(self, key: str, value: Any) -> bool:
        """
        Save value to cache
        
        Args:
            key: Cache key
            value: Value to cache (must be JSON-serializable)
        
        Returns:
            True if successful, False otherwise
        """
        redis_client = get_redis_client()
        
        if not redis_client:
            return False
        
        try:
            json_value = json.dumps(value)
            await redis_client.setex(key, self.ttl, json_value)
            
            logger.debug(f"Cache SAVE: {key}")
            return True
        
        except Exception as e:
            logger.error(f"Cache save error: {e}")
            return False
    
    async def delete_from_cache(self, key: str) -> bool:
        """Delete key from cache"""
        redis_client = get_redis_client()
        
        if not redis_client:
            return False
        
        try:
            await redis_client.delete(key)
            logger.debug(f"Cache DELETE: {key}")
            return True
        
        except Exception as e:
            logger.error(f"Cache delete error: {e}")
            return False
    
    async def clear_all(self) -> bool:
        """Clear entire cache (DESTRUCTIVE)"""
        redis_client = get_redis_client()
        
        if not redis_client:
            return False
        
        try:
            await redis_client.flushdb()
            logger.warning("Cache cleared (all keys deleted)")
            return True
        
        except Exception as e:
            logger.error(f"Cache clear error: {e}")
            return False