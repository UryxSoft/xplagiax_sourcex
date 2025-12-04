"""
Redis Repository - Cache CRUD operations
"""
import json
import logging
from typing import Any, Optional, List, Dict
import redis.asyncio as aioredis
from app.utils.serialization import dumps_json, loads_json

logger = logging.getLogger(__name__)


class RedisRepository:
    """
    Repository for Redis cache operations
    
    Handles:
    - Key-value storage with TTL
    - Batch operations
    - Pattern-based operations
    - Cache statistics
    """
    
    def __init__(self, redis_client: aioredis.Redis, default_ttl: int = 3600):
        """
        Initialize Redis repository
        
        Args:
            redis_client: Async Redis client
            default_ttl: Default time-to-live in seconds
        """
        self.client = redis_client
        self.default_ttl = default_ttl
        
        logger.info(f"✅ Redis repository initialized: ttl={default_ttl}s")
    
    # ==================== BASIC OPERATIONS ====================
    
    async def get(self, key: str) -> Optional[Any]:
        """
        Get value from cache
        
        Args:
            key: Cache key
        
        Returns:
            Deserialized value or None if not found
        """
        try:
            value = await self.client.get(key)
            
            if value is None:
                return None
            
            # Deserialize JSON
            return loads_json(value)
        
        except json.JSONDecodeError as e:
            logger.error(f"JSON decode error for key '{key}': {e}")
            return None
        
        except Exception as e:
            logger.error(f"Error getting key '{key}': {e}")
            return None
    
    async def set(
        self,
        key: str,
        value: Any,
        ttl: Optional[int] = None
    ) -> bool:
        """
        Set value in cache with TTL
        
        Args:
            key: Cache key
            value: Value to cache (must be JSON-serializable)
            ttl: Time-to-live in seconds (None = use default)
        
        Returns:
            True if successful
        """
        try:
            # Serialize to JSON
            son_value = dumps_json(value)
            
            # Use default TTL if not specified
            if ttl is None:
                ttl = self.default_ttl
            
            # Set with expiration
            await self.client.setex(key, ttl, json_value)
            
            return True
        
        except (TypeError, ValueError) as e:
            logger.error(f"Serialization error for key '{key}': {e}")
            return False
        
        except Exception as e:
            logger.error(f"Error setting key '{key}': {e}")
            return False
    
    async def delete(self, key: str) -> bool:
        """
        Delete key from cache
        
        Args:
            key: Cache key
        
        Returns:
            True if key was deleted
        """
        try:
            result = await self.client.delete(key)
            return result > 0
        
        except Exception as e:
            logger.error(f"Error deleting key '{key}': {e}")
            return False
    
    async def exists(self, key: str) -> bool:
        """
        Check if key exists
        
        Args:
            key: Cache key
        
        Returns:
            True if key exists
        """
        try:
            result = await self.client.exists(key)
            return result > 0
        
        except Exception as e:
            logger.error(f"Error checking key '{key}': {e}")
            return False
    
    async def expire(self, key: str, ttl: int) -> bool:
        """
        Set expiration on existing key
        
        Args:
            key: Cache key
            ttl: Time-to-live in seconds
        
        Returns:
            True if expiration was set
        """
        try:
            result = await self.client.expire(key, ttl)
            return result
        
        except Exception as e:
            logger.error(f"Error setting expiration for key '{key}': {e}")
            return False
    
    async def ttl(self, key: str) -> int:
        """
        Get remaining TTL for key
        
        Args:
            key: Cache key
        
        Returns:
            Remaining seconds (-1 if no expiration, -2 if key doesn't exist)
        """
        try:
            return await self.client.ttl(key)
        
        except Exception as e:
            logger.error(f"Error getting TTL for key '{key}': {e}")
            return -2
    
    # ==================== BATCH OPERATIONS ====================
    
    async def get_many(self, keys: List[str]) -> Dict[str, Any]:
        """
        Get multiple values at once
        
        Args:
            keys: List of cache keys
        
        Returns:
            Dict mapping keys to values (missing keys excluded)
        """
        if not keys:
            return {}
        
        try:
            # Use pipeline for efficiency
            pipeline = self.client.pipeline()
            
            for key in keys:
                pipeline.get(key)
            
            values = await pipeline.execute()
            
            # Deserialize and filter None values
            result = {}
            
            for key, value in zip(keys, values):
                if value is not None:
                    try:
                        result[key] = json.loads(value)
                    except json.JSONDecodeError:
                        logger.warning(f"Failed to decode value for key '{key}'")
            
            return result
        
        except Exception as e:
            logger.error(f"Error getting multiple keys: {e}")
            return {}
    
    async def set_many(
        self,
        items: Dict[str, Any],
        ttl: Optional[int] = None
    ) -> int:
        """
        Set multiple values at once
        
        Args:
            items: Dict mapping keys to values
            ttl: Time-to-live in seconds (None = use default)
        
        Returns:
            Number of keys successfully set
        """
        if not items:
            return 0
        
        try:
            # Use pipeline for efficiency
            pipeline = self.client.pipeline()
            
            if ttl is None:
                ttl = self.default_ttl
            
            for key, value in items.items():
                try:
                    son_value = dumps_json(value)
                    pipeline.setex(key, ttl, json_value)
                except (TypeError, ValueError) as e:
                    logger.warning(f"Skipping key '{key}': {e}")
            
            results = await pipeline.execute()
            
            # Count successful sets
            success_count = sum(1 for r in results if r)
            
            logger.debug(f"Set {success_count}/{len(items)} keys in batch")
            
            return success_count
        
        except Exception as e:
            logger.error(f"Error setting multiple keys: {e}")
            return 0
    
    async def delete_many(self, keys: List[str]) -> int:
        """
        Delete multiple keys at once
        
        Args:
            keys: List of cache keys
        
        Returns:
            Number of keys deleted
        """
        if not keys:
            return 0
        
        try:
            result = await self.client.delete(*keys)
            
            logger.debug(f"Deleted {result}/{len(keys)} keys")
            
            return result
        
        except Exception as e:
            logger.error(f"Error deleting multiple keys: {e}")
            return 0
    
    # ==================== PATTERN OPERATIONS ====================
    
    async def keys(self, pattern: str = "*") -> List[str]:
        """
        Get keys matching pattern
        
        Args:
            pattern: Key pattern (e.g., "user:*", "session:*")
        
        Returns:
            List of matching keys
        """
        try:
            keys = await self.client.keys(pattern)
            return [key.decode() if isinstance(key, bytes) else key for key in keys]
        
        except Exception as e:
            logger.error(f"Error getting keys with pattern '{pattern}': {e}")
            return []
    
    async def delete_pattern(self, pattern: str) -> int:
        """
        Delete all keys matching pattern
        
        Args:
            pattern: Key pattern
        
        Returns:
            Number of keys deleted
        """
        try:
            keys = await self.keys(pattern)
            
            if not keys:
                return 0
            
            return await self.delete_many(keys)
        
        except Exception as e:
            logger.error(f"Error deleting pattern '{pattern}': {e}")
            return 0
    
    async def count_pattern(self, pattern: str) -> int:
        """
        Count keys matching pattern
        
        Args:
            pattern: Key pattern
        
        Returns:
            Number of matching keys
        """
        try:
            keys = await self.keys(pattern)
            return len(keys)
        
        except Exception as e:
            logger.error(f"Error counting pattern '{pattern}': {e}")
            return 0
    
    # ==================== HASH OPERATIONS ====================
    
    async def hget(self, name: str, key: str) -> Optional[Any]:
        """
        Get value from hash
        
        Args:
            name: Hash name
            key: Hash key
        
        Returns:
            Deserialized value or None
        """
        try:
            value = await self.client.hget(name, key)
            
            if value is None:
                return None
            
            return loads_json(value)
        
        except Exception as e:
            logger.error(f"Error getting hash key '{name}:{key}': {e}")
            return None
    
    async def hset(self, name: str, key: str, value: Any) -> bool:
        """
        Set value in hash
        
        Args:
            name: Hash name
            key: Hash key
            value: Value to set
        
        Returns:
            True if successful
        """
        try:
            son_value = dumps_json(value)
            result = await self.client.hset(name, key, json_value)
            return result >= 0
        
        except Exception as e:
            logger.error(f"Error setting hash key '{name}:{key}': {e}")
            return False
    
    async def hgetall(self, name: str) -> Dict[str, Any]:
        """
        Get all key-value pairs from hash
        
        Args:
            name: Hash name
        
        Returns:
            Dict of deserialized values
        """
        try:
            data = await self.client.hgetall(name)
            
            result = {}
            for key, value in data.items():
                try:
                    key_str = key.decode() if isinstance(key, bytes) else key
                    value_str = value.decode() if isinstance(value, bytes) else value
                    result[key_str] = json.loads(value_str)
                except Exception:
                    pass
            
            return result
        
        except Exception as e:
            logger.error(f"Error getting hash '{name}': {e}")
            return {}
    
    # ==================== STATISTICS ====================
    
    async def get_stats(self) -> Dict[str, Any]:
        """
        Get cache statistics
        
        Returns:
            Dict with cache stats
        """
        try:
            info = await self.client.info('stats')
            memory_info = await self.client.info('memory')
            
            return {
                'total_keys': await self.client.dbsize(),
                'hits': info.get('keyspace_hits', 0),
                'misses': info.get('keyspace_misses', 0),
                'hit_rate': self._calculate_hit_rate(
                    info.get('keyspace_hits', 0),
                    info.get('keyspace_misses', 0)
                ),
                'memory_used_mb': memory_info.get('used_memory', 0) / (1024 * 1024),
                'memory_peak_mb': memory_info.get('used_memory_peak', 0) / (1024 * 1024)
            }
        
        except Exception as e:
            logger.error(f"Error getting cache stats: {e}")
            return {}
    
    @staticmethod
    def _calculate_hit_rate(hits: int, misses: int) -> float:
        """Calculate cache hit rate percentage"""
        total = hits + misses
        return (hits / total * 100) if total > 0 else 0.0
    
    # ==================== MANAGEMENT ====================
    
    async def flush(self) -> bool:
        """
        Clear entire cache (DESTRUCTIVE)
        
        Returns:
            True if successful
        """
        try:
            await self.client.flushdb()
            logger.warning("Redis cache flushed")
            return True
        
        except Exception as e:
            logger.error(f"Error flushing cache: {e}")
            return False
    
    async def ping(self) -> bool:
        """
        Check if Redis is alive
        
        Returns:
            True if Redis responds
        """
        try:
            result = await self.client.ping()
            return result
        
        except Exception as e:
            logger.error(f"Redis ping failed: {e}")
            return False