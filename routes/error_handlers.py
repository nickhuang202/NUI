"""
Centralized Error Handlers for NUI Application
Provides consistent error responses across all endpoints
"""

from flask import jsonify, request
from werkzeug.exceptions import HTTPException
import traceback
from config import get_config

config = get_config()


def register_error_handlers(app):
    """Register all error handlers with the Flask app"""
    
    @app.errorhandler(400)
    def bad_request(error):
        """Handle 400 Bad Request errors"""
        app.logger.warning(f"Bad Request: {request.url} - {error}")
        return jsonify({
            'error': 'Bad Request',
            'message': str(error.description) if hasattr(error, 'description') else str(error),
            'status': 400
        }), 400
    
    @app.errorhandler(401)
    def unauthorized(error):
        """Handle 401 Unauthorized errors"""
        app.logger.warning(f"Unauthorized access attempt: {request.url}")
        return jsonify({
            'error': 'Unauthorized',
            'message': 'Authentication required',
            'status': 401
        }), 401
    
    @app.errorhandler(403)
    def forbidden(error):
        """Handle 403 Forbidden errors"""
        app.logger.warning(f"Forbidden access: {request.url}")
        return jsonify({
            'error': 'Forbidden',
            'message': 'Access denied',
            'status': 403
        }), 403
    
    @app.errorhandler(404)
    def not_found(error):
        """Handle 404 Not Found errors"""
        app.logger.info(f"Resource not found: {request.url}")
        return jsonify({
            'error': 'Not Found',
            'message': str(error.description) if hasattr(error, 'description') else 'Resource not found',
            'status': 404
        }), 404
    
    @app.errorhandler(405)
    def method_not_allowed(error):
        """Handle 405 Method Not Allowed errors"""
        app.logger.warning(f"Method not allowed: {request.method} {request.url}")
        return jsonify({
            'error': 'Method Not Allowed',
            'message': f'{request.method} method not allowed for this endpoint',
            'status': 405
        }), 405
    
    @app.errorhandler(409)
    def conflict(error):
        """Handle 409 Conflict errors"""
        app.logger.warning(f"Conflict: {request.url} - {error}")
        return jsonify({
            'error': 'Conflict',
            'message': str(error.description) if hasattr(error, 'description') else 'Request conflict',
            'status': 409
        }), 409
    
    @app.errorhandler(429)
    def rate_limit_exceeded(error):
        """Handle 429 Rate Limit Exceeded errors"""
        app.logger.warning(f"Rate limit exceeded: {request.url} - {request.remote_addr}")
        return jsonify({
            'error': 'Too Many Requests',
            'message': 'Rate limit exceeded. Please try again later.',
            'status': 429
        }), 429
    
    @app.errorhandler(500)
    def internal_error(error):
        """Handle 500 Internal Server Error"""
        app.logger.error(f"Internal server error: {request.url}")
        app.logger.error(traceback.format_exc())
        
        # In production, don't expose internal details
        if config.DEBUG:
            return jsonify({
                'error': 'Internal Server Error',
                'message': str(error),
                'traceback': traceback.format_exc(),
                'status': 500
            }), 500
        else:
            return jsonify({
                'error': 'Internal Server Error',
                'message': 'An unexpected error occurred. Please contact support.',
                'status': 500
            }), 500
    
    @app.errorhandler(503)
    def service_unavailable(error):
        """Handle 503 Service Unavailable errors"""
        app.logger.error(f"Service unavailable: {request.url}")
        return jsonify({
            'error': 'Service Unavailable',
            'message': 'Service temporarily unavailable. Please try again later.',
            'status': 503
        }), 503
    
    @app.errorhandler(Exception)
    def handle_unexpected_error(error):
        """Catch-all handler for unexpected exceptions"""
        app.logger.error(f"Unexpected error: {request.url}")
        app.logger.error(f"Error type: {type(error).__name__}")
        app.logger.error(traceback.format_exc())
        
        # If it's an HTTPException, let it pass through to specific handlers
        if isinstance(error, HTTPException):
            return error
        
        # For all other exceptions
        if config.DEBUG:
            return jsonify({
                'error': 'Unexpected Error',
                'type': type(error).__name__,
                'message': str(error),
                'traceback': traceback.format_exc(),
                'status': 500
            }), 500
        else:
            return jsonify({
                'error': 'Unexpected Error',
                'message': 'An unexpected error occurred. Please contact support.',
                'status': 500
            }), 500
    
    app.logger.info("Error handlers registered successfully")


def create_error_response(message, status_code=500, **kwargs):
    """
    Helper function to create consistent error responses
    
    Args:
        message: Error message string
        status_code: HTTP status code (default 500)
        **kwargs: Additional fields to include in response
    
    Returns:
        Tuple of (json_response, status_code)
    """
    response = {
        'success': False,
        'error': message,
        'status': status_code
    }
    response.update(kwargs)
    return jsonify(response), status_code


def create_success_response(data=None, message=None, **kwargs):
    """
    Helper function to create consistent success responses
    
    Args:
        data: Response data (optional)
        message: Success message (optional)
        **kwargs: Additional fields to include in response
    
    Returns:
        Tuple of (json_response, status_code)
    """
    response = {
        'success': True,
        'status': 200
    }
    
    if data is not None:
        response['data'] = data
    
    if message is not None:
        response['message'] = message
    
    response.update(kwargs)
    return jsonify(response), 200
