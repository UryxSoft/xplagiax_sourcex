"""
Blueprint de FAISS - Gestión del índice vectorial
"""
import os
import logging
from datetime import datetime
from flask import Blueprint, request, jsonify

from auth import require_api_key
from faiss_service import get_faiss_index
from config import Config

logger = logging.getLogger(__name__)

# Crear blueprint
faiss_bp = Blueprint('faiss', __name__, url_prefix='/api/faiss')


@faiss_bp.route('/stats', methods=['GET'])
def stats():
    """Estadísticas del índice FAISS"""
    faiss_index = get_faiss_index()
    
    if not faiss_index:
        return jsonify({"error": "FAISS no disponible"}), 503
    
    return jsonify(faiss_index.get_stats()), 200


@faiss_bp.route('/search', methods=['POST'])
def search():
    """
    Búsqueda directa en FAISS
    
    Body:
    {
        "query": "machine learning",
        "k": 20,  // opcional
        "threshold": 0.7  // opcional
    }
    """
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


@faiss_bp.route('/save', methods=['POST'])
@require_api_key
def save():
    """Guarda el índice FAISS en disco (requiere autenticación)"""
    faiss_index = get_faiss_index()
    
    if not faiss_index:
        return jsonify({"error": "FAISS no disponible"}), 503
    
    try:
        faiss_index.save()
        logger.info("Índice FAISS guardado por admin")
        return jsonify({
            "message": "Índice guardado exitosamente",
            "stats": faiss_index.get_stats()
        }), 200
    except Exception as e:
        logger.error("Error guardando FAISS", extra={"error": str(e)})
        return jsonify({"error": str(e)}), 500


@faiss_bp.route('/clear', methods=['POST'])
@require_api_key
def clear():
    """Limpia el índice FAISS (requiere autenticación - DESTRUCTIVO)"""
    faiss_index = get_faiss_index()
    
    if not faiss_index:
        return jsonify({"error": "FAISS no disponible"}), 503
    
    faiss_index.clear()
    logger.warning("Índice FAISS limpiado por admin", extra={
        "ip": request.remote_addr
    })
    return jsonify({"message": "Índice FAISS limpiado"}), 200


@faiss_bp.route('/backup', methods=['POST'])
@require_api_key
def backup():
    """Backup del índice FAISS (requiere autenticación)"""
    import shutil
    
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
        
        logger.info("Backup FAISS creado", extra={
            "backup_dir": backup_dir,
            "admin_ip": request.remote_addr
        })
        
        return jsonify({
            "message": f"Backup creado exitosamente",
            "backup_path": backup_dir,
            "papers": faiss_index.index.ntotal
        }), 200
    
    except Exception as e:
        logger.error("Error creando backup", extra={"error": str(e)})
        return jsonify({"error": str(e)}), 500


@faiss_bp.route('/remove-duplicates', methods=['POST'])
@require_api_key
def remove_duplicates():
    """
    Elimina duplicados del índice FAISS (OPERACIÓN LENTA)
    Requiere autenticación
    """
    faiss_index = get_faiss_index()
    
    if not faiss_index:
        return jsonify({"error": "FAISS no disponible"}), 503
    
    try:
        logger.info("Iniciando limpieza de duplicados", extra={
            "admin_ip": request.remote_addr
        })
        
        duplicates_removed = faiss_index.remove_duplicates()
        
        logger.info("Limpieza de duplicados completada", extra={
            "duplicates_removed": duplicates_removed
        })
        
        return jsonify({
            "message": "Duplicados eliminados",
            "duplicates_removed": duplicates_removed,
            "stats": faiss_index.get_stats()
        }), 200
    
    except Exception as e:
        logger.error("Error eliminando duplicados", extra={"error": str(e)})
        return jsonify({"error": str(e)}), 500