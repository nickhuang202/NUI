"""
Health Check Routes Blueprint

Provides health check and system status endpoints for monitoring.
"""

from flask import Blueprint, jsonify
from services.health_service import HealthCheckService

# Create blueprint
health_bp = Blueprint('health', __name__)

# Initialize service
health_service = HealthCheckService()


@health_bp.route('/api/v1/health', methods=['GET'])
def get_health():
    """
    Get comprehensive health status.
    
    Returns:
        JSON response with:
        - status: 'healthy' or 'degraded'
        - timestamp: Current time
        - uptime_seconds: Application uptime
        - version: Application version
        - system: System resources (CPU, memory, disk)
        - services: External service status (qsfp, sai, fboss2)
        - dependencies: File/directory dependencies
    
    Example:
        GET /api/v1/health
        
    Response:
        {
            "success": true,
            "data": {
                "status": "healthy",
                "timestamp": "2026-02-03T21:45:00",
                "uptime_seconds": 3600.5,
                "version": "0.0.0.59",
                "system": {
                    "python_version": "3.10.11",
                    "platform": "win32",
                    "cpu_count": 8,
                    "cpu_percent": 15.2,
                    "memory_total_mb": 16384.0,
                    "memory_used_mb": 8192.0,
                    "memory_percent": 50.0,
                    "disk_total_gb": 500.0,
                    "disk_used_gb": 250.0,
                    "disk_percent": 50.0
                },
                "services": {
                    "qsfp_service": false,
                    "sai_service": false,
                    "fboss2": false,
                    "all_healthy": false
                },
                "dependencies": {
                    "test_report_dir": true,
                    "test_scripts_dir": true,
                    "topology_dir": true,
                    "logs_dir": true,
                    "cache_dir": true,
                    "all_available": true
                }
            }
        }
    """
    result = health_service.get_health_status()
    if result.success and isinstance(result.data, dict):
        data = result.data.copy()
        deps = data.get('dependencies')
        if isinstance(deps, dict):
            mapped = {
                'test_report': deps.get('test_report_dir', deps.get('test_report')),
                'test_scripts': deps.get('test_scripts_dir', deps.get('test_scripts')),
                'topology': deps.get('topology_dir', deps.get('topology')),
                'logs': deps.get('logs_dir', deps.get('logs')),
                'cache': deps.get('cache_dir', deps.get('cache')),
                'all_available': deps.get('all_available')
            }
            deps.update({k: v for k, v in mapped.items() if v is not None})
        return jsonify(data), result.status_code
    status_code = result.status_code if result.status_code >= 500 else 500
    return jsonify({'error': result.error or 'Health check failed'}), status_code


@health_bp.route('/api/health', methods=['GET'])
def get_health_legacy():
    """
    Legacy health endpoint (backward compatibility).
    Redirects to /api/v1/health
    """
    return get_health()


@health_bp.route('/health', methods=['GET'])
def get_health_simple():
    """
    Simple health check endpoint (minimal response for load balancers).
    
    Returns:
        JSON response with status only
        
    Example:
        GET /health
        
    Response:
        {"status": "healthy"}
    """
    result = health_service.get_health_status()
    
    if result.success:
        status = result.data.get('status', 'unknown') if isinstance(result.data, dict) else 'unknown'
        if status != 'healthy':
            return jsonify({'status': status}), 503
        return jsonify({'status': status}), 200
    return jsonify({'status': 'unhealthy'}), 503
