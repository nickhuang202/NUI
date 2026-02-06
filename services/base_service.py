"""
Base Service Class

Provides common functionality and utilities for all service classes.
"""

from typing import Optional, Dict, Any
from dataclasses import dataclass
from config.logging_config import get_logger


@dataclass
class ServiceResult:
    """Unified result wrapper for service operations"""
    
    success: bool
    data: Optional[Any] = None
    error: Optional[str] = None
    status_code: int = 200
    
    @classmethod
    def ok(cls, data: Any = None, status_code: int = 200) -> 'ServiceResult':
        """Create a successful result"""
        return cls(success=True, data=data, status_code=status_code)

    @classmethod
    def success(cls, data: Any = None, status_code: int = 200) -> 'ServiceResult':
        """Backward-compatible alias for ok()."""
        return cls.ok(data=data, status_code=status_code)
    
    @classmethod
    def fail(cls, error: str, status_code: int = 400) -> 'ServiceResult':
        """Create a failed result"""
        return cls(success=False, error=error, status_code=status_code)

    @classmethod
    def failure(cls, error: str, status_code: int = 400) -> 'ServiceResult':
        """Backward-compatible alias for fail()."""
        return cls.fail(error=error, status_code=status_code)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert result to dictionary for JSON responses"""
        if self.success:
            return {
                'success': True,
                'data': self.data
            }
        else:
            return {
                'success': False,
                'error': self.error
            }


class BaseService:
    """
    Base class for all service classes.
    
    Provides:
    - Logging capabilities
    - Common error handling patterns
    - Result wrapper utilities
    """
    
    def __init__(self):
        """Initialize service with logger"""
        self.logger = get_logger(self.__class__.__name__)
        
    def log_operation(self, operation: str, **kwargs):
        """Log a service operation with context"""
        context = ', '.join(f'{k}={v}' for k, v in kwargs.items())
        self.logger.info(f"[{operation}] {context}")
        
    def log_error(self, operation: str, error: Exception, **kwargs):
        """Log a service error with context"""
        context = ', '.join(f'{k}={v}' for k, v in kwargs.items())
        self.logger.error(f"[{operation}] Error: {str(error)} | Context: {context}")
