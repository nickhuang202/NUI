"""Test API versioning with HTTP requests."""
import os
os.environ['FLASK_ENV'] = 'test'

from app import app

def test_versioned_routes():
    """Test that both v1 and legacy routes work."""
    client = app.test_client()
    
    # Test dashboard routes
    print("\n[Testing Dashboard Routes]")
    v1_response = client.get('/api/v1/dashboard/current_platform')
    legacy_response = client.get('/api/dashboard/current_platform')
    print(f"  V1 route (/api/v1/dashboard/current_platform): {v1_response.status_code}")
    print(f"  Legacy route (/api/dashboard/current_platform): {legacy_response.status_code}")
    assert v1_response.status_code == 200
    assert legacy_response.status_code == 200
    
    # Test test routes
    print("\n[Testing Test Routes]")
    v1_response = client.get('/api/v1/test/status')
    legacy_response = client.get('/api/test/status')
    print(f"  V1 route (/api/v1/test/status): {v1_response.status_code}")
    print(f"  Legacy route (/api/test/status): {legacy_response.status_code}")
    assert v1_response.status_code == 200
    assert legacy_response.status_code == 200
    
    # Test lab monitor routes
    print("\n[Testing Lab Monitor Routes]")
    v1_response = client.get('/api/v1/lab_monitor/status')
    legacy_response = client.get('/api/lab_monitor/status')
    print(f"  V1 route (/api/v1/lab_monitor/status): {v1_response.status_code}")
    print(f"  Legacy route (/api/lab_monitor/status): {legacy_response.status_code}")
    # These may be 200 or 404 depending on lab_config.json
    assert v1_response.status_code in (200, 404)
    assert legacy_response.status_code in (200, 404)
    
    # Test port routes
    print("\n[Testing Port Routes]")
    v1_response = client.get('/api/v1/absent_ports')
    legacy_response = client.get('/api/absent_ports')
    print(f"  V1 route (/api/v1/absent_ports): {v1_response.status_code}")
    print(f"  Legacy route (/api/absent_ports): {legacy_response.status_code}")
    # These may be 200, 404, or 503 depending on services
    assert v1_response.status_code in (200, 404, 503)
    assert legacy_response.status_code in (200, 404, 503)
    
    # Test health route (already has internal v1/legacy)
    print("\n[Testing Health Routes]")
    v1_response = client.get('/api/v1/health')
    legacy_response = client.get('/api/health')
    simple_response = client.get('/health')
    print(f"  V1 route (/api/v1/health): {v1_response.status_code}")
    print(f"  Legacy route (/api/health): {legacy_response.status_code}")
    print(f"  Simple route (/health): {simple_response.status_code}")
    assert v1_response.status_code == 200
    assert legacy_response.status_code == 200
    assert simple_response.status_code == 200
    
    print("\n[OK] All versioning tests passed!")
    return True

if __name__ == '__main__':
    test_versioned_routes()
