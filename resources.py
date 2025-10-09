"""
Gestión de recursos globales (Redis, HTTP client)
"""
import os
from typing import Optional

import httpx

from config import Config

try:
    import redis.asyncio as aioredis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False


# Variables globales
redis_client: Optional[aioredis.Redis] = None
http_client: Optional[httpx.AsyncClient] = None


async def init_resources():
    """Inicializa recursos async (Redis, HTTP client)"""
    global redis_client, http_client
    
    # Redis
    if REDIS_AVAILABLE:
        try:
            redis_client = aioredis.Redis(
                host=os.getenv('REDIS_HOST', 'localhost'),
                port=int(os.getenv('REDIS_PORT', 6379)),
                db=0,
                decode_responses=False,
                max_connections=50
            )
            await redis_client.ping()
            print("✅ Redis conectado")
        except Exception as e:
            print(f"⚠️ Redis no disponible: {e}")
            redis_client = None
    
    # HTTP client pool persistente
    http_client = httpx.AsyncClient(
        limits=httpx.Limits(
            max_connections=Config.POOL_CONNECTIONS,
            max_keepalive_connections=Config.POOL_MAXSIZE
        ),
        timeout=httpx.Timeout(Config.REQUEST_TIMEOUT),
        http2=True
    )
    print("✅ HTTP client pool inicializado")


async def cleanup_resources():
    """Limpia recursos async"""
    global http_client, redis_client
    if http_client:
        await http_client.aclose()
    if redis_client:
        await redis_client.close()


def get_redis_client():
    """Retorna instancia de Redis client"""
    return redis_client


def get_http_client():
    """Retorna instancia de HTTP client"""
    return http_client