#!/usr/bin/env python3
"""
Check if all required dependencies are installed.
"""
import sys

def check_requirements():
    """Check if all required packages are available."""
    print("Checking Phase 1 dependencies...\n")
    
    required = [
        ('flask', 'Flask>=2.0'),
        ('requests', 'requests>=2.0'),
        ('flask_limiter', 'Flask-Limiter>=3.0'),
        ('jwt', 'PyJWT>=2.0'),
    ]
    
    optional = [
        ('pytest', 'pytest>=7.4.0 (for testing)'),
        ('pytest_cov', 'pytest-cov>=4.1.0 (for coverage)'),
        ('pytest_mock', 'pytest-mock>=3.11.1 (for mocking)'),
    ]
    
    missing_required = []
    missing_optional = []
    
    print("Required Dependencies:")
    for module, desc in required:
        try:
            __import__(module)
            print(f"  ✓ {desc}")
        except ImportError:
            print(f"  ✗ {desc} - NOT INSTALLED")
            missing_required.append(desc.split('>=')[0])
    
    print("\nOptional Dependencies (for testing):")
    for module, desc in optional:
        try:
            __import__(module)
            print(f"  ✓ {desc}")
        except ImportError:
            print(f"  ⚠ {desc} - NOT INSTALLED")
            missing_optional.append(desc.split('>=')[0])
    
    print("\n" + "=" * 60)
    
    if missing_required:
        print("✗ Missing required dependencies!")
        print("\nTo install missing required packages:")
        print(f"  pip install {' '.join(missing_required)}")
        print("\nOr install all from requirements.txt:")
        print("  pip install -r requirements.txt")
        return False
    else:
        print("✓ All required dependencies are installed!")
        
        if missing_optional:
            print(f"\n⚠ {len(missing_optional)} optional testing package(s) not installed")
            print("\nTo enable full testing capabilities:")
            print("  pip install pytest pytest-cov pytest-mock")
        else:
            print("✓ All optional dependencies are also installed!")
        
        print("\n✓ Ready to run:")
        print("  - Quick validation: python quick_test.py")
        if not missing_optional:
            print("  - Full test suite: pytest tests/")
            print("  - With coverage: pytest --cov=config --cov=utils --cov=middleware")
        
        return True


if __name__ == "__main__":
    success = check_requirements()
    exit(0 if success else 1)
