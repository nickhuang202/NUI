#!/usr/bin/env python3
"""
Cross-platform compatibility test script.

Tests that all components work correctly on both Windows and Linux.
"""

import sys
import os
from pathlib import Path


def test_platform_detection():
    """Test platform detection."""
    print(f"[OK] Platform detected: {sys.platform}")
    print(f"[OK] Python version: {sys.version.split()[0]}")
    return True


def test_path_handling():
    """Test cross-platform path handling."""
    try:
        # Test Path operations
        test_path = Path.cwd()
        assert test_path.exists()
        print(f"[OK] Current directory: {test_path}")
        
        # Test path joining (works on both Windows and Linux)
        joined = test_path / "test" / "nested" / "path"
        print(f"[OK] Path joining works: {joined}")
        
        # Test absolute vs relative
        assert test_path.is_absolute()
        print(f"[OK] Absolute path detection works")
        
        return True
    except Exception as e:
        print(f"[FAIL] Path handling failed: {e}")
        return False


def test_file_repository():
    """Test FileRepository cross-platform."""
    try:
        from repositories.file_repository import FileRepository
        
        # Test with None (should use cwd)
        repo1 = FileRepository()
        assert repo1.base_dir is not None
        print(f"[OK] FileRepository with None: {repo1.base_dir}")
        
        # Test with string path
        if sys.platform == 'win32':
            test_path = 'C:\\temp'
        else:
            test_path = '/tmp'
        
        repo2 = FileRepository(test_path)
        assert repo2.base_dir == Path(test_path)
        print(f"[OK] FileRepository with string: {repo2.base_dir}")
        
        # Test with Path object
        repo3 = FileRepository(Path.cwd())
        assert repo3.base_dir == Path.cwd()
        print(f"[OK] FileRepository with Path: {repo3.base_dir}")
        
        return True
    except Exception as e:
        print(f"[FAIL] FileRepository test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_cache_repository():
    """Test CacheRepository cross-platform."""
    try:
        from repositories.cache_repository import CacheRepository
        
        # Test with None (should use default)
        cache1 = CacheRepository()
        assert cache1.cache_dir is not None
        print(f"[OK] CacheRepository with None: {cache1.cache_dir}")
        
        # Test with string path
        cache2 = CacheRepository('.test_cache')
        assert cache2.cache_dir == Path('.test_cache')
        print(f"[OK] CacheRepository with string: {cache2.cache_dir}")
        
        # Test with Path object
        cache3 = CacheRepository(Path('.test_cache2'))
        assert cache3.cache_dir == Path('.test_cache2')
        print(f"[OK] CacheRepository with Path: {cache3.cache_dir}")
        
        return True
    except Exception as e:
        print(f"[FAIL] CacheRepository test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_health_service():
    """Test HealthCheckService cross-platform."""
    try:
        from services.health_service import HealthCheckService
        
        service = HealthCheckService()
        system_info = service._get_system_info()
        
        # Verify expected fields exist
        assert 'platform' in system_info
        assert 'cpu_percent' in system_info
        assert 'memory_percent' in system_info
        assert 'disk_percent' in system_info
        
        print(f"[OK] HealthCheckService works on {sys.platform}")
        print(f"     Platform: {system_info['platform']}")
        print(f"     CPU: {system_info['cpu_percent']:.1f}%")
        print(f"     Memory: {system_info['memory_percent']:.1f}%")
        print(f"     Disk: {system_info['disk_percent']:.1f}%")
        
        return True
    except Exception as e:
        print(f"[FAIL] HealthCheckService test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_middleware():
    """Test middleware request ID generation."""
    try:
        from flask import Flask
        from middleware.request_id import generate_request_id
        
        app = Flask(__name__)
        
        with app.test_request_context('/'):
            request_id = generate_request_id()
            
            # Verify UUID format
            assert len(request_id) == 36
            assert request_id.count('-') == 4
            
            print(f"[OK] Request ID generation works: {request_id}")
            
        return True
    except Exception as e:
        print(f"[FAIL] Middleware test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Run all cross-platform tests."""
    print("\n" + "="*70)
    print(" Cross-Platform Compatibility Tests")
    print("="*70 + "\n")
    
    tests = [
        ('Platform Detection', test_platform_detection),
        ('Path Handling', test_path_handling),
        ('FileRepository', test_file_repository),
        ('CacheRepository', test_cache_repository),
        ('HealthCheckService', test_health_service),
        ('Middleware', test_middleware),
    ]
    
    passed = 0
    failed = 0
    
    for name, test_func in tests:
        print(f"\nTesting: {name}")
        print("-" * 70)
        try:
            if test_func():
                passed += 1
            else:
                failed += 1
        except Exception as e:
            failed += 1
            print(f"[FAIL] Unexpected error: {e}")
            import traceback
            traceback.print_exc()
    
    print("\n" + "="*70)
    print(f" Results: {passed}/{len(tests)} tests passed ({passed*100//len(tests)}%)")
    print("="*70)
    
    if failed == 0:
        print("\n[OK] All tests passed! Code is cross-platform compatible.")
        print("     The application should work on both Windows and Linux.\n")
        return 0
    else:
        print(f"\n[FAIL] {failed} test(s) failed.")
        print("       Please review the errors above.\n")
        return 1


if __name__ == '__main__':
    sys.exit(main())
