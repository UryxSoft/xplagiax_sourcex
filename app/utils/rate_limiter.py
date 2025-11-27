"""
Rate Limiter - Control API request rates
"""
import time
import logging
from typing import Dict
from collections import defaultdict

logger = logging.getLogger(__name__)


class RateLimiter:
    """Simple in-memory rate limiter"""
    
    def __init__(self, max_requests: int = 5, window_seconds: int = 60):
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.requests: Dict[str, list] = defaultdict(list)
    
    async def check_limit(self, key: str) -> bool:
        """
        Check if request is allowed
        
        Args:
            key: Rate limit key (e.g., source name)
        
        Returns:
            True if allowed, False if rate limited
        """
        current_time = time.time()
        
        # Remove old requests outside the window
        self.requests[key] = [
            t for t in self.requests[key]
            if current_time - t < self.window_seconds
        ]
        
        # Check if limit exceeded
        if len(self.requests[key]) >= self.max_requests:
            logger.warning(
                f"Rate limit exceeded for {key}: "
                f"{len(self.requests[key])}/{self.max_requests}"
            )
            return False
        
        # Add current request
        self.requests[key].append(current_time)
        return True
    
    async def reset(self, key: Optional[str] = None):
        """Reset rate limiter"""
        if key:
            self.requests[key] = []
        else:
            self.requests.clear()