"""
Cache Manager - Ultra-optimizado con orjson/msgpack
"""
import hashlib
import logging
from typing import Any, Optional, List
from app.core.extensions import get_redis_client
from app.utils.serialization import dumps_json, loads_json

logger = logging.getLogger(__name__)


class CacheManager:
    """Manager de caché ultra-optimizado"""
    
    def __init__(self, ttl: int = 3600):
        self.ttl = ttl
        self.default_prefix = "xplagiax"
    
    def generate_key(
        self,
        theme: str,
        text: str,
        threshold: float,
        sources: List[str]
    ) -> str:
        """
        Genera cache key usando blake2b (más rápido que sha256)
        """
        # Normalizar sources
        sources_str = ','.join(sorted(sources)) if sources else 'all'
        
        # Crear string único
        key_data = f"{theme}:{text}:{threshold}:{sources_str}"
        
        # Hash con blake2b (2x más rápido que sha256)
        key_hash = hashlib.blake2b(
            key_data.encode('utf-8'),
            digest_size=16
        ).hexdigest()
        
        return f"{self.default_prefix}:search:{key_hash}"
    
    async def get_from_cache(self, key: str) -> Optional[Any]:
        """
        Obtiene del caché usando orjson (5x más rápido)
        """
        redis_client = get_redis_client()
        
        if not redis_client:
            return None
        
        try:
            cached = await redis_client.get(key)
            
            if cached:
                # Deserializar con orjson
                return loads_json(cached)
            
            return None
        
        except Exception as e:
            logger.error(f"Cache read error for key '{key[:30]}...': {e}")
            return None
    
    async def save_to_cache(self, key: str, value: Any) -> bool:
        """
        Guarda en caché usando orjson (ultrarrápido)
        """
        redis_client = get_redis_client()
        
        if not redis_client:
            return False
        
        try:
            # Serializar con orjson
            serialized = dumps_json(value)
            
            # Guardar con TTL
            await redis_client.setex(key, self.ttl, serialized)
            
            logger.debug(f"Cache saved: {key[:30]}... (ttl={self.ttl}s)")
            return True
        
        except Exception as e:
            logger.error(f"Cache save error for key '{key[:30]}...': {e}")
            return False
    
    async def delete_from_cache(self, key: str) -> bool:
        """Elimina key del caché"""
        redis_client = get_redis_client()
        
        if not redis_client:
            return False
        
        try:
            result = await redis_client.delete(key)
            
            if result > 0:
                logger.debug(f"Cache deleted: {key[:30]}...")
                return True
            
            return False
        
        except Exception as e:
            logger.error(f"Cache delete error: {e}")
            return False
    
    async def get_many(self, keys: List[str]) -> dict:
        """
        Obtiene múltiples keys (pipeline para eficiencia)
        """
        redis_client = get_redis_client()
        
        if not redis_client or not keys:
            return {}
        
        try:
            # Usar pipeline
            pipe = redis_client.pipeline()
            for key in keys:
                pipe.get(key)
            
            values = await pipe.execute()
            
            # Deserializar
            result = {}
            for key, value in zip(keys, values):
                if value:
                    try:
                        result[key] = loads_json(value)
                    except Exception:
                        pass
            
            return result
        
        except Exception as e:
            logger.error(f"Cache get_many error: {e}")
            return {}
    
    async def set_many(self, items: dict, ttl: Optional[int] = None) -> int:
        """
        Guarda múltiples items (pipeline)
        """
        redis_client = get_redis_client()
        
        if not redis_client or not items:
            return 0
        
        ttl = ttl or self.ttl
        
        try:
            pipe = redis_client.pipeline()
            
            for key, value in items.items():
                try:
                    serialized = dumps_json(value)
                    pipe.setex(key, ttl, serialized)
                except Exception as e:
                    logger.warning(f"Skipping key {key[:30]}...: {e}")
            
            results = await pipe.execute()
            success_count = sum(1 for r in results if r)
            
            logger.debug(f"Cache set_many: {success_count}/{len(items)} saved")
            return success_count
        
        except Exception as e:
            logger.error(f"Cache set_many error: {e}")
            return 0
    
    async def clear_all(self) -> bool:
        """Limpia todo el caché (DESTRUCTIVO)"""
        redis_client = get_redis_client()
        
        if not redis_client:
            return False
        
        try:
            await redis_client.flushdb()
            logger.warning("⚠️ Cache cleared (all keys deleted)")
            return True
        
        except Exception as e:
            logger.error(f"Cache clear error: {e}")
            return False
    
    async def get_stats(self) -> dict:
        """Estadísticas del caché"""
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
            logger.error(f"Cache stats error: {e}")
            return {'status': 'error', 'error': str(e)}