"""
Configuration module - Environment-specific settings
"""
import os
from configs.development import DevelopmentConfig
from configs.production import ProductionConfig
from configs.testing import TestingConfig


# Configuration mapping
config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'testing': TestingConfig,
    'default': DevelopmentConfig
}


def get_config(env: str = None):
    """
    Get configuration class for environment
    
    Args:
        env: Environment name (development, production, testing)
            If None, reads from FLASK_ENV environment variable
    
    Returns:
        Configuration class
    
    Examples:
        >>> cfg = get_config('production')
        >>> print(cfg.DEBUG)
        False
    """
    if env is None:
        env = os.getenv('FLASK_ENV', 'development')
    
    return config.get(env, config['default'])


__all__ = [
    'DevelopmentConfig',
    'ProductionConfig',
    'TestingConfig',
    'get_config',
]