"""
Aplicación Flask principal - VERSIÓN CORREGIDA
"""
import asyncio
import time
import atexit
import os
import logging
from collections import defaultdict
from dataclasses import asdict
from flask import Flask, request, jsonify, g
from flask_cors import CORS
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

from config import Config
from models import CircuitBreaker, PerformanceMetrics
from rate_limiter import RateLimiter
from resources import init_resources, cleanup_resources, get_redis_client, get_http_client
from search_service import process_similarity_batch
from api_validator import get_api_validator
from profiler import get_profiler, profile
from faiss_service import get_faiss_index, init_faiss_index
from logging_config import setup_logging
from input_validator import validate_similarity_input
from deduplication_service import get_deduplicator  

# Configuración de logging
logger = setup_logging()

# Variables globales
rate_limiter = RateLimiter()
circuit_breakers = defaultdict(CircuitBreaker)
metrics = PerformanceMetrics()
app_start_time = time.time()


def create_app():
    """Application Factory Pattern"""
    app = Flask(__name__)
    
    # Configuración CORS
    CORS(app, resources={
        r"/api/*": {
            "origins": os.getenv("ALLOWED_ORIGINS", "*").split(","),
            "methods": ["GET", "POST"],
            "allow_headers": ["Content-Type", "Authorization"],
            "max_age": 3600
        }
    })

    redis_url = None
    if os.getenv('REDIS_HOST'):
        redis_url = f"redis://{os.getenv('REDIS_HOST')}:{os.getenv('REDIS_PORT', 6379)}"
    
    
    # Rate Limiting
    limiter = Limiter(
        key_func=get_remote_address,
        app=app,
        default_limits=["200 per day", "50 per hour"],
        storage_uri=redis_url or "memory://",  # Usa memoria si no hay Redis
        storage_options={'socket_connect_timeout': 2}
    )
    
    # Inicializar recursos en contexto de aplicación
    with app.app_context():
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            loop.run_until_complete(init_resources())
            init_faiss_index()
            logger.info("Sistema optimizado iniciado", extra={
                "model": Config.EMBEDDING_MODEL,
                "threshold": Config.SIMILARITY_THRESHOLD
            })
        finally:
            # No cerrar el loop aquí, lo necesitamos para las requests
            pass
    
    # ========== MIDDLEWARE ==========
    
    @app.before_request
    def before_request():
        """Tracking de inicio de request"""
        g.start_time = time.time()
        g.cache_hit = False
    
    @app.after_request
    def after_request(response):
        """Tracking de métricas por request"""
        if hasattr(g, 'start_time'):
            latency = time.time() - g.start_time
            metrics.record_request(latency, response.status_code >= 400)
            
            if hasattr(g, 'cache_hit') and g.cache_hit:
                metrics.record_cache(hit=True)
        
        return response
    
    @app.errorhandler(429)
    def ratelimit_handler(e):
        """Handler para rate limit excedido"""
        logger.warning("Rate limit excedido", extra={
            "ip": request.remote_addr,
            "endpoint": request.endpoint
        })
        return jsonify({
            "error": "Rate limit excedido. Intente nuevamente más tarde.",
            "retry_after": e.description
        }), 429
    
    @app.errorhandler(500)
    def internal_error_handler(e):
        """Handler para errores internos"""
        logger.error("Error interno del servidor", extra={
            "error": str(e),
            "endpoint": request.endpoint
        })
        return jsonify({
            "error": "Error interno del servidor",
            "message": "Por favor contacte al administrador"
        }), 500
    
    # ========== ENDPOINTS PRINCIPALES ==========
    
    @app.route('/api/similarity-search', methods=['POST'])
    @limiter.limit("10 per minute")
    def similarity_search():
        """
        Endpoint principal de búsqueda de similitud
        
        Body JSON:
        {
            "data": [theme, idiom, [[page, paragraph, text], ...]],
            "sources": ["crossref", "pubmed", ...] (opcional),
            "use_faiss": true (opcional, default: true),
            "threshold": 0.70 (opcional, default: 0.70, rango: 0.0-1.0)
        }
        """
        try:
            data = request.get_json()
            
            if not data or 'data' not in data:
                return jsonify({"error": "Datos inválidos. Se requiere campo 'data'"}), 400
            
            # Validación robusta de entrada
            try:
                theme, idiom, texts = validate_similarity_input(data['data'])
            except ValueError as e:
                return jsonify({"error": str(e)}), 400
            
            sources = data.get('sources', None)
            use_faiss = data.get('use_faiss', True)
            
            # ✅ NUEVO: Threshold personalizado
            threshold = data.get('threshold', Config.SIMILARITY_THRESHOLD)
            
            # Validar threshold
            try:
                threshold = float(threshold)
                if not (0.0 <= threshold <= 1.0):
                    return jsonify({"error": "threshold debe estar entre 0.0 y 1.0"}), 400
            except (ValueError, TypeError):
                return jsonify({"error": "threshold debe ser un número"}), 400
            
            # Validar sources si se proporciona
            if sources and not isinstance(sources, list):
                return jsonify({"error": "sources debe ser una lista"}), 400
            
            logger.info("Iniciando búsqueda de similitud", extra={
                "theme": theme,
                "idiom": idiom,
                "num_texts": len(texts),
                "use_faiss": use_faiss,
                "threshold": threshold  # ✅ Log del threshold
            })
            
            # Procesar búsqueda con threshold personalizado
            results = process_similarity_batch(
                texts, 
                theme, 
                idiom,
                get_redis_client(),
                get_http_client(),
                rate_limiter,
                sources,
                use_faiss,
                threshold  # ✅ NUEVO parámetro
            )
            
            # Convertir a JSON
            response_data = [asdict(r) for r in results]
            
            logger.info("Búsqueda completada", extra={
                "num_results": len(response_data),
                "processed_texts": len(texts)
            })
            
            return jsonify({
                "results": response_data,
                "count": len(response_data),
                "processed_texts": len(texts),
                "threshold_used": threshold,  # ✅ Informar threshold usado
                "faiss_enabled": use_faiss and get_faiss_index() is not None
            }), 200
        
        except Exception as e:
            metrics.record_request(0, error=True)
            logger.error("Error en similarity_search", extra={
                "error": str(e),
                "type": type(e).__name__
            })
            return jsonify({
                "error": f"Error en el procesamiento: {str(e)}"
            }), 500
    
    # ========== ENDPOINT ESPECIALIZADO PARA PLAGIO ==========

    @app.route('/api/plagiarism-check', methods=['POST'])
    @limiter.limit("5 per minute")  # Más restrictivo (es intensivo)
    def plagiarism_check():
        """
        Endpoint especializado para detección de plagio
        
        Features:
        - Fragmentación automática de texto
        - Análisis por niveles de plagio
        - Reporte detallado
        
        Body JSON:
        {
            "data": [theme, idiom, [[page, paragraph, text], ...]],
            "threshold": 0.70 (opcional),
            "chunk_mode": "sentences" | "sliding" (opcional, default: sentences),
            "min_chunk_words": 15 (opcional),
            "sources": [...] (opcional)
        }
        """
        try:
            from text_chunker import chunk_text_by_sentences, chunk_text_sliding_window
            
            data = request.get_json()
            
            if not data or 'data' not in data:
                return jsonify({"error": "Datos inválidos. Se requiere campo 'data'"}), 400
            
            # Validar entrada
            try:
                theme, idiom, texts = validate_similarity_input(data['data'])
            except ValueError as e:
                return jsonify({"error": str(e)}), 400
            
            threshold = float(data.get('threshold', 0.70))
            chunk_mode = data.get('chunk_mode', 'sentences')
            min_chunk_words = int(data.get('min_chunk_words', 5))
            sources = data.get('sources', None)
            
            logger.info("Iniciando detección de plagio", extra={
                "theme": theme,
                "num_texts": len(texts),
                "chunk_mode": chunk_mode,
                "threshold": threshold
            })
            
            all_results = []
            chunks_analyzed = 0
            
            # Procesar cada texto
            for page, paragraph, text in texts:
                # Fragmentar texto
                if chunk_mode == 'sentences':
                    sentence_chunks = chunk_text_by_sentences(text, min_words=min_chunk_words)
                    chunks_to_check = [
                        (page, f"{paragraph}_s{idx}", chunk) 
                        for idx, chunk in sentence_chunks
                    ]
                else:  # sliding window
                    window_chunks = chunk_text_sliding_window(text, window_size=50, overlap=10)
                    chunks_to_check = [
                        (page, f"{paragraph}_w{idx}", chunk) 
                        for idx, chunk in enumerate(window_chunks)
                    ]
                
                chunks_analyzed += len(chunks_to_check)
                
                # Analizar cada fragmento
                if chunks_to_check:
                    results = process_similarity_batch(
                        chunks_to_check,
                        theme,
                        idiom,
                        get_redis_client(),
                        get_http_client(),
                        rate_limiter,
                        sources=sources,
                        use_faiss=True,
                        threshold=threshold
                    )
                    all_results.extend(results)
            
            # Agrupar por nivel de plagio
            by_level = {
                'very_high': [],
                'high': [],
                'moderate': [],
                'low': [],
                'minimal': []
            }
            
            for result in all_results:
                level = result.plagiarism_level
                by_level[level].append(asdict(result))
            
            # Generar resumen
            plagiarism_detected = (
                len(by_level['very_high']) > 0 or 
                len(by_level['high']) > 0
            )
            
            logger.info("Detección de plagio completada", extra={
                "chunks_analyzed": chunks_analyzed,
                "matches_found": len(all_results),
                "plagiarism_detected": plagiarism_detected
            })
            
            return jsonify({
                "plagiarism_detected": plagiarism_detected,
                "chunks_analyzed": chunks_analyzed,
                "total_matches": len(all_results),
                "summary": {
                    "very_high": len(by_level['very_high']),
                    "high": len(by_level['high']),
                    "moderate": len(by_level['moderate']),
                    "low": len(by_level['low']),
                    "minimal": len(by_level['minimal'])
                },
                "by_level": {
                    level: {
                        "count": len(results),
                        "results": results[:10]  # Limitar a 10 por nivel
                    }
                    for level, results in by_level.items()
                    if len(results) > 0  # Solo incluir niveles con resultados
                },
                "threshold_used": threshold,
                "faiss_enabled": get_faiss_index() is not None
            }), 200
        
        except Exception as e:
            logger.error("Error en plagiarism_check", extra={
                "error": str(e),
                "type": type(e).__name__
            })
            return jsonify({
                "error": f"Error en la detección de plagio: {str(e)}"
            }), 500

    @app.route('/api/health', methods=['GET'])
    def health_check():
        """Endpoint de verificación de salud con métricas"""
        circuit_status = {
            source: breaker.state.value 
            for source, breaker in circuit_breakers.items()
        }
        
        stats = metrics.get_stats()
        stats['uptime_seconds'] = round(time.time() - app_start_time, 2)
        
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
    
    @app.route('/api/metrics', methods=['GET'])
    def get_metrics():
        """Endpoint dedicado a métricas (Prometheus-compatible)"""
        stats = metrics.get_stats()
        uptime = time.time() - app_start_time
        
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
    
    @app.route('/api/reset-limits', methods=['POST'])
    def reset_limits():
        """Reinicia los contadores de límites de API"""
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            loop.run_until_complete(rate_limiter.reset())
        finally:
            loop.close()
        
        # Reiniciar circuit breakers
        from models import CircuitState
        for breaker in circuit_breakers.values():
            breaker.failure_count = 0
            breaker.state = CircuitState.CLOSED
        
        logger.info("Límites y circuit breakers reiniciados")
        
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
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                loop.run_until_complete(redis_client.flushdb())
                logger.info("Caché limpiado exitosamente")
                return jsonify({"message": "Caché limpiado"}), 200
            finally:
                loop.close()
        except Exception as e:
            logger.error("Error limpiando caché", extra={"error": str(e)})
            return jsonify({"error": str(e)}), 500
    
    @app.route('/api/benchmark', methods=['POST'])
    @limiter.limit("5 per hour")  # ✅ Agregar rate limit estricto
    @profile
    def benchmark():
        """Endpoint para benchmarking - solo FAISS, sin APIs"""
        try:
            data = request.get_json() or {}
            num_texts = min(data.get('num_texts', 10), 50)  # Reducir máximo a 50
            
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
    
    # ========== ENDPOINTS FAISS ==========
    
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
        logger.warning("Índice FAISS limpiado")
        return jsonify({"message": "Índice FAISS limpiado"}), 200
    
    @app.route('/api/faiss/save', methods=['POST'])
    def faiss_save():
        """Guarda el índice FAISS en disco"""
        faiss_index = get_faiss_index()
        
        if not faiss_index:
            return jsonify({"error": "FAISS no disponible"}), 503
        
        try:
            faiss_index.save()
            logger.info("Índice FAISS guardado")
            return jsonify({
                "message": "Índice guardado exitosamente",
                "stats": faiss_index.get_stats()
            }), 200
        except Exception as e:
            logger.error("Error guardando FAISS", extra={"error": str(e)})
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
            k = min(data.get('k', 10), 100)  # Máximo 100
            threshold = max(0.0, min(data.get('threshold', 0.7), 1.0))  # Entre 0 y 1
            
            if not query:
                return jsonify({"error": "Query requerido"}), 400
            
            results = faiss_index.search(query, k=k, threshold=threshold)
            
            return jsonify({
                "query": query,
                "results": results,
                "count": len(results)
            }), 200
        
        except Exception as e:
            logger.error("Error en búsqueda FAISS", extra={"error": str(e)})
            return jsonify({"error": str(e)}), 500
    
    @app.route('/api/faiss/backup', methods=['POST'])
    def faiss_backup():
        """Backup del índice FAISS"""
        import shutil
        from datetime import datetime
        
        faiss_index = get_faiss_index()
        if not faiss_index:
            return jsonify({"error": "FAISS no disponible"}), 503
        
        try:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            backup_dir = f"backups/faiss_{timestamp}"
            
            os.makedirs(backup_dir, exist_ok=True)
            
            # Guardar primero
            faiss_index.save()
            
            # Copiar archivos
            shutil.copy("data/faiss_index.index", backup_dir)
            shutil.copy("data/faiss_index_metadata.pkl", backup_dir)
            
            logger.info("Backup FAISS creado", extra={"backup_dir": backup_dir})
            
            return jsonify({
                "message": f"Backup creado exitosamente",
                "backup_path": backup_dir,
                "papers": faiss_index.index.ntotal
            }), 200
        
        except Exception as e:
            logger.error("Error creando backup", extra={"error": str(e)})
            return jsonify({"error": str(e)}), 500
    
    # ✅ NUEVO ENDPOINT (agregar después de faiss_backup)
    @app.route('/api/deduplication/stats', methods=['GET'])
    def deduplication_stats():
        """Estadísticas del sistema de deduplicación"""
        try:
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
    # ========== ENDPOINTS DE VALIDACIÓN DE APIS ==========
    
    @app.route('/api/validate-apis', methods=['POST'])
    def validate_external_apis():
        """Valida todas las APIs externas"""
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
    
    @app.route('/api/api-health', methods=['GET'])
    def get_api_health():
        """Retorna estado de salud de APIs (último check)"""
        validator = get_api_validator()
        report = validator.get_health_report()
        
        return jsonify(report), 200
    
    @app.route('/api/failing-apis', methods=['GET'])
    def get_failing_apis():
        """Lista APIs que están fallando"""
        validator = get_api_validator()
        failing = validator.get_failing_apis()
        
        return jsonify({
            "failing_apis": failing,
            "count": len(failing)
        }), 200
    
    # ========== ENDPOINTS DE PROFILING ==========
    
    @app.route('/api/profiler/stats', methods=['GET'])
    def get_profiler_stats():
        """Estadísticas de performance del sistema"""
        profiler = get_profiler()
        report = profiler.generate_report()
        
        return jsonify(report), 200
    
    @app.route('/api/profiler/bottlenecks', methods=['GET'])
    def get_bottlenecks():
        """Identifica cuellos de botella"""
        top_n = min(request.args.get('top', 5, type=int), 20)
        profiler = get_profiler()
        bottlenecks = profiler.get_bottlenecks(top_n)
        
        return jsonify({
            "bottlenecks": bottlenecks,
            "count": len(bottlenecks)
        }), 200
    
    @app.route('/api/profiler/clear', methods=['POST'])
    def clear_profiler_snapshots():
        """Limpia snapshots del profiler"""
        profiler = get_profiler()
        profiler.clear_snapshots()
        
        logger.info("Snapshots del profiler limpiados")
        return jsonify({"message": "Snapshots limpiados"}), 200
    
    # ========== DIAGNÓSTICO ==========
    
    @app.route('/api/diagnostics/full', methods=['GET'])
    def full_diagnostics():
        """Diagnóstico completo del sistema"""
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
            for source, breaker in circuit_breakers.items()
        }
        
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
    
    return app


# Cleanup al cerrar
def shutdown():
    """Limpia recursos al cerrar"""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        loop.run_until_complete(cleanup_resources())
        
        # Cerrar deduplicator
        from deduplication_service import _deduplicator
        if _deduplicator:
            loop.run_until_complete(_deduplicator.close())
        
        logger.info("Recursos liberados")
    finally:
        loop.close()


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
    print("   POST /api/faiss/backup       - Backup FAISS")
    print("   POST /api/validate-apis      - Validar APIs externas")
    print("   GET  /api/diagnostics/full   - Diagnóstico completo")
    print("=" * 60)
    
    app = create_app()
    
    # Usar gunicorn en producción
    app.run(
        host='0.0.0.0', 
        port=8000, 
        debug=True, 
        threaded=True
    )