"""
Admin Controller - Handle administrative operations
"""
import logging
import time
from flask import request, jsonify

from app.core.extensions import get_redis_client, get_faiss_index
from app.core.config import Config
from app.utils.profiling import profile

logger = logging.getLogger(__name__)


class AdminController:
    """Controller for admin operations"""
    
    def reset_limits(self):
        """
        Handle POST /api/reset-limits
        
        Returns:
            JSON response confirming reset
        """
        from app.utils.rate_limiter import RateLimiter
        from app.models.circuit_breaker import reset_all_circuit_breakers
        
        try:
            # Reset rate limiter
            rate_limiter = RateLimiter()
            
            import asyncio
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                loop.run_until_complete(rate_limiter.reset())
            finally:
                loop.close()
            
            # Reset circuit breakers
            reset_all_circuit_breakers()
            
            logger.info(
                "Limits reset by admin",
                extra={"ip": request.remote_addr}
            )
            
            return jsonify({
                "message": "Limits and circuit breakers reset successfully"
            }), 200
        
        except Exception as e:
            logger.error(f"Error resetting limits: {e}")
            return jsonify({
                "error": "Failed to reset limits"
            }), 500
    
    def clear_cache(self):
        """
        Handle POST /api/cache/clear (DESTRUCTIVE)
        
        Returns:
            JSON response confirming cache clear
        """
        try:
            redis_client = get_redis_client()
            
            if not redis_client:
                return jsonify({
                    "error": "Redis not available"
                }), 503
            
            import asyncio
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                loop.run_until_complete(redis_client.flushdb())
            finally:
                loop.close()
            
            logger.warning(
                "Cache cleared by admin",
                extra={"ip": request.remote_addr}
            )
            
            return jsonify({
                "message": "Cache cleared successfully"
            }), 200
        
        except Exception as e:
            logger.error(f"Error clearing cache: {e}")
            return jsonify({
                "error": "Failed to clear cache"
            }), 500
    
    @profile
    def benchmark(self):
        """
        Handle POST /api/benchmark
        
        Returns:
            JSON response with benchmark results
        """
        try:
            data = request.get_json() or {}
            num_texts = min(data.get('num_texts', 10), 50)
            
            faiss_index = get_faiss_index()
            
            if not faiss_index or faiss_index.index.ntotal == 0:
                return jsonify({
                    "error": "FAISS empty. Run searches first to populate index."
                }), 400
            
            # Test queries
            test_queries = [
                "machine learning algorithms",
                "neural network architectures",
                "deep learning optimization",
                "natural language processing",
                "computer vision techniques",
            ] * ((num_texts // 5) + 1)
            
            queries = test_queries[:num_texts]
            
            # Benchmark
            start = time.time()
            results = faiss_index.search_batch(
                queries,
                k=10,
                threshold=0.7
            )
            elapsed = time.time() - start
            
            total_results = sum(len(r) for r in results)
            
            logger.info(
                "Benchmark completed",
                extra={
                    "num_queries": num_texts,
                    "elapsed": elapsed,
                    "ip": request.remote_addr
                }
            )
            
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
            logger.error(f"Error in benchmark: {e}")
            return jsonify({
                "error": "Benchmark failed"
            }), 500
    
    def deduplication_stats(self):
        """
        Handle GET /api/deduplication/stats
        
        Returns:
            JSON response with deduplication statistics
        """
        try:
            import asyncio
            from app.services.deduplication_service import get_deduplicator
            
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                deduplicator = loop.run_until_complete(get_deduplicator())
                stats = loop.run_until_complete(deduplicator.get_stats())
                
                return jsonify(stats), 200
            finally:
                loop.close()
        
        except Exception as e:
            logger.error(f"Error getting deduplication stats: {e}")
            return jsonify({
                "error": "Failed to get deduplication stats"
            }), 500


# Singleton instance
admin_controller = AdminController()