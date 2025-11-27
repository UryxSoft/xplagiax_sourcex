"""
FAISS Controller - Handle FAISS operations
"""
import logging
from flask import request, jsonify
from marshmallow import ValidationError

from app.api.schemas.faiss_schema import FAISSSearchSchema
from app.core.errors import ValidationError as APIValidationError, ServiceUnavailableError
from app.core.extensions import get_faiss_index

logger = logging.getLogger(__name__)


class FAISSController:
    """Controller for FAISS operations"""
    
    def __init__(self):
        self.search_schema = FAISSSearchSchema()
    
    def get_stats(self):
        """
        Handle GET /api/faiss/stats
        
        Returns:
            JSON response with FAISS statistics
        """
        try:
            faiss_index = get_faiss_index()
            
            if not faiss_index:
                raise ServiceUnavailableError("FAISS not available")
            
            stats = faiss_index.get_stats()
            
            return jsonify(stats), 200
        
        except ServiceUnavailableError as e:
            return jsonify({
                "error": e.message
            }), 503
        
        except Exception as e:
            logger.error(f"Error getting FAISS stats: {e}")
            return jsonify({
                "error": "Failed to get stats"
            }), 500
    
    def search(self):
        """
        Handle POST /api/faiss/search
        
        Returns:
            JSON response with search results
        """
        try:
            # Validate input
            data = request.get_json()
            
            try:
                validated = self.search_schema.load(data)
            except ValidationError as e:
                raise APIValidationError(str(e.messages))
            
            # Get FAISS index
            faiss_index = get_faiss_index()
            
            if not faiss_index:
                raise ServiceUnavailableError("FAISS not available")
            
            # Execute search
            results = faiss_index.search(
                query=validated['query'],
                k=validated['k'],
                threshold=validated['threshold']
            )
            
            return jsonify({
                "query": validated['query'],
                "results": results,
                "count": len(results)
            }), 200
        
        except APIValidationError as e:
            return jsonify({
                "error": "Validation error",
                "message": e.message
            }), 400
        
        except ServiceUnavailableError as e:
            return jsonify({
                "error": e.message
            }), 503
        
        except Exception as e:
            logger.error(f"Error in FAISS search: {e}")
            return jsonify({
                "error": "Search failed"
            }), 500
    
    def save(self):
        """
        Handle POST /api/faiss/save
        
        Returns:
            JSON response confirming save
        """
        try:
            faiss_index = get_faiss_index()
            
            if not faiss_index:
                raise ServiceUnavailableError("FAISS not available")
            
            faiss_index.save()
            
            logger.info("FAISS index saved by admin")
            
            return jsonify({
                "message": "Index saved successfully",
                "stats": faiss_index.get_stats()
            }), 200
        
        except ServiceUnavailableError as e:
            return jsonify({
                "error": e.message
            }), 503
        
        except Exception as e:
            logger.error(f"Error saving FAISS: {e}")
            return jsonify({
                "error": "Failed to save index"
            }), 500
    
    def clear(self):
        """
        Handle POST /api/faiss/clear (DESTRUCTIVE)
        
        Returns:
            JSON response confirming clear
        """
        try:
            faiss_index = get_faiss_index()
            
            if not faiss_index:
                raise ServiceUnavailableError("FAISS not available")
            
            faiss_index.clear()
            
            logger.warning(
                "FAISS index cleared by admin",
                extra={"ip": request.remote_addr}
            )
            
            return jsonify({
                "message": "Index cleared successfully"
            }), 200
        
        except ServiceUnavailableError as e:
            return jsonify({
                "error": e.message
            }), 503
        
        except Exception as e:
            logger.error(f"Error clearing FAISS: {e}")
            return jsonify({
                "error": "Failed to clear index"
            }), 500
    
    def backup(self):
        """
        Handle POST /api/faiss/backup
        
        Returns:
            JSON response with backup info
        """
        import os
        import shutil
        from datetime import datetime
        
        try:
            faiss_index = get_faiss_index()
            
            if not faiss_index:
                raise ServiceUnavailableError("FAISS not available")
            
            # Create backup directory
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            backup_dir = f"backups/faiss_{timestamp}"
            
            os.makedirs(backup_dir, exist_ok=True)
            
            # Save current index
            faiss_index.save()
            
            # Copy files
            shutil.copy("data/faiss_index.index", backup_dir)
            shutil.copy("data/faiss_index_metadata.pkl", backup_dir)
            
            logger.info(
                "FAISS backup created",
                extra={"backup_dir": backup_dir, "ip": request.remote_addr}
            )
            
            return jsonify({
                "message": "Backup created successfully",
                "backup_path": backup_dir,
                "papers": faiss_index.index.ntotal
            }), 200
        
        except ServiceUnavailableError as e:
            return jsonify({
                "error": e.message
            }), 503
        
        except Exception as e:
            logger.error(f"Error creating backup: {e}")
            return jsonify({
                "error": "Backup failed"
            }), 500
    
    def remove_duplicates(self):
        """
        Handle POST /api/faiss/remove-duplicates
        
        Returns:
            JSON response with duplicates removed count
        """
        try:
            faiss_index = get_faiss_index()
            
            if not faiss_index:
                raise ServiceUnavailableError("FAISS not available")
            
            logger.info("Starting duplicate removal")
            
            duplicates_removed = faiss_index.remove_duplicates()
            
            logger.info(f"Removed {duplicates_removed} duplicates")
            
            return jsonify({
                "message": "Duplicates removed",
                "duplicates_removed": duplicates_removed,
                "stats": faiss_index.get_stats()
            }), 200
        
        except ServiceUnavailableError as e:
            return jsonify({
                "error": e.message
            }), 503
        
        except Exception as e:
            logger.error(f"Error removing duplicates: {e}")
            return jsonify({
                "error": "Failed to remove duplicates"
            }), 500


# Singleton instance
faiss_controller = FAISSController()