import httpx
from typing import Optional

class OptimizedHTTPClient:
    """
    HTTP client ultra-optimizado con connection pooling
    """
    
    def __init__(self):
        # ✅ Limites de conexiones
        limits = httpx.Limits(
            max_keepalive_connections=20,  # Keepalive pool
            max_connections=100,            # Total connections
            keepalive_expiry=30.0          # 30s keepalive
        )
        
        # ✅ Timeouts optimizados
        timeout = httpx.Timeout(
            connect=5.0,    # Rápido connect
            read=10.0,      # Leer
            write=5.0,      # Escribir
            pool=2.0        # Pool timeout
        )
        
        # ✅ HTTP/2 enabled
        self.client = httpx.AsyncClient(
            limits=limits,
            timeout=timeout,
            http2=True,              # HTTP/2 multiplexing
            follow_redirects=True,
            max_redirects=3
        )
    
    async def get(self, url: str, **kwargs):
        """GET con retry automático"""
        for attempt in range(3):
            try:
                response = await self.client.get(url, **kwargs)
                response.raise_for_status()
                return response
            except httpx.HTTPStatusError as e:
                if e.response.status_code >= 500 and attempt < 2:
                    await asyncio.sleep(0.5 * (attempt + 1))
                    continue
                raise
            except httpx.RequestError as e:
                if attempt < 2:
                    await asyncio.sleep(0.5 * (attempt + 1))
                    continue
                raise
    
    async def close(self):
        """Cerrar conexiones"""
        await self.client.aclose()