"""
Blueprint de Búsqueda - Endpoints principales de similitud y plagio
"""
import logging
from dataclasses import asdict
from flask import Blueprint, request, jsonify
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

from config import Config
from input_validator import validate_similarity_input
from services.search_service import process_similarity_batch
from resources import get_redis_client, get_http_client
from rate_limiter import RateLimiter

logger = logging.getLogger(__name__)

# Crear blueprint
search_bp = Blueprint('search', __name__, url_prefix='/api')

# Rate limiter (se configurará desde app.py)
limiter = None
rate_limiter_service = RateLimiter()


def init_search_blueprint(app_limiter):
    """Inicializa el limiter del blueprint"""
    global limiter
    limiter = app_limiter


@search_bp.route('/similarity-search', methods=['POST'])
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
            "threshold": threshold
        })
        
        # Procesar búsqueda
        results = process_similarity_batch(
            texts, 
            theme, 
            idiom,
            get_redis_client(),
            get_http_client(),
            rate_limiter_service,
            sources,
            use_faiss,
            threshold
        )
        
        # Convertir a JSON
        response_data = [asdict(r) for r in results]
        
        logger.info("Búsqueda completada", extra={
            "num_results": len(response_data),
            "processed_texts": len(texts)
        })
        
        from faiss_service import get_faiss_index
        
        return jsonify({
            "results": response_data,
            "count": len(response_data),
            "processed_texts": len(texts),
            "threshold_used": threshold,
            "faiss_enabled": use_faiss and get_faiss_index() is not None
        }), 200
    
    except Exception as e:
        logger.error("Error en similarity_search", extra={
            "error": str(e),
            "type": type(e).__name__
        })
        return jsonify({
            "error": f"Error en el procesamiento: {str(e)}"
        }), 500


@search_bp.route('/plagiarism-check', methods=['POST'])
@limiter.limit("5 per minute")
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
                    rate_limiter_service,
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
                if len(results) > 0
            },
            "threshold_used": threshold,
            "faiss_enabled": True
        }), 200
    
    except Exception as e:
        logger.error("Error en plagiarism_check", extra={
            "error": str(e),
            "type": type(e).__name__
        })
        return jsonify({
            "error": f"Error en la detección de plagio: {str(e)}"
        }), 500