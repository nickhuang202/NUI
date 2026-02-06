"""Tests for middleware components."""
import pytest
from unittest.mock import Mock, MagicMock, patch
from flask import Flask, g
from middleware.request_id import (
    generate_request_id,
    get_request_id,
    setup_request_id_tracing
)


class TestGenerateRequestId:
    """Test cases for generate_request_id function."""
    
    def test_generates_uuid(self):
        """Test that generate_request_id returns a valid UUID string."""
        request_id = generate_request_id()
        
        assert isinstance(request_id, str)
        assert len(request_id) == 36  # UUID4 format: xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx
        assert request_id.count('-') == 4
    
    def test_generates_unique_ids(self):
        """Test that multiple calls generate different IDs."""
        id1 = generate_request_id()
        id2 = generate_request_id()
        id3 = generate_request_id()
        
        assert id1 != id2
        assert id2 != id3
        assert id1 != id3


class TestGetRequestId:
    """Test cases for get_request_id function."""
    
    def test_returns_request_id_from_g(self):
        """Test getting request ID from Flask's g object."""
        app = Flask(__name__)
        
        with app.app_context():
            # Manually set request_id in g
            g.request_id = "test-request-id-123"
            
            result = get_request_id()
            assert result == "test-request-id-123"
    
    def test_returns_none_when_not_set(self):
        """Test returns None when request_id not in g."""
        app = Flask(__name__)
        
        with app.app_context():
            result = get_request_id()
            assert result is None


class TestSetupRequestIdTracing:
    """Test cases for request ID tracing middleware."""
    
    @pytest.fixture
    def app(self):
        """Create a Flask app for testing."""
        app = Flask(__name__)
        
        @app.route('/test')
        def test_route():
            return {'message': 'test'}, 200
        
        @app.route('/with-existing-id')
        def test_with_id():
            # Access request_id from g
            from flask import g
            return {'request_id': g.request_id}, 200
        
        return app
    
    def test_middleware_adds_request_id_to_g(self, app):
        """Test that middleware adds request_id to Flask's g object."""
        setup_request_id_tracing(app)
        client = app.test_client()
        
        with app.app_context():
            response = client.get('/with-existing-id')
            data = response.get_json()
            
            # Should have generated a request_id
            assert 'request_id' in data
            assert len(data['request_id']) == 36  # UUID format
    
    def test_middleware_adds_header_to_response(self, app):
        """Test that middleware adds X-Request-ID header to response."""
        setup_request_id_tracing(app)
        client = app.test_client()
        
        response = client.get('/test')
        
        # Should have X-Request-ID in response headers
        assert 'X-Request-ID' in response.headers
        assert len(response.headers['X-Request-ID']) == 36
    
    def test_middleware_respects_existing_request_id(self, app):
        """Test that middleware uses existing X-Request-ID from request."""
        setup_request_id_tracing(app)
        client = app.test_client()
        
        existing_id = "existing-request-id-12345"
        response = client.get('/test', headers={'X-Request-ID': existing_id})
        
        # Should return the same request ID in response
        assert response.headers['X-Request-ID'] == existing_id
    
    def test_middleware_generates_new_id_when_missing(self, app):
        """Test that middleware generates new ID when not provided."""
        setup_request_id_tracing(app)
        client = app.test_client()
        
        response1 = client.get('/test')
        response2 = client.get('/test')
        
        id1 = response1.headers['X-Request-ID']
        id2 = response2.headers['X-Request-ID']
        
        # Should generate different IDs for different requests
        assert id1 != id2
    
    def test_middleware_logging_before_request(self, app):
        """Test that middleware logs before request processing."""
        setup_request_id_tracing(app)
        client = app.test_client()
        
        with patch('middleware.request_id.get_logger') as mock_get_logger:
            mock_logger = Mock()
            mock_get_logger.return_value = mock_logger
            
            # Need to re-setup to use mocked logger
            setup_request_id_tracing(app)
            
            response = client.get('/test')
            
            # Logger should have been called
            assert mock_logger.info.called
    
    def test_multiple_requests_different_ids(self, app):
        """Test that multiple requests get different request IDs."""
        setup_request_id_tracing(app)
        client = app.test_client()
        
        request_ids = []
        for _ in range(5):
            response = client.get('/test')
            request_ids.append(response.headers['X-Request-ID'])
        
        # All IDs should be unique
        assert len(set(request_ids)) == 5
    
    def test_request_id_available_in_route_handler(self, app):
        """Test that request_id is available in route handlers."""
        setup_request_id_tracing(app)
        
        @app.route('/access-request-id')
        def route_with_request_id():
            from flask import g
            return {'has_request_id': hasattr(g, 'request_id')}, 200
        
        client = app.test_client()
        response = client.get('/access-request-id')
        data = response.get_json()
        
        assert data['has_request_id'] is True


class TestRequestIdIntegration:
    """Integration tests for request ID tracing."""
    
    def test_request_id_flow(self):
        """Test complete request ID flow from request to response."""
        app = Flask(__name__)
        setup_request_id_tracing(app)
        
        captured_request_id = None
        
        @app.route('/capture')
        def capture_route():
            nonlocal captured_request_id
            captured_request_id = get_request_id()
            return {'ok': True}, 200
        
        client = app.test_client()
        provided_id = "my-custom-request-id"
        
        response = client.get('/capture', headers={'X-Request-ID': provided_id})
        
        # Request ID should be:
        # 1. Captured in route handler
        assert captured_request_id == provided_id
        
        # 2. Returned in response header
        assert response.headers['X-Request-ID'] == provided_id
    
    def test_request_id_with_error(self):
        """Test that request ID is still added even if route raises error."""
        app = Flask(__name__)
        setup_request_id_tracing(app)
        
        @app.route('/error')
        def error_route():
            raise ValueError("Test error")
        
        @app.errorhandler(ValueError)
        def handle_error(e):
            return {'error': str(e)}, 500
        
        client = app.test_client()
        response = client.get('/error')
        
        # Should still have request ID even with error
        assert 'X-Request-ID' in response.headers
        assert len(response.headers['X-Request-ID']) == 36
    
    def test_request_id_with_multiple_routes(self):
        """Test request ID tracing with multiple routes."""
        app = Flask(__name__)
        setup_request_id_tracing(app)
        
        @app.route('/route1')
        def route1():
            return {'route': 1, 'request_id': get_request_id()}, 200
        
        @app.route('/route2')
        def route2():
            return {'route': 2, 'request_id': get_request_id()}, 200
        
        client = app.test_client()
        
        # Each route should get its own request ID
        response1 = client.get('/route1')
        response2 = client.get('/route2')
        
        id1 = response1.headers['X-Request-ID']
        id2 = response2.headers['X-Request-ID']
        
        assert id1 != id2
        
        # Request IDs should match between header and route handler
        data1 = response1.get_json()
        data2 = response2.get_json()
        assert data1['request_id'] == id1
        assert data2['request_id'] == id2
