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
from api_validator import get_api_validator
from profiler import get_profiler, profile
from faiss_service import get_faiss_index, init_faiss_index

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
        "sources": ["crossref", "pubmed", ...] (opcional),
        "use_faiss": true (opcional, default: true)
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
        use_faiss = data.get('use_faiss', True)
        
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
            sources,
            use_faiss
        )
        
        # Convertir a JSON
        response = [asdict(r) for r in results]
        
        return jsonify({
            "results": response,
            "count": len(response),
            "processed_texts": len(texts),
            "faiss_enabled": use_faiss and get_faiss_index() is not None
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
    
    # Stats de FAISS
    faiss_index = get_faiss_index()
    faiss_stats = faiss_index.get_stats() if faiss_index else None
    
    return jsonify({
        "status": "healthy",
        "model": Config.EMBEDDING_MODEL,
        "redis": get_redis_client() is not None,
        "http_pool": get_http_client() is not None,
        "faiss": faiss_stats,
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


@app.route('/api/faiss/stats', methods=['GET'])
def faiss_stats():
    """Estadísticas del índice FAISS"""
    faiss_index = get_faiss_index()
    
    if not faiss_index:
        return jsonify({"error": "FAISS no disponible"}), 503
    
    return jsonify(faiss_index.get_stats()), 200


@app.route('/api/faiss/clear', methods=['POST'])
def faiss_clear():
    """Limpia el índice FAISS"""
    faiss_index = get_faiss_index()
    
    if not faiss_index:
        return jsonify({"error": "FAISS no disponible"}), 503
    
    faiss_index.clear()
    return jsonify({"message": "Índice FAISS limpiado"}), 200


@app.route('/api/faiss/save', methods=['POST'])
def faiss_save():
    """Guarda el índice FAISS en disco"""
    faiss_index = get_faiss_index()
    
    if not faiss_index:
        return jsonify({"error": "FAISS no disponible"}), 503
    
    try:
        faiss_index.save()
        return jsonify({
            "message": "Índice guardado exitosamente",
            "stats": faiss_index.get_stats()
        }), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/faiss/search', methods=['POST'])
def faiss_search():
    """Búsqueda directa en FAISS"""
    faiss_index = get_faiss_index()
    
    if not faiss_index:
        return jsonify({"error": "FAISS no disponible"}), 503
    
    try:
        data = request.get_json()
        query = data.get('query')
        k = data.get('k', 10)
        threshold = data.get('threshold', 0.7)
        
        if not query:
            return jsonify({"error": "Query requerido"}), 400
        
        results = faiss_index.search(query, k=k, threshold=threshold)
        
        return jsonify({
            "query": query,
            "results": results,
            "count": len(results)
        }), 200
    
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# ========== ENDPOINTS DE VALIDACIÓN DE APIS ==========
@app.route('/api/validate-apis', methods=['POST'])
async def validate_external_apis():
    """
    Valida todas las APIs externas
    
    POST /api/validate-apis
    {
        "sources": ["crossref", "pubmed"]  // Opcional, default: todas
    }
    """
    try:
        data = request.get_json() or {}
        sources = data.get('sources', None)
        
        validator = get_api_validator()
        
        if sources:
            # Validar solo fuentes específicas
            async with httpx.AsyncClient() as client:
                tasks = [validator.validate_api(s, client) for s in sources]
                results = await asyncio.gather(*tasks)
            
            metrics = {r.source: r for r in results}
        else:
            # Validar todas
            metrics = await validator.validate_all_apis()
        
        report = validator.get_health_report()
        
        return jsonify(report), 200
    
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/api-health', methods=['GET'])
def get_api_health():
    """
    Retorna estado de salud de APIs (último check)
    
    GET /api/api-health
    """
    validator = get_api_validator()
    report = validator.get_health_report()
    
    return jsonify(report), 200


@app.route('/api/failing-apis', methods=['GET'])
def get_failing_apis():
    """
    Lista APIs que están fallando
    
    GET /api/failing-apis
    """
    validator = get_api_validator()
    failing = validator.get_failing_apis()
    
    return jsonify({
        "failing_apis": failing,
        "count": len(failing)
    }), 200


# ========== ENDPOINTS DE PROFILING ==========

@app.route('/api/profiler/stats', methods=['GET'])
def get_profiler_stats():
    """
    Estadísticas de performance del sistema
    
    GET /api/profiler/stats
    """
    profiler = get_profiler()
    report = profiler.generate_report()
    
    return jsonify(report), 200


@app.route('/api/profiler/bottlenecks', methods=['GET'])
def get_bottlenecks():
    """
    Identifica cuellos de botella
    
    GET /api/profiler/bottlenecks?top=10
    """
    top_n = request.args.get('top', 5, type=int)
    profiler = get_profiler()
    bottlenecks = profiler.get_bottlenecks(top_n)
    
    return jsonify({
        "bottlenecks": bottlenecks,
        "count": len(bottlenecks)
    }), 200


@app.route('/api/profiler/clear', methods=['POST'])
def clear_profiler_snapshots():
    """
    Limpia snapshots del profiler
    
    POST /api/profiler/clear
    """
    profiler = get_profiler()
    profiler.clear_snapshots()
    
    return jsonify({"message": "Snapshots limpiados"}), 200


# ========== ENDPOINTS DE DIAGNÓSTICO AVANZADO ==========

@app.route('/api/diagnostics/full', methods=['GET'])
async def full_diagnostics():
    """
    Diagnóstico completo del sistema
    
    GET /api/diagnostics/full
    """
    # 1. Validar APIs
    validator = get_api_validator()
    api_health = await validator.validate_all_apis()
    api_report = validator.get_health_report()
    
    # 2. Profiler
    profiler = get_profiler()
    perf_report = profiler.generate_report()
    
    # 3. FAISS Stats
    faiss_index = get_faiss_index()
    faiss_stats = faiss_index.get_stats() if faiss_index else None
    
    # 4. Redis/HTTP
    redis_ok = get_redis_client() is not None
    http_ok = get_http_client() is not None
    
    # 5. Circuit Breakers
    circuit_status = {
        source: breaker.state.value 
        for source, breaker in circuit_breakers.items()
    }
    
    return jsonify({
        "timestamp": time.time(),
        "overall_health": "healthy" if api_report['summary']['overall_health'] == "healthy" and perf_report['system']['cpu']['percent'] < 80 else "degraded",
        "components": {
            "faiss": faiss_stats,
            "redis": {"status": "connected" if redis_ok else "disconnected"},
            "http_pool": {"status": "active" if http_ok else "inactive"},
            "apis": api_report,
            "performance": perf_report,
            "circuit_breakers": circuit_status
        },
        "recommendations": perf_report['recommendations'] + [
            f"⚠️ {len(validator.get_failing_apis())} APIs con problemas" 
            if validator.get_failing_apis() else "✅ Todas las APIs operativas"
        ]
    }), 200


# ========== BENCHMARK AVANZADO ==========

@app.route('/api/benchmark/advanced', methods=['POST'])
@profile  # Decorador de profiling
def advanced_benchmark():
    """
    Benchmark avanzado con profiling
    
    POST /api/benchmark/advanced
    {
        "num_texts": 50,
        "use_faiss": true,
        "parallel": true
    }
    """
    try:
        data = request.get_json() or {}
        num_texts = data.get('num_texts', 20)
        use_faiss = data.get('use_faiss', True)
        parallel = data.get('parallel', True)
        
        # Generar textos de prueba
        test_texts = [
            (f"page_{i}", f"para_{i}", 
             f"machine learning artificial intelligence neural networks deep learning "
             f"convolutional networks image recognition natural language processing {i}")
            for i in range(num_texts)
        ]
        
        # Medir con profiler
        profiler = get_profiler()
        
        start = time.time()
        results = process_similarity_batch(
            test_texts,
            "machine learning",
            "en",
            get_redis_client(),
            get_http_client(),
            rate_limiter,
            use_faiss=use_faiss
        )
        elapsed = time.time() - start
        
        # Obtener stats del profiler
        perf_stats = profiler.get_system_stats()
        
        return jsonify({
            "benchmark": {
                "num_texts": num_texts,
                "num_results": len(results),
                "elapsed_seconds": round(elapsed, 3),
                "throughput_texts_per_sec": round(num_texts / elapsed, 2),
                "avg_latency_ms": round(elapsed / num_texts * 1000, 2)
            },
            "performance": {
                "cpu_percent": perf_stats['cpu']['percent'],
                "memory_used_mb": perf_stats['memory']['used_mb'],
                "memory_percent": perf_stats['memory']['percent']
            },
            "config": {
                "faiss_enabled": use_faiss,
                "parallel_processing": parallel
            }
        }), 200
    
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ========== OPTIMIZACIÓN AUTOMÁTICA ==========

@app.route('/api/optimize/auto', methods=['POST'])
def auto_optimize():
    """
    Optimización automática del sistema
    
    POST /api/optimize/auto
    """
    recommendations = []
    
    # 1. Verificar FAISS
    faiss_index = get_faiss_index()
    if faiss_index:
        stats = faiss_index.get_stats()
        
        # Sugerir upgrade si es necesario
        if stats['total_papers'] > 10000 and stats.get('strategy') == 'flat':
            recommendations.append({
                "component": "FAISS",
                "action": "upgrade_to_hnsw",
                "reason": f"{stats['total_papers']} papers detectados, HNSW sería 100x más rápido"
            })
        
        if stats.get('corrupted'):
            recommendations.append({
                "component": "FAISS",
                "action": "repair_index",
                "reason": "Índice corrupto detectado"
            })
    
    # 2. Verificar memoria
    profiler = get_profiler()
    sys_stats = profiler.get_system_stats()
    
    if sys_stats['memory']['percent'] > 85:
        recommendations.append({
            "component": "Memory",
            "action": "enable_compression",
            "reason": f"Memoria alta ({sys_stats['memory']['percent']}%), activar compresión FAISS"
        })
    
    # 3. Verificar APIs
    validator = get_api_validator()
    failing = validator.get_failing_apis()
    
    if failing:
        recommendations.append({
            "component": "APIs",
            "action": "disable_failing_apis",
            "reason": f"Desactivar temporalmente: {', '.join(failing)}"
        })
    
    # 4. Aplicar optimizaciones automáticas
    applied_optimizations = []
    
    for rec in recommendations:
        if rec['action'] == 'repair_index' and faiss_index:
            faiss_index.auto_repair()
            applied_optimizations.append(f"✅ Índice FAISS reparado")
        
        if rec['action'] == 'upgrade_to_hnsw':
            applied_optimizations.append(f"💡 Sugerencia: Reiniciar con init_optimized_faiss_index()")
    
    return jsonify({
        "recommendations": recommendations,
        "applied": applied_optimizations,
        "status": "optimized" if applied_optimizations else "no_action_needed"
    }), 200


# ========== ENDPOINT DE STRESS TEST ==========

@app.route('/api/stress-test', methods=['POST'])
async def stress_test():
    """
    Stress test del sistema
    
    POST /api/stress-test
    {
        "concurrent_requests": 10,
        "texts_per_request": 5
    }
    """
    try:
        data = request.get_json() or {}
        concurrent = data.get('concurrent_requests', 10)
        texts_per_req = data.get('texts_per_request', 5)
        
        # Generar requests concurrentes
        test_texts = [
            (f"p{i}", f"t{j}", f"test text {i}-{j} machine learning neural networks")
            for i in range(concurrent)
            for j in range(texts_per_req)
        ]
        
        # Medir
        start = time.time()
        
        # Simular requests concurrentes
        tasks = []
        for i in range(concurrent):
            batch = test_texts[i*texts_per_req:(i+1)*texts_per_req]
            task = asyncio.create_task(
                asyncio.to_thread(
                    process_similarity_batch,
                    batch,
                    "test",
                    "en",
                    get_redis_client(),
                    get_http_client(),
                    rate_limiter
                )
            )
            tasks.append(task)
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        elapsed = time.time() - start
        
        # Contar errores
        errors = sum(1 for r in results if isinstance(r, Exception))
        success = len(results) - errors
        
        return jsonify({
            "test": {
                "concurrent_requests": concurrent,
                "texts_per_request": texts_per_req,
                "total_texts": len(test_texts)
            },
            "results": {
                "successful_requests": success,
                "failed_requests": errors,
                "total_time_seconds": round(elapsed, 3),
                "avg_time_per_request_ms": round((elapsed / concurrent) * 1000, 2),
                "throughput_requests_per_sec": round(concurrent / elapsed, 2)
            },
            "verdict": "PASS" if errors == 0 and elapsed < (concurrent * 2) else "FAIL"
        }), 200
    
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# Inicialización al primer request
@app.before_first_request
def startup():
    """Inicializa recursos al primer request"""
    asyncio.run(init_resources())
    init_faiss_index()
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
    print("   GET  /api/faiss/stats        - Estadísticas FAISS")
    print("   POST /api/faiss/clear        - Limpiar índice FAISS")
    print("   POST /api/faiss/save         - Guardar índice FAISS")
    print("   POST /api/faiss/search       - Búsqueda directa FAISS")
    print("=" * 60)
    
    # Inicializar recursos
    asyncio.run(init_resources())
    init_faiss_index()
    
    app.run(
        host='0.0.0.0', 
        port=5000, 
        debug=False, 
        threaded=True
    )