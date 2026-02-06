"""Configuration management for NUI application.

Environment-based configuration supporting dev/staging/production.
"""
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Optional


@dataclass
class Config:
    """Base configuration class with environment variable support."""
    
    # Flask Application Settings
    HOST: str = '0.0.0.0'
    PORT: int = 5000
    DEBUG: bool = False
    
    # Security Settings
    SECRET_KEY: str = 'CHANGE-ME-IN-PRODUCTION'
    JWT_SECRET: str = 'CHANGE-ME-IN-PRODUCTION'
    JWT_EXPIRATION_HOURS: int = 24
    
    # Path Configuration
    BASE_DIR: Path = Path(os.getcwd())
    TEST_REPORT_BASE: str = os.path.join(os.getcwd(), 'test_report')
    CACHE_DIR: str = os.path.join(os.getcwd(), '.cache')
    LOGS_DIR: str = os.path.join(os.getcwd(), 'logs')
    
    # Timeout Settings
    SUBPROCESS_TIMEOUT: int = 3600  # 1 hour
    HTTP_TIMEOUT: int = 30
    
    # Monitoring Settings
    MONITOR_INTERVAL: float = 30.0
    TRANSCEIVER_MONITOR_INTERVAL: float = 30.0
    LAB_MONITOR_STATUS_INTERVAL: float = 30.0
    LAB_MONITOR_REPORT_INTERVAL: float = 86400.0  # 24 hours
    
    # Rate Limiting
    RATE_LIMIT_ENABLED: bool = True
    RATE_LIMIT_DEFAULT: str = '200 per day'
    RATE_LIMIT_TEST_START: str = '5 per minute'
    
    # CORS Settings
    CORS_ENABLED: bool = False
    CORS_ORIGINS: str = '*'
    
    # Logging
    LOG_LEVEL: str = 'INFO'
    
    # Platform Cache
    PLATFORM_CACHE_FILE: str = '.platform_cache'
    
    def __post_init__(self):
        """Validate configuration after initialization."""
        # Load environment overrides at instance creation time.
        self.HOST = os.getenv('FLASK_HOST', self.HOST)
        self.PORT = int(os.getenv('FLASK_PORT', str(self.PORT)))
        self.DEBUG = os.getenv('FLASK_DEBUG', str(self.DEBUG)).lower() in ('true', '1', 'yes')

        self.SECRET_KEY = os.getenv('SECRET_KEY', self.SECRET_KEY)
        self.JWT_SECRET = os.getenv('JWT_SECRET', self.JWT_SECRET)
        self.JWT_EXPIRATION_HOURS = int(os.getenv('JWT_EXPIRATION_HOURS', str(self.JWT_EXPIRATION_HOURS)))

        base_dir = Path(os.getenv('BASE_DIR', os.getcwd()))
        self.BASE_DIR = base_dir
        self.TEST_REPORT_BASE = os.getenv('TEST_REPORT_BASE', str(base_dir / 'test_report'))
        self.CACHE_DIR = os.getenv('CACHE_DIR', str(base_dir / '.cache'))
        self.LOGS_DIR = os.getenv('LOGS_DIR', str(base_dir / 'logs'))

        self.SUBPROCESS_TIMEOUT = int(os.getenv('SUBPROCESS_TIMEOUT', str(self.SUBPROCESS_TIMEOUT)))
        self.HTTP_TIMEOUT = int(os.getenv('HTTP_TIMEOUT', str(self.HTTP_TIMEOUT)))

        self.MONITOR_INTERVAL = float(os.getenv('MONITOR_INTERVAL', str(self.MONITOR_INTERVAL)))
        self.TRANSCEIVER_MONITOR_INTERVAL = float(
            os.getenv('TRANSCEIVER_MONITOR_INTERVAL', str(self.TRANSCEIVER_MONITOR_INTERVAL))
        )
        self.LAB_MONITOR_STATUS_INTERVAL = float(
            os.getenv('LAB_MONITOR_STATUS_INTERVAL', str(self.LAB_MONITOR_STATUS_INTERVAL))
        )
        self.LAB_MONITOR_REPORT_INTERVAL = float(
            os.getenv('LAB_MONITOR_REPORT_INTERVAL', str(self.LAB_MONITOR_REPORT_INTERVAL))
        )

        self.RATE_LIMIT_ENABLED = os.getenv('RATE_LIMIT_ENABLED', str(self.RATE_LIMIT_ENABLED)).lower() in (
            'true', '1', 'yes'
        )
        self.RATE_LIMIT_DEFAULT = os.getenv('RATE_LIMIT_DEFAULT', self.RATE_LIMIT_DEFAULT)
        self.RATE_LIMIT_TEST_START = os.getenv('RATE_LIMIT_TEST_START', self.RATE_LIMIT_TEST_START)

        self.CORS_ENABLED = os.getenv('CORS_ENABLED', str(self.CORS_ENABLED)).lower() in ('true', '1', 'yes')
        self.CORS_ORIGINS = os.getenv('CORS_ORIGINS', self.CORS_ORIGINS)

        self.LOG_LEVEL = os.getenv('LOG_LEVEL', self.LOG_LEVEL).upper()

        # Warn about insecure defaults in production
        if not self.DEBUG:
            if self.SECRET_KEY == 'CHANGE-ME-IN-PRODUCTION':
                print('WARNING: Using default SECRET_KEY in production mode!')
            if self.JWT_SECRET == 'CHANGE-ME-IN-PRODUCTION':
                print('WARNING: Using default JWT_SECRET in production mode!')


@dataclass
class DevelopmentConfig(Config):
    """Development environment configuration."""
    DEBUG: bool = True
    LOG_LEVEL: str = 'DEBUG'


@dataclass
class ProductionConfig(Config):
    """Production environment configuration."""
    DEBUG: bool = False
    LOG_LEVEL: str = 'INFO'
    RATE_LIMIT_ENABLED: bool = True


@dataclass
class TestingConfig(Config):
    """Testing environment configuration."""
    DEBUG: bool = True
    LOG_LEVEL: str = 'DEBUG'
    SUBPROCESS_TIMEOUT: int = 60  # Shorter timeout for tests


# Environment configuration mapping
_config_map = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'testing': TestingConfig,
}


def get_config(env: Optional[str] = None) -> Config:
    """Get configuration for the specified environment.
    
    Args:
        env: Environment name (development, production, testing)
             If None, reads from FLASK_ENV environment variable
    
    Returns:
        Config: Configuration instance
    """
    if env is None:
        env = os.getenv('FLASK_ENV', 'development').lower()
    
    config_class = _config_map.get(env, Config)
    return config_class()
