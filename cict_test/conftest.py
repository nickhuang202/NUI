"""Pytest configuration and shared fixtures."""

import os
import sys
import logging
from unittest.mock import patch

# Patch logging.basicConfig BEFORE any test modules are imported
# This prevents run_scheduled_profile.py from trying to create file handlers during test collection
_original_basicConfig = logging.basicConfig

def _patched_basicConfig(*args, **kwargs):
    """Override basicConfig to skip file-based logging during tests."""
    # Keep only the StreamHandler, remove FileHandler from handlers if present
    if 'handlers' in kwargs:
        handlers = kwargs['handlers']
        # Filter out FileHandler instances
        kwargs['handlers'] = [h for h in handlers if not isinstance(h, logging.FileHandler)]
    
    # Call original with modified handlers
    return _original_basicConfig(*args, **kwargs)

# Apply the patch
logging.basicConfig = _patched_basicConfig

# Also ensure logs directory exists as a fallback
_root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_logs_dir = os.path.join(_root_dir, 'logs')
try:
    os.makedirs(_logs_dir, exist_ok=True)
except (OSError, PermissionError):
    # If we can't create logs directory, that's OK during tests
    pass
