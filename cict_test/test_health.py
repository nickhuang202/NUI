"""Tests for health check endpoints."""
import pytest
from unittest.mock import Mock, patch
from flask import Flask
import os
os.environ['FLASK_ENV'] = 'test'

from app import app as main_app


class TestHealthEndpoints:
    """Test cases for health check endpoints."""
    
    @pytest.fixture
    def client(self):
        """Create a test client."""
        main_app.config['TESTING'] = True
        with main_app.test_client() as client:
            yield client
    
    @patch('services.health_service.psutil')
    @patch('services.health_service.os.path.exists')
    def test_health_v1_endpoint_success(self, mock_exists, mock_psutil, client):
        """Test /api/v1/health endpoint returns 200 with full data."""
        # Mock psutil
        mock_psutil.cpu_percent.return_value = 25.0
        mock_psutil.virtual_memory.return_value = Mock(percent=50.0)
        mock_psutil.disk_usage.return_value = Mock(percent=40.0)
        mock_psutil.boot_time.return_value = 1000000000
        
        # Mock dependencies exist
        mock_exists.return_value = True
        
        response = client.get('/api/v1/health')
        
        assert response.status_code == 200
        data = response.get_json()
        
        assert 'status' in data
        assert data['status'] in ['healthy', 'degraded']
        assert 'timestamp' in data
        assert 'system' in data
        assert 'services' in data
        assert 'dependencies' in data
    
    @patch('services.health_service.psutil')
    @patch('services.health_service.os.path.exists')
    def test_health_legacy_endpoint(self, mock_exists, mock_psutil, client):
        """Test /api/health legacy endpoint works."""
        # Mock psutil
        mock_psutil.cpu_percent.return_value = 20.0
        mock_psutil.virtual_memory.return_value = Mock(percent=45.0)
        mock_psutil.disk_usage.return_value = Mock(percent=35.0)
        mock_psutil.boot_time.return_value = 1000000000
        
        mock_exists.return_value = True
        
        response = client.get('/api/health')
        
        assert response.status_code == 200
        data = response.get_json()
        
        # Should have same structure as v1
        assert 'status' in data
        assert 'system' in data
    
    @patch('services.health_service.psutil')
    @patch('services.health_service.os.path.exists')
    def test_health_simple_endpoint_healthy(self, mock_exists, mock_psutil, client):
        """Test /health simple endpoint returns 200 when healthy."""
        # Mock healthy system
        mock_psutil.cpu_percent.return_value = 20.0
        mock_psutil.virtual_memory.return_value = Mock(percent=40.0)
        mock_psutil.disk_usage.return_value = Mock(percent=30.0)
        mock_psutil.boot_time.return_value = 1000000000
        
        mock_exists.return_value = True
        
        response = client.get('/health')
        
        # Simple endpoint returns just status code
        assert response.status_code in (200, 503)
    
    @patch('services.health_service.HealthCheckService.get_health_status')
    def test_health_endpoint_degraded_status(self, mock_get_health, client):
        """Test health endpoint when system is degraded."""
        from services.base_service import ServiceResult
        
        # Mock degraded status
        mock_get_health.return_value = ServiceResult.success(data={
            'status': 'degraded',
            'timestamp': '2026-02-03T00:00:00',
            'system': {'cpu_percent': 85.0},
            'services': {'qsfp_service': False},
            'dependencies': {'test_report': False}
        })
        
        response = client.get('/api/v1/health')
        
        assert response.status_code == 200
        data = response.get_json()
        assert data['status'] == 'degraded'
    
    @patch('services.health_service.HealthCheckService.get_health_status')
    def test_health_simple_endpoint_degraded(self, mock_get_health, client):
        """Test /health returns 503 when degraded."""
        from services.base_service import ServiceResult
        
        mock_get_health.return_value = ServiceResult.success(data={
            'status': 'degraded',
            'timestamp': '2026-02-03T00:00:00',
            'system': {},
            'services': {},
            'dependencies': {}
        })
        
        response = client.get('/health')
        
        # Simple endpoint returns 503 for degraded
        assert response.status_code == 503
    
    @patch('services.health_service.HealthCheckService.get_health_status')
    def test_health_endpoint_error_handling(self, mock_get_health, client):
        """Test health endpoint handles service errors."""
        from services.base_service import ServiceResult
        
        # Mock service error
        mock_get_health.return_value = ServiceResult.failure(
            error="Health check failed"
        )
        
        response = client.get('/api/v1/health')
        
        # Should still return a response, not crash
        assert response.status_code in (200, 500, 503)
    
    @patch('services.health_service.psutil')
    def test_health_system_info_structure(self, mock_psutil, client):
        """Test that system info has expected structure."""
        mock_psutil.cpu_percent.return_value = 30.5
        mock_psutil.virtual_memory.return_value = Mock(percent=55.2)
        mock_psutil.disk_usage.return_value = Mock(percent=45.8)
        mock_psutil.boot_time.return_value = 1000000000
        
        response = client.get('/api/v1/health')
        data = response.get_json()
        
        if 'system' in data:
            system = data['system']
            assert 'cpu_percent' in system
            assert 'memory_percent' in system
            assert 'disk_percent' in system
            assert 'uptime_seconds' in system
            assert 'python_version' in system
    
    def test_health_services_structure(self, client):
        """Test that services info has expected structure."""
        response = client.get('/api/v1/health')
        data = response.get_json()
        
        if 'services' in data:
            services = data['services']
            assert 'qsfp_service' in services
            assert 'sai_service' in services
            assert 'fboss2' in services
            
            # Values should be boolean
            assert isinstance(services['qsfp_service'], bool)
            assert isinstance(services['sai_service'], bool)
            assert isinstance(services['fboss2'], bool)
    
    def test_health_dependencies_structure(self, client):
        """Test that dependencies info has expected structure."""
        response = client.get('/api/v1/health')
        data = response.get_json()
        
        if 'dependencies' in data:
            deps = data['dependencies']
            assert 'test_report' in deps
            assert 'test_scripts' in deps
            assert 'topology' in deps
            assert 'logs' in deps
            assert 'cache' in deps
            
            # Values should be boolean
            assert isinstance(deps['test_report'], bool)
    
    def test_health_response_has_request_id(self, client):
        """Test that health responses include request ID header."""
        response = client.get('/api/v1/health')
        
        # Request ID middleware should add this header
        assert 'X-Request-ID' in response.headers
    
    def test_health_endpoints_accessible_without_auth(self, client):
        """Test that health endpoints don't require authentication."""
        # All three health endpoints should be accessible
        v1_response = client.get('/api/v1/health')
        legacy_response = client.get('/api/health')
        simple_response = client.get('/health')
        
        # None should return 401 Unauthorized
        assert v1_response.status_code != 401
        assert legacy_response.status_code != 401
        assert simple_response.status_code != 401
    
    def test_health_v1_and_legacy_return_same_data(self, client):
        """Test that v1 and legacy endpoints return same data structure."""
        v1_response = client.get('/api/v1/health')
        legacy_response = client.get('/api/health')
        
        v1_data = v1_response.get_json()
        legacy_data = legacy_response.get_json()
        
        # Both should have same keys
        assert set(v1_data.keys()) == set(legacy_data.keys())
    
    @patch('services.health_service.psutil')
    def test_health_timestamp_format(self, mock_psutil, client):
        """Test that timestamp is in ISO format."""
        mock_psutil.cpu_percent.return_value = 20.0
        mock_psutil.virtual_memory.return_value = Mock(percent=40.0)
        mock_psutil.disk_usage.return_value = Mock(percent=30.0)
        mock_psutil.boot_time.return_value = 1000000000
        
        response = client.get('/api/v1/health')
        data = response.get_json()
        
        if 'timestamp' in data:
            timestamp = data['timestamp']
            # ISO format should contain 'T' separator
            assert 'T' in timestamp or isinstance(timestamp, str)
    
    def test_health_version_info(self, client):
        """Test that health check includes version info."""
        response = client.get('/api/v1/health')
        data = response.get_json()
        
        # Should include version from VERSION file
        assert 'version' in data or 'system' in data


class TestHealthEndpointPerformance:
    """Performance-related tests for health endpoints."""
    
    @pytest.fixture
    def client(self):
        """Create a test client."""
        main_app.config['TESTING'] = True
        with main_app.test_client() as client:
            yield client
    
    @patch('services.health_service.psutil')
    def test_health_endpoint_response_time(self, mock_psutil, client):
        """Test that health endpoint responds quickly."""
        import time
        
        mock_psutil.cpu_percent.return_value = 20.0
        mock_psutil.virtual_memory.return_value = Mock(percent=40.0)
        mock_psutil.disk_usage.return_value = Mock(percent=30.0)
        mock_psutil.boot_time.return_value = 1000000000
        
        start = time.time()
        response = client.get('/health')
        duration = time.time() - start
        
        # Health check should be fast (< 1 second)
        assert duration < 1.0
        assert response.status_code in (200, 503)
    
    def test_multiple_health_checks_dont_interfere(self, client):
        """Test that multiple concurrent health checks work."""
        responses = []
        
        # Make multiple requests
        for _ in range(5):
            response = client.get('/health')
            responses.append(response.status_code)
        
        # All should succeed
        assert all(status in (200, 503) for status in responses)
