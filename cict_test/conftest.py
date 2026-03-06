"""Pytest configuration and shared fixtures."""

import os

# Create required directories BEFORE any test modules are imported
# This is critical because run_scheduled_profile.py sets up logging during import
_root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_logs_dir = os.path.join(_root_dir, 'logs')
os.makedirs(_logs_dir, exist_ok=True)
