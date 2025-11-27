"""
Sistema de caché con Redis - VERSIÓN OPTIMIZADA
"""
import hashlib
import logging
from typing import Optional, List, Dict

try:
    import orjson
    JSON_AVAILABLE = True
except ImportError:
    import json
    JSON_AVAILABLE = False

from config import Config

logger = logging.getLogger(__name__)


async def get_from_cache(redis_client, key: str) -> Optional[List[Dict]]:
    """
    Obtiene del caché usando orjson (5x más rápido que pickle)
    """
    if not redis_client:
        return None
    
    try:
        cached = await redis_client.get(f"search:{key}")
        
        if cached:
            if JSON_AVAILABLE:
                return orjson.loads(cached)
            else:
                return json.loads(cached)
        
        return None
    
    except Exception as e:
        logger.warning("Error leyendo caché", extra={"error": str(e), "key": key[:20]})
        return None


async def save_to_cache(redis_client, key: str, results: List[Dict]):
    """Guarda en caché usando orjson (ultrarrápido)"""
    if not redis_client:
        return
    
    try:
        if JSON_AVAILABLE:
            serialized = orjson.dumps(results)
        else:
            serialized = json.dumps(results).encode('utf-8')
        
        await redis_client.setex(
            f"search:{key}",
            Config.CACHE_TTL,
            serialized
        )
        
        logger.debug("Guardado en caché exitoso", extra={"key": key[:20], "results": len(results)})
    
    except Exception as e:
        logger.warning("Error guardando en caché", extra={"error": str(e), "key": key[:20]})


def get_cache_key(theme: str, idiom: str, text: str) -> str:
    """
    Genera clave de caché única usando blake2b (más rápido que sha256)
    """
    content = f"{theme}:{idiom}:{text}"
    return hashlib.blake2b(content.encode(), digest_size=16).hexdigest()