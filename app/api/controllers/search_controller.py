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

logger = logging.getLogger(__name__)


class SearchController:
    """Controller for search operations"""
    
    def __init__(self):
        self.similarity_service = SimilarityService()
        self.search_schema = SimilaritySearchSchema()
        self.plagiarism_schema = PlagiarismCheckSchema()
    
    def similarity_search(self):
        """
        Handle POST /api/similarity-search
        
        Returns:
            JSON response with search results
        """
        try:
            # 1. Validate request data
            data = request.get_json()
            
            if not data:
                raise APIValidationError("Request body is required")
            
            # Parse and validate using Marshmallow
            try:
                # Convert legacy format to schema format
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
            
            # 2. Execute search service
            logger.info(
                "Similarity search started",
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
            
            # 3. Format response
            response_data = {
                "results": [asdict(r) for r in results],
                "count": len(results),
                "processed_texts": len(validated['texts']),
                "threshold_used": validated['threshold'],
                "faiss_enabled": validated['use_faiss']
            }
            
            logger.info(
                "Similarity search completed",
                extra={
                    "num_results": len(results),
                    "threshold": validated['threshold']
                }
            )
            
            return jsonify(response_data), 200
        
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