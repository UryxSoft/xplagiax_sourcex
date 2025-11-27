"""
Diagnostics Controller - Handle health checks and monitoring
"""
import time
import logging
from flask import request, jsonify

from app.core.extensions import get_redis_client, get_http_client, get_faiss_index
from app.core.middleware import get_metrics
from app.utils.api_validator import get_api_validator
from app.utils.profiling import get_profiler

logger = logging.getLogger(__name__)


class DiagnosticsController:
    """Controller for diagnostics and monitoring"""
    
    def __init__(self):
        self.app_start_time = time.time()
    
    def health(self):
        """
        Handle GET /api/health
        
        Returns:
            JSON response with health status
        """
        try:
            # Get component status
            redis_client = get_redis_client()
            http_client = get_http_client()
            faiss_index = get_faiss_index()
            
            redis_status = "connected" if redis_client else "disconnected"
            http_status = "active" if http_client else "inactive"
            
            # FAISS stats
            faiss_stats = None
            if faiss_index:
                faiss_stats = faiss_index.get_stats()
            
            # Metrics
            metrics = get_metrics()
            stats = metrics.get_stats()
            stats['uptime_seconds'] = round(time.time() - self.app_start_time, 2)
            
            # Determine overall health
            overall_healthy = (
                redis_status == "connected" and
                http_status == "active" and
                (not faiss_stats or not faiss_stats.get('corrupted', False))
            )
            
            return jsonify({
                "status": "healthy" if overall_healthy else "degraded",
                "version": "2.1.0",
                "redis": redis_status,
                "http_pool": http_status,
                "faiss": faiss_stats,
                "metrics": stats
            }), 200 if overall_healthy else 503
        
        except Exception as e:
            logger.error(f"Error in health check: {e}")
            return jsonify({
                "status": "unhealthy",
                "error": str(e)
            }), 503
    
    def metrics(self):
        """
        Handle GET /api/metrics (Prometheus format)
        
        Returns:
            Plain text metrics in Prometheus format
        """
        try:
            metrics = get_metrics()
            stats = metrics.get_stats()
            uptime = time.time() - self.app_start_time
            
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
uptime_seconds {uptime:.2f}

# HELP faiss_indexed_papers Total papers in FAISS index
# TYPE faiss_indexed_papers gauge
faiss_indexed_papers {faiss_papers}
"""
            
            return prometheus_format, 200, {'Content-Type': 'text/plain; charset=utf-8'}
        
        except Exception as e:
            logger.error(f"Error generating metrics: {e}")
            return "# Error generating metrics\n", 500
    
    def full_diagnostics(self):
        """
        Handle GET /api/diagnostics/full
        
        Returns:
            JSON response with complete diagnostics
        """
        import asyncio
        
        try:
            # Validate external APIs
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
            
            # FAISS
            faiss_index = get_faiss_index()
            faiss_stats = faiss_index.get_stats() if faiss_index else None
            
            # Components
            redis_ok = get_redis_client() is not None
            http_ok = get_http_client() is not None
            
            # Overall health
            overall_healthy = (
                api_report['summary']['overall_health'] == "healthy" and
                perf_report['system']['cpu']['percent'] < 80 and
                redis_ok and http_ok
            )
            
            recommendations = perf_report['recommendations'].copy()
            
            failing = validator.get_failing_apis()
            if failing:
                recommendations.append(
                    f"⚠️ {len(failing)} APIs with issues: {', '.join(failing)}"
                )
            else:
                recommendations.append("✅ All APIs operational")
            
            return jsonify({
                "timestamp": time.time(),
                "overall_health": "healthy" if overall_healthy else "degraded",
                "components": {
                    "faiss": faiss_stats,
                    "redis": {"status": "connected" if redis_ok else "disconnected"},
                    "http_pool": {"status": "active" if http_ok else "inactive"},
                    "apis": api_report,
                    "performance": perf_report
                },
                "recommendations": recommendations
            }), 200
        
        except Exception as e:
            logger.error(f"Error in full diagnostics: {e}")
            return jsonify({
                "error": "Diagnostics failed",
                "message": str(e)
            }), 500
    
    def validate_apis(self):
        """
        Handle POST /api/validate-apis
        
        Returns:
            JSON response with API validation results
        """
        import asyncio
        
        try:
            data = request.get_json() or {}
            sources = data.get('sources', None)
            
            validator = get_api_validator()
            http_client = get_http_client()
            
            if not http_client:
                return jsonify({
                    "error": "HTTP client not available"
                }), 503
            
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
            logger.error(f"Error validating APIs: {e}")
            return jsonify({
                "error": "API validation failed"
            }), 500


# Singleton instance
diagnostics_controller = DiagnosticsController()