"""
Aplicación Flask principal
"""
import asyncio
import time
import atexit
from collections import defaultdict
from dataclasses import asdict

from flask import Flask, request, jsonify, g

from config import Config
from models import CircuitBreaker, PerformanceMetrics
from rate_limiter import RateLimiter
from resources import init_resources, cleanup_resources, get_redis_client, get_http_client
from search_service import process_similarity_batch


# Inicialización global
app = Flask(__name__)
rate_limiter = RateLimiter()
circuit_breakers = defaultdict(CircuitBreaker)
metrics = PerformanceMetrics()
app_start_time = time.time()


@app.before_request
def before_request():
    """Tracking de inicio de request"""
    g.start_time = time.time()


@app.after_request
def after_request(response):
    """Tracking de métricas por request"""
    if hasattr(g, 'start_time'):
        latency = time.time() - g.start_time
        metrics.record_request(latency, response.status_code >= 400)
    return response


@app.route('/api/similarity-search', methods=['POST'])
def similarity_search():
    """
    Endpoint principal de búsqueda de similitud
    
    Body JSON:
    {
        "data": [theme, idiom, [[page, paragraph, text], ...]],
        "sources": ["crossref", "pubmed", ...] (opcional)
    }
    """
    try:
        data = request.get_json()
        
        if not data or 'data' not in data:
            return jsonify({"error": "Datos inválidos. Se requiere campo 'data'"}), 400
        
        input_data = data['data']
        
        if not isinstance(input_data, list) or len(input_data) < 3:
            return jsonify({
                "error": "Formato inválido. Se esperaba [theme, idiom, [...]]"
            }), 400
        
        theme = input_data[0]
        idiom = input_data[1]
        texts = input_data[2]
        sources = data.get('sources', None)
        
        # Validación
        if not isinstance(texts, list):
            return jsonify({
                "error": "El tercer elemento debe ser una lista de tuplas"
            }), 400
        
        if not theme or not idiom:
            return jsonify({
                "error": "Theme e idiom son requeridos"
            }), 400
        
        # Procesar búsqueda
        results = process_similarity_batch(
            texts, 
            theme, 
            idiom,
            get_redis_client(),
            get_http_client(),
            rate_limiter,
            sources
        )
        
        # Convertir a JSON
        response = [asdict(r) for r in results]
        
        return jsonify({
            "results": response,
            "count": len(response),
            "processed_texts": len(texts)
        }), 200
    
    except Exception as e:
        metrics.record_request(0, error=True)
        return jsonify({
            "error": f"Error en el procesamiento: {str(e)}"
        }), 500


@app.route('/api/health', methods=['GET'])
def health_check():
    """Endpoint de verificación de salud con métricas"""
    circuit_status = {
        source: breaker.state.value 
        for source, breaker in circuit_breakers.items()
    }
    
    stats = metrics.get_stats()
    stats['uptime_seconds'] = time.time() - app_start_time
    
    return jsonify({
        "status": "healthy",
        "model": Config.EMBEDDING_MODEL,
        "redis": get_redis_client() is not None,
        "http_pool": get_http_client() is not None,
        "metrics": stats,
        "circuit_breakers": circuit_status,
        "config": {
            "similarity_threshold": Config.SIMILARITY_THRESHOLD,
            "batch_size": Config.EMBEDDING_BATCH_SIZE,
            "max_results_per_source": Config.MAX_RESULTS_PER_SOURCE
        }
    }), 200


@app.route('/api/metrics', methods=['GET'])
def get_metrics():
    """Endpoint dedicado a métricas (Prometheus-compatible)"""
    stats = metrics.get_stats()
    uptime = time.time() - app_start_time
    
    prometheus_format = f"""
# HELP api_requests_total Total number of API requests
# TYPE api_requests_total counter
api_requests_total {stats['requests']}

# HELP api_latency_ms Average request latency in milliseconds
# TYPE api_latency_ms gauge
api_latency_ms {stats['avg_latency_ms']}

# HELP api_error_rate Percentage of failed requests
# TYPE api_error_rate gauge
api_error_rate {stats['error_rate']}

# HELP cache_hit_rate Percentage of cache hits
# TYPE cache_hit_rate gauge
cache_hit_rate {stats['cache_hit_rate']}

# HELP uptime_seconds Application uptime in seconds
# TYPE uptime_seconds counter
uptime_seconds {uptime}
"""
    
    return prometheus_format, 200, {'Content-Type': 'text/plain; charset=utf-8'}


@app.route('/api/reset-limits', methods=['POST'])
def reset_limits():
    """Reinicia los contadores de límites de API"""
    asyncio.run(rate_limiter.reset())
    
    # Reiniciar circuit breakers
    from models import CircuitState
    for breaker in circuit_breakers.values():
        breaker.failure_count = 0
        breaker.state = CircuitState.CLOSED
    
    return jsonify({
        "message": "Límites y circuit breakers reiniciados"
    }), 200


@app.route('/api/cache/clear', methods=['POST'])
def clear_cache():
    """Limpia el caché de Redis"""
    redis_client = get_redis_client()
    if not redis_client:
        return jsonify({"error": "Redis no disponible"}), 503
    
    try:
        asyncio.run(redis_client.flushdb())
        return jsonify({"message": "Caché limpiado"}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/benchmark', methods=['POST'])
def benchmark():
    """
    Endpoint para benchmarking
    """
    try:
        data = request.get_json()
        num_texts = data.get('num_texts', 10)
        
        # Generar textos de prueba
        test_texts = [
            (f"page_{i}", f"para_{i}", f"machine learning artificial intelligence neural networks deep learning research paper methodology results conclusion {i}")
            for i in range(num_texts)
        ]
        
        start = time.time()
        results = process_similarity_batch(
            test_texts, 
            "machine learning", 
            "en",
            get_redis_client(),
            get_http_client(),
            rate_limiter,
            sources=["semantic_scholar"]
        )
        elapsed = time.time() - start
        
        return jsonify({
            "num_texts": num_texts,
            "num_results": len(results),
            "elapsed_seconds": round(elapsed, 3),
            "throughput_texts_per_sec": round(num_texts / elapsed, 2),
            "avg_latency_ms": round(elapsed / num_texts * 1000, 2)
        }), 200
    
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# Inicialización al primer request
@app.before_first_request
def startup():
    """Inicializa recursos al primer request"""
    asyncio.run(init_resources())
    print("🚀 Sistema optimizado iniciado")


# Cleanup al cerrar
def shutdown():
    """Limpia recursos al cerrar"""
    asyncio.run(cleanup_resources())
    print("👋 Recursos liberados")


atexit.register(shutdown)


if __name__ == '__main__':
    print("=" * 60)
    print("🔥 SERVIDOR OPTIMIZADO INICIADO")
    print("=" * 60)
    print(f"📊 Modelo: {Config.EMBEDDING_MODEL}")
    print(f"🎯 Umbral de similitud: {Config.SIMILARITY_THRESHOLD * 100}%")
    print(f"📢 Batch size: {Config.EMBEDDING_BATCH_SIZE}")
    print(f"🌐 HTTP/2 Pool: {Config.POOL_CONNECTIONS} conexiones")
    print(f"⚡ Circuit Breaker: ✅ Activo")
    print(f"🚀 Rate Limiting: ✅ Thread-safe")
    print("=" * 60)
    print("\n🔌 Endpoints disponibles:")
    print("   POST /api/similarity-search  - Búsqueda principal")
    print("   GET  /api/health             - Estado del sistema")
    print("   GET  /api/metrics            - Métricas Prometheus")
    print("   POST /api/reset-limits       - Reiniciar límites")
    print("   POST /api/cache/clear        - Limpiar caché")
    print("   POST /api/benchmark          - Test de performance")
    print("=" * 60)
    
    # Inicializar recursos
    asyncio.run(init_resources())
    
    app.run(
        host='0.0.0.0', 
        port=5000, 
        debug=False, 
        threaded=True
    )