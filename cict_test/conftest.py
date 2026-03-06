"""Pytest configuration and shared fixtures."""

import os
import pytest


@pytest.fixture(scope="session", autouse=True)
def setup_test_environment():
    """Ensure test environment directories exist."""
    # Create logs directory if it doesn't exist
    logs_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'logs')
    os.makedirs(logs_dir, exist_ok=True)
    
    yield
    
    # Cleanup is optional - you can remove this if you want to keep logs
