"""
Request/Response Logging Middleware
Logs all API requests with method, path, status code, and duration.
"""

import time
from flask import request, g
from config.logging_config import get_logger

logger = get_logger(__name__)


def setup_request_logging(app):
    """Setup request/response logging middleware."""
    
    @app.before_request
    def log_request_start():
        """Log request details before processing."""
        # Store start time on request context
        request._start_time = time.time()
        
        # Get request ID if available
        request_id = getattr(g, 'request_id', 'unknown')
        
        # Log incoming request with ID
        logger.info(
            f"[{request_id}] → {request.method} {request.path} "
            f"from {request.remote_addr}"
        )
    
    @app.after_request
    def log_request_end(response):
        """Log response details after processing."""
        # Calculate duration
        if hasattr(request, '_start_time'):
            duration = (time.time() - request._start_time) * 1000  # Convert to ms
        else:
            duration = 0
        
        # Get request ID if available
        request_id = getattr(g, 'request_id', 'unknown')
        
        # Log response with ID
        logger.info(
            f"[{request_id}] ← {request.method} {request.path} "
            f"[{response.status_code}] "
            f"{duration:.2f}ms"
        )
        
        return response
    
    @app.teardown_request
    def log_request_error(error=None):
        """Log any errors that occurred during request processing."""
        if error:
            # Get request ID if available
            request_id = getattr(g, 'request_id', 'unknown')
            
            logger.error(
                f"[{request_id}] ✗ {request.method} {request.path} "
                f"ERROR: {str(error)}"
            )
    
    logger.info("Request/response logging middleware enabled")
