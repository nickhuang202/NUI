"""Unit tests for logging configuration."""
import pytest
import logging
import os
import tempfile
from pathlib import Path
from config.logging_config import setup_logging, get_logger


class TestSetupLogging:
    """Test logging setup functionality."""
    
    def test_setup_without_app(self):
        """Test logging setup without Flask app."""
        logger = setup_logging()
        assert logger is not None
        assert isinstance(logger, logging.Logger)
    
    def test_log_level_from_env(self, monkeypatch):
        """Test log level from environment variable."""
        monkeypatch.setenv('LOG_LEVEL', 'WARNING')
        logger = setup_logging()
        assert logger.level == logging.WARNING
    
    def test_log_level_custom(self):
        """Test custom log level."""
        logger = setup_logging(log_level=logging.ERROR)
        assert logger.level == logging.ERROR
    
    def test_log_directory_created(self):
        """Test that log directory is created."""
        log_dir = Path(os.getcwd()) / 'logs'
        setup_logging()
        assert log_dir.exists()
        assert log_dir.is_dir()
    
    def test_handlers_configured(self):
        """Test that handlers are properly configured."""
        logger = setup_logging()
        root_logger = logging.getLogger()
        
        # Should have file and console handlers
        assert len(root_logger.handlers) >= 2
        
        # Check handler types
        handler_types = [type(h).__name__ for h in root_logger.handlers]
        assert 'RotatingFileHandler' in handler_types
        assert 'StreamHandler' in handler_types


class TestGetLogger:
    """Test logger retrieval."""
    
    def test_get_logger_by_name(self):
        """Test getting logger by name."""
        logger = get_logger('test_module')
        assert logger is not None
        assert logger.name == 'test_module'
    
    def test_logger_inherits_config(self):
        """Test that logger inherits root config."""
        setup_logging(log_level=logging.WARNING)
        logger = get_logger('test_module')
        
        # Logger should inherit root level
        assert logger.getEffectiveLevel() == logging.WARNING


# Self-test function
def self_test():
    """Run quick self-test of logging configuration."""
    print("Running logging self-test...")
    
    tests = []
    
    # Test basic setup
    logger = setup_logging()
    tests.append(("Logger created", logger is not None, True))
    tests.append(("Logger is Logger instance", isinstance(logger, logging.Logger), True))
    
    # Test log directory
    log_dir = Path(os.getcwd()) / 'logs'
    tests.append(("Log directory exists", log_dir.exists(), True))
    
    # Test getting named logger
    named_logger = get_logger('test')
    tests.append(("Named logger created", named_logger is not None, True))
    tests.append(("Named logger has correct name", named_logger.name == 'test', True))
    
    # Test actual logging (should not raise)
    try:
        logger.info("Test info message")
        logger.warning("Test warning message")
        logger.error("Test error message")
        tests.append(("Logging works", True, True))
    except Exception as e:
        tests.append(("Logging works", False, True))
    
    # Check that log file was created
    log_file = log_dir / 'nui.log'
    tests.append(("Log file created", log_file.exists(), True))
    
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
    
    # Show log file location
    if log_file.exists():
        print(f"\nLog file created at: {log_file}")
        print(f"Log file size: {log_file.stat().st_size} bytes")
    
    return failed == 0


if __name__ == "__main__":
    success = self_test()
    exit(0 if success else 1)
