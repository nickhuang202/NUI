"""Logging configuration for NUI application.

This module provides structured logging with rotation and proper formatters.
Replaces print() statements throughout the application.
"""
import logging
import os
from logging.handlers import RotatingFileHandler
from pathlib import Path


def setup_logging(app=None, log_level=None):
    """Configure structured logging for the application.
    
    Args:
        app: Flask application instance (optional)
        log_level: Logging level (default: INFO, or from environment)
    
    Returns:
        logging.Logger: Configured logger instance
    """
    # Determine log level
    if log_level is None:
        log_level_str = os.getenv('LOG_LEVEL', 'INFO').upper()
        log_level = getattr(logging, log_level_str, logging.INFO)
    
    # Create logs directory if it doesn't exist
    log_dir = Path(os.getcwd()) / 'logs'
    log_dir.mkdir(exist_ok=True)
    
    # Configure formatter
    formatter = logging.Formatter(
        '[%(asctime)s] %(levelname)s in %(module)s.%(funcName)s:%(lineno)d - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # File handler with rotation (10MB per file, keep 10 backups)
    log_file = log_dir / 'nui.log'
    file_handler = RotatingFileHandler(
        log_file,
        maxBytes=10485760,  # 10MB
        backupCount=10,
        encoding='utf-8'
    )
    file_handler.setFormatter(formatter)
    file_handler.setLevel(log_level)
    
    # Console handler for development
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    console_handler.setLevel(log_level)
    
    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)
    
    # Remove existing handlers to avoid duplicates
    root_logger.handlers.clear()
    
    # Add handlers
    root_logger.addHandler(file_handler)
    root_logger.addHandler(console_handler)
    
    # Configure Flask app logger if provided
    if app:
        app.logger.handlers.clear()
        app.logger.addHandler(file_handler)
        app.logger.addHandler(console_handler)
        app.logger.setLevel(log_level)
        app.logger.info('Logging configured for NUI application')
    else:
        root_logger.info('Logging configured (standalone mode)')
    
    return app.logger if app else root_logger


def get_logger(name):
    """Get a logger instance for a specific module.
    
    Args:
        name: Logger name (typically __name__)
    
    Returns:
        logging.Logger: Logger instance
    """
    return logging.getLogger(name)
