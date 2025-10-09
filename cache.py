"""
Sistema de caché con Redis
"""
import hashlib
import pickle
from typing import Optional, List, Dict

from config import Config

try:
    import redis.asyncio as aioredis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False


async def get_from_cache(redis_client, key: str) -> Optional[List[Dict]]:
    """
    Obtiene del caché (pickle binario en vez de JSON)
    """
    if not redis_client:
        return None
    try:
        cached = await redis_client.get(f"search:{key}")
        if cached:
            return pickle.loads(cached)
    except Exception as e:
        print(f"Cache read error: {e}")
    return None


async def save_to_cache(redis_client, key: str, results: List[Dict]):
    """Guarda en caché (binario)"""
    if not redis_client:
        return
    try:
        serialized = pickle.dumps(results, protocol=pickle.HIGHEST_PROTOCOL)
        await redis_client.setex(f"search:{key}", Config.CACHE_TTL, serialized)
    except Exception as e:
        print(f"Cache write error: {e}")


def get_cache_key(theme: str, idiom: str, text: str) -> str:
    """Genera clave de caché única (hash rápido)"""
    content = f"{theme}:{idiom}:{text}"
    return hashlib.blake2b(content.encode(), digest_size=16).hexdigest()