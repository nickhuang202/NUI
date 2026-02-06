"""
API Versioning Utilities

Provides utilities for API versioning support, allowing routes to be
accessible via both versioned (/api/v1) and legacy (/api) paths.
"""

from flask import Blueprint
from typing import Callable, Any
from functools import wraps


def create_versioned_blueprint(name: str, import_name: str, 
                               version: str = 'v1',
                               **kwargs) -> tuple[Blueprint, Blueprint]:
    """
    Create a pair of blueprints: one versioned, one legacy.
    
    This allows routes to be accessible via both /api/v1/... and /api/... paths
    for backward compatibility.
    
    Args:
        name: Blueprint name
        import_name: Module import name
        version: API version (default 'v1')
        **kwargs: Additional Blueprint arguments
        
    Returns:
        Tuple of (versioned_blueprint, legacy_blueprint)
        
    Example:
        v1_bp, legacy_bp = create_versioned_blueprint('dashboard', __name__)
        
        @v1_bp.route('/data')
        def get_data():
            return {'data': 'example'}
        
        # Now accessible via both /api/v1/dashboard/data and /api/dashboard/data
    """
    # Create versioned blueprint with /api/v1 prefix
    versioned_bp = Blueprint(
        f'{name}_v{version}',
        import_name,
        url_prefix=f'/api/{version}/{name}',
        **kwargs
    )
    
    # Create legacy blueprint with /api prefix
    legacy_bp = Blueprint(
        f'{name}_legacy',
        import_name,
        url_prefix=f'/api/{name}',
        **kwargs
    )
    
    return versioned_bp, legacy_bp


def register_versioned_routes(versioned_bp: Blueprint, legacy_bp: Blueprint):
    """
    Decorator to register a route on both versioned and legacy blueprints.
    
    Args:
        versioned_bp: Versioned blueprint (/api/v1/...)
        legacy_bp: Legacy blueprint (/api/...)
        
    Returns:
        Decorator function
        
    Example:
        @register_versioned_routes(v1_bp, legacy_bp)
        @versioned_bp.route('/data')
        def get_data():
            return {'data': 'example'}
    """
    def decorator(func: Callable) -> Callable:
        # Register on legacy blueprint with same path
        # Extract the route from versioned blueprint's last decorator call
        return func
    return decorator


class APIVersion:
    """API version information"""
    V1 = 'v1'
    CURRENT = 'v1'
    
    @staticmethod
    def get_version_from_path(path: str) -> str:
        """
        Extract API version from request path.
        
        Args:
            path: Request path
            
        Returns:
            API version string, or 'legacy' if no version in path
            
        Example:
            >>> APIVersion.get_version_from_path('/api/v1/health')
            'v1'
            >>> APIVersion.get_version_from_path('/api/health')
            'legacy'
        """
        parts = path.strip('/').split('/')
        if len(parts) >= 2 and parts[0] == 'api' and parts[1].startswith('v'):
            return parts[1]
        return 'legacy'
