"""Input validation utilities for NUI application.

Provides sanitization and validation functions to prevent:
- Path traversal attacks
- Command injection
- Invalid input data
"""
import os
import re
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)

# Allowed platform names (whitelist)
ALLOWED_PLATFORMS = {
    'MINIPACK3BA',
    'MINIPACK3N',
    'WEDGE800BACT',
    'WEDGE800CACT'
}

# Allowed test types (whitelist)
ALLOWED_TEST_TYPES = {
    'sai',
    'link',
    'agent_hw',
    'prbs',
    'link_t0',
    'link_t1',
    'link_t2',
    'sai_t0',
    'sai_t1',
    'sai_t2',
    'agent_t0',
    'agent_t1',
    'agent_t2',
    'evt_exit'
}


def sanitize_path(path: str, base_dir: Optional[str] = None) -> Optional[str]:
    """Sanitize file path to prevent path traversal attacks.
    
    Args:
        path: User-provided path
        base_dir: Base directory to constrain paths within
    
    Returns:
        str: Sanitized absolute path, or None if invalid
    """
    if not path:
        return None
    
    try:
        # Remove any dangerous characters
        path = path.replace('\x00', '')
        
        # Resolve to absolute path
        abs_path = Path(path).resolve()
        
        # If base_dir specified, ensure path is within it
        if base_dir:
            base = Path(base_dir).resolve()
            try:
                abs_path.relative_to(base)
            except ValueError:
                logger.warning(f'Path traversal attempt detected: {path} outside {base_dir}')
                return None
        
        return str(abs_path)
    
    except Exception as e:
        logger.error(f'Error sanitizing path "{path}": {e}')
        return None


def is_safe_filename(filename: str) -> bool:
    """Check if filename is safe (no path traversal or special characters).
    
    Args:
        filename: Filename to validate
    
    Returns:
        bool: True if safe, False otherwise
    """
    if not filename:
        return False
    
    # Check for path traversal attempts
    if '..' in filename or '/' in filename or '\\' in filename:
        return False
    
    # Check for null bytes
    if '\x00' in filename:
        return False
    
    # Allow only alphanumeric, dash, underscore, dot
    if not re.match(r'^[a-zA-Z0-9._-]+$', filename):
        return False
    
    return True


def validate_platform(platform: str) -> bool:
    """Validate platform name against whitelist.
    
    Args:
        platform: Platform name to validate
    
    Returns:
        bool: True if valid, False otherwise
    """
    if not platform:
        return False
    
    platform_upper = platform.upper()
    is_valid = platform_upper in ALLOWED_PLATFORMS
    
    if not is_valid:
        logger.warning(f'Invalid platform name: {platform}')
    
    return is_valid


def validate_date(date_str: str) -> bool:
    """Validate date string format (YYYY-MM-DD).
    
    Args:
        date_str: Date string to validate
    
    Returns:
        bool: True if valid, False otherwise
    """
    if not date_str:
        return False
    
    if not re.match(r'^\d{4}-\d{2}-\d{2}$', date_str):
        logger.warning(f'Invalid date format: {date_str}')
        return False

    try:
        datetime.strptime(date_str, '%Y-%m-%d')
        return True
    except ValueError:
        logger.warning(f'Invalid date format: {date_str}')
        return False


def validate_test_items(test_items: Dict[str, Any]) -> Dict[str, Any]:
    """Validate and sanitize test items dictionary.
    
    Args:
        test_items: Test items configuration
    
    Returns:
        dict: Validated test items, or empty dict if invalid
    """
    if not isinstance(test_items, dict):
        logger.error('test_items must be a dictionary')
        return {}
    
    validated = {}
    
    for key, value in test_items.items():
        # Validate test type keys
        if key not in ALLOWED_TEST_TYPES:
            logger.warning(f'Unknown test type: {key}')
            continue
        
        # Ensure boolean values
        if not isinstance(value, bool):
            logger.warning(f'Invalid value for {key}: {value}, expected boolean')
            continue
        
        validated[key] = value
    
    return validated


def sanitize_command_arg(arg: str) -> str:
    """Sanitize command line argument.
    
    Args:
        arg: Argument to sanitize
    
    Returns:
        str: Sanitized argument with dangerous characters removed
    """
    if not arg:
        return ''
    
    # Remove shell metacharacters
    dangerous_chars = ';|&$`<>"\'\n\r\t\\'
    sanitized = ''.join(c for c in arg if c not in dangerous_chars)
    
    return sanitized


def validate_port_number(port: Any) -> bool:
    """Validate port number.
    
    Args:
        port: Port number to validate
    
    Returns:
        bool: True if valid port (1-65535), False otherwise
    """
    try:
        port_int = int(port)
        return 1 <= port_int <= 65535
    except (ValueError, TypeError):
        return False


def validate_ip_address(ip: str) -> bool:
    """Validate IPv4 address format.
    
    Args:
        ip: IP address string
    
    Returns:
        bool: True if valid IPv4, False otherwise
    """
    if not ip:
        return False
    
    pattern = r'^(\d{1,3}\.){3}\d{1,3}$'
    if not re.match(pattern, ip):
        return False
    
    # Check each octet is 0-255
    octets = ip.split('.')
    for octet in octets:
        if not 0 <= int(octet) <= 255:
            return False
    
    return True
