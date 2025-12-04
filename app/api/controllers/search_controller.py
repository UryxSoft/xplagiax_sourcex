"""
Search Controller - Handle similarity search and plagiarism check
"""
import logging
from dataclasses import asdict
from flask import request, jsonify, g
from marshmallow import ValidationError

from app.api.schemas.search_schema import SimilaritySearchSchema, PlagiarismCheckSchema
from app.core.errors import ValidationError as APIValidationError
from app.services.similarity_service import SimilarityService
from app.utils.asyncio_compat import run_async
from app.utils.cache import CacheManager
import time

logger = logging.getLogger(__name__)


class SearchController:
    """Controller for search operations"""
    
    def __init__(self):
        self.similarity_service = SimilarityService()
        self.search_schema = SimilaritySearchSchema()
        self.plagiarism_schema = PlagiarismCheckSchema()
        self.cache_manager = CacheManager()
    
    def similarity_search(self):
        """
        Handle POST /api/similarity-search (OPTIMIZADO)
        """
        start_time = time.perf_counter()  # ✅ Más preciso que time.time()
        
        try:
            # 1. Validate request data
            data = request.get_json()
            
            if not data:
                raise APIValidationError("Request body is required")
            
            # Parse and validate
            try:
                # Convert legacy format
                legacy_data = data.get('data', [])
                if len(legacy_data) >= 3:
                    validated_data = {
                        'theme': legacy_data[0],
                        'idiom': legacy_data[1],
                        'texts': legacy_data[2],
                        'threshold': data.get('threshold', 0.70),
                        'use_faiss': data.get('use_faiss', True),
                        'sources': data.get('sources')
                    }
                else:
                    validated_data = data
                
                validated = self.search_schema.load(validated_data)
            
            except ValidationError as e:
                raise APIValidationError(str(e.messages))
            
            # ✅ 2. Check cache ANTES de procesar
            cache_key = self.cache_manager.generate_key(
                theme=validated['theme'],
                text=str(validated['texts']),  # Simple hash de todos los textos
                threshold=validated['threshold'],
                sources=validated['sources'] or []
            )
            
            # Intentar obtener del cache
            cached_results = run_async(
                self.cache_manager.get_from_cache(cache_key)
            )
            
            if cached_results:
                logger.info("Cache HIT - returning cached results")
                return jsonify({
                    "results": cached_results,
                    "count": len(cached_results),
                    "processed_texts": len(validated['texts']),
                    "threshold_used": validated['threshold'],
                    "faiss_enabled": validated['use_faiss'],
                    "cached": True,  # ✅ Indicar que es cached
                    "response_time_ms": round((time.perf_counter() - start_time) * 1000, 2)
                }), 200
            
            # 3. Execute search service
            logger.info(
                "Cache MISS - processing search",
                extra={
                    "theme": validated['theme'],
                    "idiom": validated['idiom'],
                    "num_texts": len(validated['texts']),
                    "threshold": validated['threshold']
                }
            )
            
            results = run_async(
                self.similarity_service.search_similarity(
                    theme=validated['theme'],
                    idiom=validated['idiom'],
                    texts=validated['texts'],
                    threshold=validated['threshold'],
                    use_faiss=validated['use_faiss'],
                    sources=validated['sources']
                )
            )
            
            # 4. Convert to dict format
            response_data = [asdict(r) for r in results]
            
            # ✅ 5. Save to cache (async, no esperar)
            if response_data:
                run_async(
                    self.cache_manager.save_to_cache(cache_key, response_data)
                )
            
            elapsed_ms = round((time.perf_counter() - start_time) * 1000, 2)
            
            logger.info(
                "Search completed",
                extra={
                    "num_results": len(response_data),
                    "threshold": validated['threshold'],
                    "elapsed_ms": elapsed_ms
                }
            )
            
            return jsonify({
                "results": response_data,
                "count": len(response_data),
                "processed_texts": len(validated['texts']),
                "threshold_used": validated['threshold'],
                "faiss_enabled": validated['use_faiss'],
                "cached": False,
                "response_time_ms": elapsed_ms
            }), 200
        
        except APIValidationError as e:
            return jsonify({
                "error": "Validation error",
                "message": e.message
            }), 400
        
        except Exception as e:
            logger.error(
                "Error in similarity search",
                extra={"error": str(e)},
                exc_info=True
            )
            
            return jsonify({
                "error": "Search failed",
                "message": "An error occurred during search"
            }), 500
    
    def plagiarism_check(self):
        """
        Handle POST /api/plagiarism-check
        
        Returns:
            JSON response with plagiarism analysis
        """
        try:
            # 1. Validate request data
            data = request.get_json()
            
            if not data:
                raise APIValidationError("Request body is required")
            
            try:
                # Convert legacy format
                legacy_data = data.get('data', [])
                if len(legacy_data) >= 3:
                    validated_data = {
                        'theme': legacy_data[0],
                        'idiom': legacy_data[1],
                        'texts': legacy_data[2],
                        'threshold': data.get('threshold', 0.70),
                        'use_faiss': data.get('use_faiss', True),
                        'sources': data.get('sources'),
                        'chunk_mode': data.get('chunk_mode', 'sentences'),
                        'min_chunk_words': data.get('min_chunk_words', 15)
                    }
                else:
                    validated_data = data
                
                validated = self.plagiarism_schema.load(validated_data)
            
            except ValidationError as e:
                raise APIValidationError(str(e.messages))
            
            # 2. Execute plagiarism check
            logger.info(
                "Plagiarism check started",
                extra={
                    "theme": validated['theme'],
                    "num_texts": len(validated['texts']),
                    "chunk_mode": validated['chunk_mode']
                }
            )
            
            analysis = run_async(
                self.similarity_service.check_plagiarism(
                    theme=validated['theme'],
                    idiom=validated['idiom'],
                    texts=validated['texts'],
                    threshold=validated['threshold'],
                    chunk_mode=validated['chunk_mode'],
                    min_chunk_words=validated['min_chunk_words'],
                    sources=validated['sources']
                )
            )
            
            logger.info(
                "Plagiarism check completed",
                extra={
                    "chunks_analyzed": analysis['chunks_analyzed'],
                    "matches": analysis['total_matches'],
                    "plagiarism_detected": analysis['plagiarism_detected']
                }
            )
            
            return jsonify(analysis), 200
        
        except APIValidationError as e:
            return jsonify({
                "error": "Validation error",
                "message": e.message
            }), 400
        
        except Exception as e:
            logger.error(
                "Error in plagiarism check",
                extra={"error": str(e)},
                exc_info=True
            )
            
            return jsonify({
                "error": "Plagiarism check failed",
                "message": "An error occurred during analysis"
            }), 500


# Singleton instance
search_controller = SearchController()