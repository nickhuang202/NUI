"""
API Versioning Blueprint Wrapper

Creates versioned API blueprints that respond to both /api/v1/... and /api/... paths.
"""

from flask import Blueprint
from typing import List, Tuple


def register_with_versioning(app, blueprint: Blueprint, version: str = 'v1'):
    """
    Register a blueprint to respond to both versioned and legacy paths.
    
    This creates a wrapper that makes routes accessible via:
    - /api/v1/{blueprint_prefix}/... (versioned)
    - /api/{blueprint_prefix}/... (legacy, backward compatibility)
    
    Args:
        app: Flask application
        blueprint: Blueprint to register
        version: API version (default 'v1')
        
    Example:
        dashboard_bp = Blueprint('dashboard', __name__, url_prefix='/api/dashboard')
        register_with_versioning(app, dashboard_bp)
        # Now accessible via /api/v1/dashboard/... AND /api/dashboard/...
    """
    # Register original blueprint (legacy path)
    app.register_blueprint(blueprint)
    
    # Create versioned copy
    if blueprint.url_prefix and blueprint.url_prefix.startswith('/api/'):
        # Extract the part after /api/
        suffix = blueprint.url_prefix[4:]  # Remove '/api'
        
        # Create new blueprint with versioned prefix
        versioned_name = f"{blueprint.name}_v{version}"
        versioned_prefix = f"/api/{version}{suffix}"
        
        # Create a new blueprint that shares the same view functions
        versioned_bp = Blueprint(
            versioned_name,
            blueprint.import_name,
            url_prefix=versioned_prefix
        )
        
        # Copy all routes from original blueprint
        for rule in app.url_map.iter_rules():
            if rule.endpoint.startswith(f"{blueprint.name}."):
                # Get the view function
                view_func = app.view_functions[rule.endpoint]
                
                # Extract the route path (relative to blueprint prefix)
                if blueprint.url_prefix:
                    route_path = rule.rule[len(blueprint.url_prefix):]
                else:
                    route_path = rule.rule
                
                # Add route to versioned blueprint
                versioned_bp.add_url_rule(
                    route_path,
                    endpoint=rule.endpoint.split('.')[-1],
                    view_func=view_func,
                    methods=rule.methods - {'HEAD', 'OPTIONS'}
                )
        
        # Register versioned blueprint
        app.register_blueprint(versioned_bp)
        
        return versioned_name
    
    return None


def register_all_with_versioning(app, blueprints: List[Blueprint], version: str = 'v1'):
    """
    Register multiple blueprints with versioning support.
    
    Args:
        app: Flask application
        blueprints: List of blueprints to register
        version: API version (default 'v1')
        
    Returns:
        List of (original_name, versioned_name) tuples
    """
    registered = []
    
    for bp in blueprints:
        versioned_name = register_with_versioning(app, bp, version)
        registered.append((bp.name, versioned_name))
    
    return registered
