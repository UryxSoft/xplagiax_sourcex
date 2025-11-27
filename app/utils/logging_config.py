"""
Logging Configuration - Setup structured logging
"""
import logging
import sys
import re
from typing import Optional
from logging.handlers import RotatingFileHandler


class SanitizingFormatter(logging.Formatter):
    """
    Custom formatter that sanitizes sensitive data from logs
    
    Removes:
    - API keys
    - Passwords
    - Tokens
    - Email addresses (optional)
    """
    
    # Patterns to sanitize
    PATTERNS = [
        (re.compile(r'(api[_-]?key["\']?\s*[:=]\s*["\']?)([^"\'}\s]+)', re.IGNORECASE), r'\1***REDACTED***'),
        (re.compile(r'(bearer\s+)([^\s]+)', re.IGNORECASE), r'\1***REDACTED***'),
        (re.compile(r'(password["\']?\s*[:=]\s*["\']?)([^"\'}\s]+)', re.IGNORECASE), r'\1***REDACTED***'),
        (re.compile(r'(token["\']?\s*[:=]\s*["\']?)([^"\'}\s]+)', re.IGNORECASE), r'\1***REDACTED***'),
        (re.compile(r'(secret["\']?\s*[:=]\s*["\']?)([^"\'}\s]+)', re.IGNORECASE), r'\1***REDACTED***'),
    ]
    
    def format(self, record: logging.LogRecord) -> str:
        """
        Format log record and sanitize sensitive data
        
        Args:
            record: Log record
        
        Returns:
            Formatted and sanitized log message
        """
        # Format the message
        message = super().format(record)
        
        # Sanitize patterns
        for pattern, replacement in self.PATTERNS:
            message = pattern.sub(replacement, message)
        
        return message


def setup_logging(
    level: str = "INFO",
    log_file: Optional[str] = None,
    max_bytes: int = 10 * 1024 * 1024,  # 10MB
    backup_count: int = 5
):
    """
    Setup application logging
    
    Args:
        level: Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_file: Path to log file (None = console only)
        max_bytes: Max size of log file before rotation
        backup_count: Number of backup files to keep
    
    Examples:
        >>> setup_logging(level="DEBUG", log_file="logs/app.log")
        >>> # Logs to both console and file
    """
    # Convert level string to logging constant
    numeric_level = getattr(logging, level.upper(), logging.INFO)
    
    # Create formatter
    formatter = SanitizingFormatter(
        fmt='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # Get root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(numeric_level)
    
    # Remove existing handlers
    root_logger.handlers.clear()
    
    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(numeric_level)
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)
    
    # File handler (if specified)
    if log_file:
        try:
            import os
            os.makedirs(os.path.dirname(log_file), exist_ok=True)
            
            file_handler = RotatingFileHandler(
                log_file,
                maxBytes=max_bytes,
                backupCount=backup_count
            )
            file_handler.setLevel(numeric_level)
            file_handler.setFormatter(formatter)
            root_logger.addHandler(file_handler)
            
            root_logger.info(f"Logging to file: {log_file}")
        
        except Exception as e:
            root_logger.error(f"Failed to setup file logging: {e}")
    
    # Silence noisy loggers
    logging.getLogger('urllib3').setLevel(logging.WARNING)
    logging.getLogger('httpx').setLevel(logging.WARNING)
    logging.getLogger('httpcore').setLevel(logging.WARNING)
    
    root_logger.info(f"✅ Logging configured: level={level}")