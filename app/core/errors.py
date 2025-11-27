"""
Error handlers and custom exceptions
"""
import logging
from flask import Flask, jsonify, request
from werkzeug.exceptions import HTTPException

logger = logging.getLogger(__name__)


# ==================== CUSTOM EXCEPTIONS ====================

class APIError(Exception):
    """Base API exception"""
    status_code = 500
    
    def __init__(self, message: str, status_code: int = None, payload: dict = None):
        super().__init__()
        self.message = message
        if status_code is not None:
            self.status_code = status_code
        self.payload = payload
    
    def to_dict(self):
        rv = dict(self.payload or ())
        rv['error'] = self.message
        rv['status_code'] = self.status_code
        return rv


class ValidationError(APIError):
    """Input validation error"""
    status_code = 400


class AuthenticationError(APIError):
    """Authentication error"""
    status_code = 401


class AuthorizationError(APIError):
    """Authorization error"""
    status_code = 403


class NotFoundError(APIError):
    """Resource not found"""
    status_code = 404


class RateLimitError(APIError):
    """Rate limit exceeded"""
    status_code = 429


class ServiceUnavailableError(APIError):
    """External service unavailable"""
    status_code = 503


# ==================== ERROR HANDLERS ====================

def register_error_handlers(app: Flask):
    """
    Register all error handlers
    
    Args:
        app: Flask app instance
    """
    
    @app.errorhandler(APIError)
    def handle_api_error(error: APIError):
        """Handle custom API errors"""
        logger.warning(
            f"API Error: {error.message}",
            extra={
                "status_code": error.status_code,
                "endpoint": request.endpoint,
                "ip": request.remote_addr
            }
        )
        
        response = jsonify(error.to_dict())
        response.status_code = error.status_code
        return response
    
    @app.errorhandler(ValidationError)
    def handle_validation_error(error: ValidationError):
        """Handle validation errors"""
        logger.info(
            f"Validation error: {error.message}",
            extra={"endpoint": request.endpoint}
        )
        
        return jsonify({
            "error": "Validation error",
            "message": error.message,
            "status_code": 400
        }), 400
    
    @app.errorhandler(404)
    def handle_not_found(error):
        """Handle 404 errors"""
        return jsonify({
            "error": "Not found",
            "message": f"The requested URL {request.path} was not found",
            "status_code": 404
        }), 404
    
    @app.errorhandler(405)
    def handle_method_not_allowed(error):
        """Handle 405 errors"""
        return jsonify({
            "error": "Method not allowed",
            "message": f"Method {request.method} not allowed for {request.path}",
            "status_code": 405
        }), 405
    
    @app.errorhandler(429)
    def handle_rate_limit(error):
        """Handle rate limit errors"""
        logger.warning(
            "Rate limit exceeded",
            extra={
                "ip": request.remote_addr,
                "endpoint": request.endpoint
            }
        )
        
        return jsonify({
            "error": "Rate limit exceeded",
            "message": "Too many requests. Please try again later.",
            "retry_after": str(error.description) if hasattr(error, 'description') else "60s",
            "status_code": 429
        }), 429
    
    @app.errorhandler(500)
    def handle_internal_error(error):
        """Handle 500 errors"""
        logger.error(
            "Internal server error",
            extra={
                "error": str(error),
                "endpoint": request.endpoint,
                "ip": request.remote_addr
            },
            exc_info=True
        )
        
        return jsonify({
            "error": "Internal server error",
            "message": "An unexpected error occurred. Please contact support.",
            "status_code": 500
        }), 500
    
    @app.errorhandler(503)
    def handle_service_unavailable(error):
        """Handle 503 errors"""
        logger.error("Service unavailable", extra={"error": str(error)})
        
        return jsonify({
            "error": "Service unavailable",
            "message": "The service is temporarily unavailable. Please try again later.",
            "status_code": 503
        }), 503
    
    @app.errorhandler(Exception)
    def handle_unexpected_error(error):
        """Handle any unexpected errors"""
        logger.error(
            "Unexpected error",
            extra={
                "error": str(error),
                "type": type(error).__name__,
                "endpoint": request.endpoint
            },
            exc_info=True
        )
        
        # Don't expose internal error details in production
        if app.config.get('DEBUG'):
            message = str(error)
        else:
            message = "An unexpected error occurred"
        
        return jsonify({
            "error": "Unexpected error",
            "message": message,
            "status_code": 500
        }), 500
    
    logger.info("✅ Error handlers registered")