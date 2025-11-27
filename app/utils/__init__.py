"""
Utilities - Helper functions and tools
"""
from app.utils.asyncio_compat import run_async
from app.utils.cache import CacheManager
from app.utils.stopwords import get_stopwords, remove_stopwords_optimized
from app.utils.rate_limiter import RateLimiter
from app.utils.profiling import PerformanceProfiler, get_profiler, profile
from app.utils.api_validator import APIValidator, get_api_validator
from app.utils.validators import (
    sanitize_string,
    validate_similarity_input,
    validate_sources
)
from app.utils.logging_config import setup_logging, SanitizingFormatter
from app.utils.html_cleaner import (
    HTMLCleaner,
    clean_html,
    strip_html,
    extract_text_from_html,
    is_safe_html,
    sanitize_for_display
)

__all__ = [
    'run_async',
    'CacheManager',
    'get_stopwords',
    'remove_stopwords_optimized',
    'RateLimiter',
    'PerformanceProfiler',
    'get_profiler',
    'profile',
    'APIValidator',
    'get_api_validator',
    'sanitize_string',
    'validate_similarity_input',
    'validate_sources',
    'setup_logging',
    'SanitizingFormatter',
    'HTMLCleaner',
    'clean_html',
    'strip_html',
    'extract_text_from_html',
    'is_safe_html',
    'sanitize_for_display',
]