"""
Gestión de recursos globales (Redis, HTTP client) - VERSIÓN CORREGIDA
"""
import os
import logging
from typing import Optional

import httpx

from config import Config

try:
    import redis.asyncio as aioredis
    #import redis.asyncio as aioredis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False

logger = logging.getLogger(__name__)

# Variables globales
redis_client: Optional[aioredis.Redis] = None
http_client: Optional[httpx.AsyncClient] = None


async def init_resources():
    """Inicializa recursos async (Redis, HTTP client)"""
    global redis_client, http_client
    
    # Inicializar Redis
    if REDIS_AVAILABLE:
        try:
            redis_host = os.getenv('REDIS_HOST', 'localhost')
            redis_port = int(os.getenv('REDIS_PORT', 6379))
            redis_password = os.getenv('REDIS_PASSWORD', None)
            
            redis_client = aioredis.Redis(
                host=redis_host,
                port=redis_port,
                password=redis_password,
                db=0,
                decode_responses=False,
                max_connections=50,
                socket_connect_timeout=5,
                socket_timeout=5
            )
            
            # Verificar conexión
            await redis_client.ping()
            logger.info("Redis conectado exitosamente", extra={
                "host": redis_host,
                "port": redis_port,
                "auth": "yes" if redis_password else "no"
            })
        
        except Exception as e:
            logger.warning("Redis no disponible, operando sin caché", extra={"error": str(e)})
            redis_client = None
    else:
        logger.warning("Librería redis no instalada, operando sin caché")
        redis_client = None
    
    # Inicializar HTTP client pool persistente
    try:
        http_client = httpx.AsyncClient(
            limits=httpx.Limits(
                max_connections=Config.POOL_CONNECTIONS,
                max_keepalive_connections=Config.POOL_MAXSIZE
            ),
            timeout=httpx.Timeout(Config.REQUEST_TIMEOUT),
            http2=False,  # CAMBIAR A FALSE (HTTP/2 puede fallar sin configuración correcta)
            follow_redirects=True,
            verify=False
        )
        logger.info("HTTP client pool inicializado", extra={
            "max_connections": Config.POOL_CONNECTIONS,
            "timeout": Config.REQUEST_TIMEOUT
        })
    
    except Exception as e:
        logger.error("Error inicializando HTTP client", extra={"error": str(e)})
        http_client = None


async def cleanup_resources():
    """Limpia recursos async"""
    global http_client, redis_client
    
    if http_client:
        try:
            await http_client.aclose()
            logger.info("HTTP client cerrado")
        except Exception as e:
            logger.error("Error cerrando HTTP client", extra={"error": str(e)})
    
    if redis_client:
        try:
            await redis_client.close()
            logger.info("Redis cerrado")
        except Exception as e:
            logger.error("Error cerrando Redis", extra={"error": str(e)})


def get_redis_client() -> Optional[aioredis.Redis]:
    """Retorna instancia de Redis client"""
    return redis_client


def get_http_client() -> Optional[httpx.AsyncClient]:
    """Retorna instancia de HTTP client"""
    return http_client