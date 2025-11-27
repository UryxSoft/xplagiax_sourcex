"""
Blueprint de Administración - Endpoints de gestión y mantenimiento
"""
import time
import logging
from flask import Blueprint, request, jsonify
from flask_limiter import Limiter

from auth import require_api_key
from resources import get_redis_client
from profiler import profile
from faiss_service import get_faiss_index
from config import Config

logger = logging.getLogger(__name__)

# Crear blueprint
admin_bp = Blueprint('admin', __name__, url_prefix='/api')

# Rate limiter (se configurará desde app.py)
limiter = None


def init_admin_blueprint(app_limiter):
    """Inicializa el limiter del blueprint"""
    global limiter
    limiter = app_limiter


@admin_bp.route('/reset-limits', methods=['POST'])
@require_api_key
def reset_limits():
    """
    Reinicia los contadores de límites de API
    Requiere autenticación
    """
    from rate_limiter import RateLimiter
    from models import CircuitBreaker, CircuitState
    from collections import defaultdict
    
    # Crear nuevo rate limiter
    rate_limiter = RateLimiter()
    
    import asyncio
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        loop.run_until_complete(rate_limiter.reset())
    finally:
        loop.close()
    
    # Reiniciar circuit breakers (esto requeriría acceso global, lo dejamos como está)
    
    logger.info("Límites reiniciados por admin", extra={
        "admin_ip": request.remote_addr
    })
    
    return jsonify({
        "message": "Límites reiniciados exitosamente"
    }), 200


@admin_bp.route('/cache/clear', methods=['POST'])
@require_api_key
def clear_cache():
    """
    Limpia el caché de Redis (DESTRUCTIVO)
    Requiere autenticación
    """
    redis_client = get_redis_client()
    if not redis_client:
        return jsonify({"error": "Redis no disponible"}), 503
    
    try:
        import asyncio
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            loop.run_until_complete(redis_client.flushdb())
            logger.warning("Caché Redis limpiado por admin", extra={
                "admin_ip": request.remote_addr
            })
            return jsonify({"message": "Caché limpiado"}), 200
        finally:
            loop.close()
    except Exception as e:
        logger.error("Error limpiando caché", extra={"error": str(e)})
        return jsonify({"error": str(e)}), 500


@admin_bp.route('/benchmark', methods=['POST'])
@limiter.limit("5 per hour")
@profile
def benchmark():
    """
    Endpoint para benchmarking - solo FAISS, sin APIs
    Rate limited: 5 requests/hour
    """
    try:
        data = request.get_json() or {}
        num_texts = min(data.get('num_texts', 10), 50)  # Máximo 50
        
        faiss_index = get_faiss_index()
        
        if not faiss_index or faiss_index.index.ntotal == 0:
            return jsonify({
                "error": "FAISS vacío. Primero haz búsquedas reales para poblarlo."
            }), 400
        
        # Textos de prueba DIVERSOS
        test_queries = [
            "machine learning algorithms",
            "neural network architectures", 
            "deep learning optimization",
            "natural language processing",
            "computer vision techniques",
            "reinforcement learning agents",
            "transformer models attention",
            "convolutional neural networks",
            "recurrent neural networks",
            "generative adversarial networks"
        ]
        
        # Usar solo los primeros num_texts
        queries = (test_queries * ((num_texts // len(test_queries)) + 1))[:num_texts]
        
        # Benchmark SOLO de FAISS (rápido, determinístico)
        start = time.time()
        results = faiss_index.search_batch(
            queries,
            k=10,
            threshold=Config.SIMILARITY_THRESHOLD
        )
        elapsed = time.time() - start
        
        total_results = sum(len(r) for r in results)
        
        logger.info("Benchmark ejecutado", extra={
            "num_queries": num_texts,
            "elapsed_seconds": elapsed,
            "admin_ip": request.remote_addr
        })
        
        return jsonify({
            "benchmark_type": "faiss_only",
            "num_queries": num_texts,
            "total_results": total_results,
            "elapsed_seconds": round(elapsed, 3),
            "throughput_queries_per_sec": round(num_texts / elapsed, 2) if elapsed > 0 else 0,
            "avg_latency_ms": round(elapsed / num_texts * 1000, 2) if num_texts > 0 else 0,
            "faiss_index_size": faiss_index.index.ntotal,
            "faiss_strategy": faiss_index.current_strategy
        }), 200
    
    except Exception as e:
        logger.error("Error en benchmark", extra={"error": str(e)})
        return jsonify({"error": str(e)}), 500


@admin_bp.route('/deduplication/stats', methods=['GET'])
def deduplication_stats():
    """Estadísticas del sistema de deduplicación"""
    try:
        import asyncio
        from deduplication_service import get_deduplicator
        
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            deduplicator = loop.run_until_complete(get_deduplicator())
            stats = loop.run_until_complete(deduplicator.get_stats())
            return jsonify(stats), 200
        finally:
            loop.close()
    
    except Exception as e:
        logger.error("Error obteniendo stats de deduplicación", extra={"error": str(e)})
        return jsonify({"error": str(e)}), 500