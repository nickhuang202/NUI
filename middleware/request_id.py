"""
Request ID Tracing Middleware

Adds a unique request ID to each request for distributed tracing and debugging.
The request ID is:
- Generated or extracted from X-Request-ID header
- Added to response headers
- Included in all log messages for the request
- Available to route handlers via g.request_id
"""

import uuid
from flask import g, request, has_request_context, has_app_context
from config.logging_config import get_logger


def generate_request_id() -> str:
    """Generate a unique request ID"""
    return str(uuid.uuid4())


def get_request_id() -> str:
    """
    Get the current request ID.
    
    Returns:
        Request ID string, or 'no-request' if outside request context
    """
    if has_request_context() and hasattr(g, 'request_id'):
        return g.request_id
    if has_app_context() and hasattr(g, 'request_id'):
        return g.request_id
    return None


def setup_request_id_tracing(app):
    """
    Setup request ID tracing middleware.
    
    Adds unique request IDs to all requests for tracing and debugging.
    Request IDs are:
    1. Extracted from X-Request-ID header if present
    2. Generated automatically if not present
    3. Added to response headers
    4. Available in logs via g.request_id
    
    Args:
        app: Flask application instance
    """
    
    logger = get_logger(__name__)

    @app.before_request
    def add_request_id():
        """Add or generate request ID before processing request"""
        # Check if request ID provided by client (for distributed tracing)
        request_id = request.headers.get('X-Request-ID')
        
        if not request_id:
            # Generate new request ID
            request_id = generate_request_id()
        
        # Store in Flask's g object for access throughout request
        g.request_id = request_id
        
        # Log request with ID
        logger.info(
            f"[{request_id}] {request.method} {request.path} "
            f"from {request.remote_addr}"
        )
    
    @app.after_request
    def add_request_id_to_response(response):
        """Add request ID to response headers"""
        if hasattr(g, 'request_id'):
            response.headers['X-Request-ID'] = g.request_id
        return response
    
    logger.info("Request ID tracing middleware enabled")
