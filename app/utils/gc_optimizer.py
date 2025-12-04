"""
Garbage Collection optimizer
"""
import gc
import logging

logger = logging.getLogger(__name__)


def optimize_gc():
    """
    Optimiza GC para aplicaciones de alto throughput
    
    - Aumenta thresholds (menos colecciones frecuentes)
    - Deshabilita gen2 durante requests
    - Fuerza colección en momentos apropiados
    """
    # ✅ Aumentar thresholds (default: 700, 10, 10)
    gc.set_threshold(5000, 50, 50)  # Gen0, Gen1, Gen2
    
    # ✅ Deshabilitar gen2 (más caro)
    # Se ejecutará manualmente en background
    gc.disable()
    
    # ✅ Solo gen0 automático
    gc.set_threshold(10000, 0, 0)
    gc.enable()
    
    logger.info("✅ GC optimized: gen0=10000, gen1/2=manual")
    
    return True


def manual_gc_cycle():
    """
    Ejecuta full GC cycle (llamar periódicamente en background)
    """
    collected = gc.collect()
    logger.debug(f"GC cycle: {collected} objects collected")
    return collected


def get_gc_stats() -> dict:
    """Estadísticas de GC"""
    stats = gc.get_stats()
    count = gc.get_count()
    
    return {
        'counts': {
            'gen0': count[0],
            'gen1': count[1],
            'gen2': count[2]
        },
        'thresholds': gc.get_threshold(),
        'stats': stats
    }