"""
Decoradores para circuit breaker
"""
from functools import wraps


def with_circuit_breaker(source: str):
    """Decorador para aplicar circuit breaker a búsquedas"""
    def decorator(func):
        @wraps(func)
        async def wrapper(circuit_breakers, *args, **kwargs):
            breaker = circuit_breakers[source]
            
            if not breaker.can_attempt():
                print(f"⚡ Circuit breaker OPEN para {source}")
                return []
            
            try:
                result = await func(*args, **kwargs)
                breaker.record_success()
                return result
            except Exception as e:
                breaker.record_failure()
                print(f"❌ Error en {source}: {e}")
                return []
        
        return wrapper
    return decorator