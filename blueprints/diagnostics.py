"""
Blueprint de Diagnósticos - Health checks y monitoreo
"""
import time
import logging
from collections import defaultdict
from flask import Blueprint, request, jsonify

from models import CircuitBreaker, PerformanceMetrics
from resources import get_redis_client, get_http_client
from faiss_service import get_faiss_index
from api_validator import get_api_validator
from profiler import get_profiler
from config import Config

logger = logging.getLogger(__name__)

# Crear blueprint
diagnostics_bp = Blueprint('diagnostics', __name__, url_prefix='/api')

# Métricas globales (se pasarán desde app.py)
_metrics = None
_circuit_breakers = None
_app_start_time = None


def init_diagnostics_blueprint(metrics, circuit_breakers, app_start_time):
    """Inicializa con referencias globales"""
    global _metrics, _circuit_breakers, _app_start_time
    _metrics = metrics
    _circuit_breakers = circuit_breakers
    _app_start_time = app_start_time


@diagnostics_bp.route('/health', methods=['GET'])
def health():
    """Endpoint de verificación de salud con métricas"""
    circuit_status = {
        source: breaker.state.value 
        for source, breaker in _circuit_breakers.items()
    } if _circuit_breakers else {}
    
    stats = _metrics.get_stats() if _metrics else {}
    stats['uptime_seconds'] = round(time.time() - _app_start_time, 2) if _app_start_time else 0
    
    # Stats de FAISS
    faiss_index = get_faiss_index()
    faiss_stats = faiss_index.get_stats() if faiss_index else None
    
    redis_status = "connected" if get_redis_client() else "disconnected"
    http_status = "active" if get_http_client() else "inactive"
    
    overall_healthy = (
        redis_status == "connected" and 
        http_status == "active" and
        (not faiss_stats or not faiss_stats.get('corrupted', False))
    )
    
    return jsonify({
        "status": "healthy" if overall_healthy else "degraded",
        "model": Config.EMBEDDING_MODEL,
        "redis": redis_status,
        "http_pool": http_status,
        "faiss": faiss_stats,
        "metrics": stats,
        "circuit_breakers": circuit_status,
        "config": {
            "similarity_threshold": Config.SIMILARITY_THRESHOLD,
            "batch_size": Config.EMBEDDING_BATCH_SIZE,
            "max_results_per_source": Config.MAX_RESULTS_PER_SOURCE
        }
    }), 200 if overall_healthy else 503


@diagnostics_bp.route('/metrics', methods=['GET'])
def metrics():
    """Endpoint dedicado a métricas (Prometheus-compatible)"""
    stats = _metrics.get_stats() if _metrics else {
        'requests': 0,
        'avg_latency_ms': 0,
        'error_rate': 0,
        'cache_hit_rate': 0
    }
    uptime = time.time() - _app_start_time if _app_start_time else 0
    
    faiss_index = get_faiss_index()
    faiss_papers = faiss_index.index.ntotal if faiss_index else 0
    
    prometheus_format = f"""# HELP api_requests_total Total number of API requests
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

# HELP faiss_indexed_papers Total papers in FAISS index
# TYPE faiss_indexed_papers gauge
faiss_indexed_papers {faiss_papers}
"""
    
    return prometheus_format, 200, {'Content-Type': 'text/plain; charset=utf-8'}


@diagnostics_bp.route('/diagnostics/full', methods=['GET'])
def full_diagnostics():
    """Diagnóstico completo del sistema"""
    import asyncio
    
    # Validar APIs
    validator = get_api_validator()
    http_client = get_http_client()
    
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        if http_client:
            loop.run_until_complete(validator.validate_all_apis(http_client))
        api_report = validator.get_health_report()
    finally:
        loop.close()
    
    # Profiler
    profiler = get_profiler()
    perf_report = profiler.generate_report()
    
    # FAISS Stats
    faiss_index = get_faiss_index()
    faiss_stats = faiss_index.get_stats() if faiss_index else None
    
    # Redis/HTTP
    redis_ok = get_redis_client() is not None
    http_ok = get_http_client() is not None
    
    # Circuit Breakers
    circuit_status = {
        source: breaker.state.value 
        for source, breaker in _circuit_breakers.items()
    } if _circuit_breakers else {}
    
    overall_healthy = (
        api_report['summary']['overall_health'] == "healthy" and
        perf_report['system']['cpu']['percent'] < 80 and
        redis_ok and http_ok
    )
    
    recommendations = perf_report['recommendations'].copy()
    if validator.get_failing_apis():
        recommendations.append(
            f"⚠️ {len(validator.get_failing_apis())} APIs con problemas"
        )
    else:
        recommendations.append("✅ Todas las APIs operativas")
    
    return jsonify({
        "timestamp": time.time(),
        "overall_health": "healthy" if overall_healthy else "degraded",
        "components": {
            "faiss": faiss_stats,
            "redis": {"status": "connected" if redis_ok else "disconnected"},
            "http_pool": {"status": "active" if http_ok else "inactive"},
            "apis": api_report,
            "performance": perf_report,
            "circuit_breakers": circuit_status
        },
        "recommendations": recommendations
    }), 200


@diagnostics_bp.route('/validate-apis', methods=['POST'])
def validate_apis():
    """Valida todas las APIs externas"""
    import asyncio
    
    try:
        data = request.get_json() or {}
        sources = data.get('sources', None)
        
        validator = get_api_validator()
        http_client = get_http_client()
        
        if not http_client:
            return jsonify({"error": "HTTP client no disponible"}), 503
        
        # Ejecutar validación en nuevo event loop
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            if sources:
                async def validate_sources():
                    tasks = [validator.validate_api(s, http_client) for s in sources]
                    return await asyncio.gather(*tasks)
                
                results = loop.run_until_complete(validate_sources())
                for result in results:
                    validator.metrics[result.source] = result
            else:
                loop.run_until_complete(validator.validate_all_apis(http_client))
            
            report = validator.get_health_report()
            return jsonify(report), 200
        finally:
            loop.close()
    
    except Exception as e:
        logger.error("Error validando APIs", extra={"error": str(e)})
        return jsonify({"error": str(e)}), 500


@diagnostics_bp.route('/api-health', methods=['GET'])
def api_health():
    """Retorna estado de salud de APIs (último check)"""
    validator = get_api_validator()
    report = validator.get_health_report()
    
    return jsonify(report), 200


@diagnostics_bp.route('/failing-apis', methods=['GET'])
def failing_apis():
    """Lista APIs que están fallando"""
    validator = get_api_validator()
    failing = validator.get_failing_apis()
    
    return jsonify({
        "failing_apis": failing,
        "count": len(failing)
    }), 200


@diagnostics_bp.route('/profiler/stats', methods=['GET'])
def profiler_stats():
    """Estadísticas de performance del sistema"""
    profiler = get_profiler()
    report = profiler.generate_report()
    
    return jsonify(report), 200


@diagnostics_bp.route('/profiler/bottlenecks', methods=['GET'])
def bottlenecks():
    """Identifica cuellos de botella"""
    top_n = min(request.args.get('top', 5, type=int), 20)
    profiler = get_profiler()
    bottlenecks_list = profiler.get_bottlenecks(top_n)
    
    return jsonify({
        "bottlenecks": bottlenecks_list,
        "count": len(bottlenecks_list)
    }), 200


@diagnostics_bp.route('/profiler/clear', methods=['POST'])
def clear_profiler():
    """Limpia snapshots del profiler"""
    profiler = get_profiler()
    profiler.clear_snapshots()
    
    logger.info("Snapshots del profiler limpiados")
    return jsonify({"message": "Snapshots limpiados"}), 200