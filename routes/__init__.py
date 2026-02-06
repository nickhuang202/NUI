"""
Flask Blueprints for NUI Application
Modularizes the 95 routes into logical groups
"""

from flask import Blueprint

# Import blueprints from their modules
from routes.dashboard import dashboard_bp
from routes.test import test_bp
from routes.topology import topology_bp
from routes.lab_monitor import lab_monitor_bp
from routes.ports import port_bp
from routes.health import health_bp

# LLDP blueprint to be implemented
lldp_bp = Blueprint('lldp', __name__, url_prefix='/api/lldp')

__all__ = [
    'dashboard_bp',
    'test_bp', 
    'topology_bp',
    'lab_monitor_bp',
    'port_bp',
    'health_bp',
    'lldp_bp'
]
