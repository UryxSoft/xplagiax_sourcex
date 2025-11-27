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
    """Manage Redis caching for search results"""
    
    def __init__(self, ttl: int = 3600):
        """
        Initialize cache manager
        
        Args:
            ttl: Time to live in seconds (default: 1 hour)
        """
        self.ttl = ttl
    
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
        
        Examples:
            >>> cache = CacheManager()
            >>> key = cache.generate_key("AI", "machine learning", 0.7, ["pubmed"])
            >>> print(key)
            'search:abc123def456'
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
            logger.debug("Redis client not available")
            return None
        
        try:
            value = await redis_client.get(key)
            
            if value:
                logger.debug(f"Cache HIT: {key}")
                return json.loads(value)
            
            logger.debug(f"Cache MISS: {key}")
            return None
        
        except json.JSONDecodeError as e:
            logger.error(f"JSON decode error for key '{key}': {e}")
            return None
        
        except Exception as e:
            logger.error(f"Cache get error for key '{key}': {e}")
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
            logger.debug("Redis client not available")
            return False
        
        try:
            json_value = json.dumps(value)
            await redis_client.setex(key, self.ttl, json_value)
            
            logger.debug(f"Cache SAVE: {key} (ttl={self.ttl}s)")
            return True
        
        except (TypeError, ValueError) as e:
            logger.error(f"Serialization error for key '{key}': {e}")
            return False
        
        except Exception as e:
            logger.error(f"Cache save error for key '{key}': {e}")
            return False
    
    async def delete_from_cache(self, key: str) -> bool:
        """
        Delete key from cache
        
        Args:
            key: Cache key
        
        Returns:
            True if key was deleted
        """
        redis_client = get_redis_client()
        
        if not redis_client:
            return False
        
        try:
            result = await redis_client.delete(key)
            
            if result > 0:
                logger.debug(f"Cache DELETE: {key}")
                return True
            
            return False
        
        except Exception as e:
            logger.error(f"Cache delete error for key '{key}': {e}")
            return False
    
    async def clear_all(self) -> bool:
        """
        Clear entire cache (DESTRUCTIVE)
        
        Returns:
            True if successful
        """
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
    
    async def get_stats(self) -> dict:
        """
        Get cache statistics
        
        Returns:
            Dict with cache stats
        """
        redis_client = get_redis_client()
        
        if not redis_client:
            return {'status': 'unavailable'}
        
        try:
            info = await redis_client.info('stats')
            
            hits = info.get('keyspace_hits', 0)
            misses = info.get('keyspace_misses', 0)
            total = hits + misses
            hit_rate = (hits / total * 100) if total > 0 else 0
            
            return {
                'status': 'connected',
                'hits': hits,
                'misses': misses,
                'hit_rate': round(hit_rate, 2),
                'total_keys': await redis_client.dbsize()
            }
        
        except Exception as e:
            logger.error(f"Error getting cache stats: {e}")
            return {'status': 'error', 'error': str(e)}