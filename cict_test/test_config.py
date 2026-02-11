"""Unit tests for config module."""
import pytest
import os
from config.settings import Config, DevelopmentConfig, ProductionConfig, get_config


class TestConfig:
    """Test base configuration class."""
    
    def test_default_values(self):
        """Test that default values are set correctly."""
        config = Config()
        assert config.HOST == '0.0.0.0'
        assert config.PORT == 5000
        assert config.DEBUG is False
        assert config.SUBPROCESS_TIMEOUT == 3600
        assert config.HTTP_TIMEOUT == 30
    
    def test_environment_override(self, monkeypatch):
        """Test that environment variables override defaults."""
        monkeypatch.setenv('FLASK_PORT', '8080')
        monkeypatch.setenv('FLASK_DEBUG', 'True')
        
        config = Config()
        assert config.PORT == 8080
        assert config.DEBUG is True
    
    def test_security_defaults(self):
        """Test security-related defaults."""
        config = Config()
        # Should have default (insecure) values
        assert config.SECRET_KEY == 'CHANGE-ME-IN-PRODUCTION'
        assert config.JWT_SECRET == 'CHANGE-ME-IN-PRODUCTION'
    
    def test_path_configuration(self):
        """Test path configuration."""
        config = Config()
        assert 'test_report' in config.TEST_REPORT_BASE
        assert '.cache' in config.CACHE_DIR
        assert 'logs' in config.LOGS_DIR
    
    def test_rate_limiting_defaults(self):
        """Test rate limiting default settings."""
        config = Config()
        assert config.RATE_LIMIT_ENABLED is True
        assert '100000 per day' in config.RATE_LIMIT_DEFAULT
        assert '5 per minute' in config.RATE_LIMIT_TEST_START


class TestDevelopmentConfig:
    """Test development configuration."""
    
    def test_debug_enabled(self):
        """Test that DEBUG is enabled in development."""
        config = DevelopmentConfig()
        assert config.DEBUG is True
        assert config.LOG_LEVEL == 'DEBUG'


class TestProductionConfig:
    """Test production configuration."""
    
    def test_debug_disabled(self):
        """Test that DEBUG is disabled in production."""
        config = ProductionConfig()
        assert config.DEBUG is False
        assert config.LOG_LEVEL == 'INFO'
    
    def test_rate_limiting_enabled(self):
        """Test that rate limiting is enforced in production."""
        config = ProductionConfig()
        assert config.RATE_LIMIT_ENABLED is True


class TestGetConfig:
    """Test configuration factory function."""
    
    def test_default_environment(self, monkeypatch):
        """Test default to development environment."""
        monkeypatch.delenv('FLASK_ENV', raising=False)
        config = get_config()
        assert isinstance(config, DevelopmentConfig)
    
    def test_development_environment(self):
        """Test getting development config."""
        config = get_config('development')
        assert isinstance(config, DevelopmentConfig)
        assert config.DEBUG is True
    
    def test_production_environment(self):
        """Test getting production config."""
        config = get_config('production')
        assert isinstance(config, ProductionConfig)
        assert config.DEBUG is False
    
    def test_testing_environment(self):
        """Test getting testing config."""
        config = get_config('testing')
        assert config.DEBUG is True
        # Testing should have shorter timeouts
        assert config.SUBPROCESS_TIMEOUT == 60
    
    def test_environment_from_env_var(self, monkeypatch):
        """Test reading environment from FLASK_ENV."""
        monkeypatch.setenv('FLASK_ENV', 'production')
        config = get_config()
        assert isinstance(config, ProductionConfig)


# Self-test function
def self_test():
    """Run quick self-test of config module."""
    print("Running config self-test...")
    
    tests = []
    
    # Test default config
    config = Config()
    tests.append(("Default port", config.PORT == 5000, True))
    tests.append(("Default host", config.HOST == '0.0.0.0', True))
    
    # Test development config
    dev_config = DevelopmentConfig()
    tests.append(("Dev debug enabled", dev_config.DEBUG, True))
    tests.append(("Dev log level", dev_config.LOG_LEVEL == 'DEBUG', True))
    
    # Test production config
    prod_config = ProductionConfig()
    tests.append(("Prod debug disabled", not prod_config.DEBUG, True))
    tests.append(("Prod log level", prod_config.LOG_LEVEL == 'INFO', True))
    
    # Test get_config
    config = get_config('development')
    tests.append(("Get dev config", isinstance(config, DevelopmentConfig), True))
    
    passed = 0
    failed = 0
    
    for name, result, expected in tests:
        if result == expected:
            print(f"  ✓ {name}")
            passed += 1
        else:
            print(f"  ✗ {name} (expected {expected}, got {result})")
            failed += 1
    
    print(f"\nResults: {passed} passed, {failed} failed")
    return failed == 0


if __name__ == "__main__":
    success = self_test()
    exit(0 if success else 1)
