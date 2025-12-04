"""
Request deduplication - evita procesamiento duplicado
"""
import asyncio
import hashlib
import logging
from typing import Any, Dict, Optional
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


class RequestDeduplicator:
    """
    Deduplica requests idénticos en vuelo
    
    Si 10 usuarios buscan "machine learning" al mismo tiempo,
    solo se procesa 1 vez y los otros 9 esperan el resultado.
    """
    
    def __init__(self, ttl_seconds: int = 10):
        self._pending: Dict[str, asyncio.Future] = {}
        self._lock = asyncio.Lock()
        self.ttl_seconds = ttl_seconds
        self._hits = 0
        self._misses = 0
    
    def _generate_key(self, *args, **kwargs) -> str:
        """Genera key único para request"""
        key_data = f"{args}:{sorted(kwargs.items())}"
        return hashlib.blake2b(key_data.encode(), digest_size=16).hexdigest()
    
    async def deduplicate(self, key: str, coro_func, *args, **kwargs):
        """
        Deduplica ejecución de coroutine
        
        Args:
            key: Request key
            coro_func: Async function a ejecutar
            *args, **kwargs: Argumentos para coro_func
        
        Returns:
            Result de coro_func
        """
        async with self._lock:
            # Si ya hay request pendiente, reusar
            if key in self._pending:
                self._hits += 1
                logger.debug(f"Dedup HIT: {key[:16]}... (waiting for result)")
                future = self._pending[key]
        
        # Si existe, esperar resultado
        if key in self._pending:
            try:
                result = await asyncio.wait_for(
                    future,
                    timeout=self.ttl_seconds
                )
                return result
            except asyncio.TimeoutError:
                logger.warning(f"Dedup timeout for {key[:16]}...")
                # Continuar con ejecución normal
        
        # No existe, ejecutar
        self._misses += 1
        
        # Crear future
        future = asyncio.Future()
        
        async with self._lock:
            self._pending[key] = future
        
        try:
            # Ejecutar
            result = await coro_func(*args, **kwargs)
            
            # Marcar como completo
            if not future.done():
                future.set_result(result)
            
            return result
        
        except Exception as e:
            # Propagar error
            if not future.done():
                future.set_exception(e)
            raise
        
        finally:
            # Cleanup
            async with self._lock:
                self._pending.pop(key, None)
    
    def get_stats(self) -> dict:
        """Estadísticas"""
        total = self._hits + self._misses
        hit_rate = (self._hits / total * 100) if total > 0 else 0
        
        return {
            'pending_requests': len(self._pending),
            'hits': self._hits,
            'misses': self._misses,
            'hit_rate': round(hit_rate, 2)
        }
    
    def clear(self):
        """Clear all pending"""
        self._pending.clear()
        self._hits = 0
        self._misses = 0


# Global instance
_deduplicator = RequestDeduplicator()


def get_deduplicator() -> RequestDeduplicator:
    """Get global deduplicator"""
    return _deduplicator