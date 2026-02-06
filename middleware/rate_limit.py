"""Rate limiting middleware for NUI application.

Protects against DoS attacks by limiting request rates.
Requires: Flask-Limiter>=3.0
"""
from flask import request
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
import logging

logger = logging.getLogger(__name__)


def setup_rate_limiting(app, config):
    """Configure rate limiting for the Flask application.
    
    Args:
        app: Flask application instance
        config: Configuration object with rate limit settings
    
    Returns:
        Limiter: Configured limiter instance
    """
    if not config.RATE_LIMIT_ENABLED:
        logger.info('Rate limiting is disabled')
        return None
    
    limiter = Limiter(
        app=app,
        key_func=get_remote_address,
        default_limits=[config.RATE_LIMIT_DEFAULT],
        storage_uri="memory://",  # Use in-memory storage (consider Redis for production)
        strategy="fixed-window"
    )
    
    logger.info(f'Rate limiting configured: {config.RATE_LIMIT_DEFAULT}')
    
    return limiter


def get_rate_limit_key():
    """Custom key function for rate limiting.
    
    Uses X-Forwarded-For if behind a proxy, otherwise uses remote address.
    
    Returns:
        str: Client identifier for rate limiting
    """
    if request.headers.get('X-Forwarded-For'):
        return request.headers.get('X-Forwarded-For').split(',')[0].strip()
    return get_remote_address()
