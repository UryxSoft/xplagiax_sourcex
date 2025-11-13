"""
Rate limiter thread-safe
"""
import asyncio
import time
from collections import defaultdict

from config import Config


class RateLimiter:
    """Rate limiter thread-safe con ventana deslizante"""
    def __init__(self):
        self._requests = defaultdict(list)
        self._lock = asyncio.Lock()
    
    async def can_make_request(self, source: str) -> bool:
        async with self._lock:
            now = time.time()
            limit = Config.RATE_LIMITS.get(source, 100)
            
            # Limpiar requests antiguos (ventana de 60s)
            self._requests[source] = [
                ts for ts in self._requests[source] 
                if now - ts < 60
            ]
            
            if len(self._requests[source]) < limit:
                self._requests[source].append(now)
                return True
            return False
    
    async def reset(self):
        async with self._lock:
            self._requests.clear()
