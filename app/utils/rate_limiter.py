"""
Rate Limiter - Control API request rates
"""
import time
import logging
from typing import Dict
from collections import defaultdict

logger = logging.getLogger(__name__)


class RateLimiter:
    """
    Simple in-memory rate limiter
    
    Uses sliding window algorithm
    """
    
    def __init__(self, max_requests: int = 5, window_seconds: int = 60):
        """
        Initialize rate limiter
        
        Args:
            max_requests: Maximum requests allowed in window
            window_seconds: Time window in seconds
        
        Examples:
            >>> limiter = RateLimiter(max_requests=10, window_seconds=60)
            >>> # Allow 10 requests per minute
        """
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.requests: Dict[str, list] = defaultdict(list)
    
    async def check_limit(self, key: str) -> bool:
        """
        Check if request is allowed
        
        Args:
            key: Rate limit key (e.g., source name, user ID)
        
        Returns:
            True if allowed, False if rate limited
        
        Examples:
            >>> limiter = RateLimiter(max_requests=2, window_seconds=10)
            >>> await limiter.check_limit("user_123")
            True
            >>> await limiter.check_limit("user_123")
            True
            >>> await limiter.check_limit("user_123")
            False  # Rate limited
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
                f"Rate limit exceeded for '{key}': "
                f"{len(self.requests[key])}/{self.max_requests} in {self.window_seconds}s"
            )
            return False
        
        # Add current request
        self.requests[key].append(current_time)
        return True
    
    async def reset(self, key: Optional[str] = None):
        """
        Reset rate limiter
        
        Args:
            key: Specific key to reset (None = reset all)
        """
        if key:
            self.requests[key] = []
            logger.debug(f"Rate limit reset for '{key}'")
        else:
            self.requests.clear()
            logger.debug("All rate limits reset")
    
    def get_remaining(self, key: str) -> int:
        """
        Get remaining requests for key
        
        Args:
            key: Rate limit key
        
        Returns:
            Number of requests remaining
        """
        current_time = time.time()
        
        # Clean old requests
        self.requests[key] = [
            t for t in self.requests[key]
            if current_time - t < self.window_seconds
        ]
        
        return max(0, self.max_requests - len(self.requests[key]))
    
    def get_reset_time(self, key: str) -> float:
        """
        Get time until rate limit resets
        
        Args:
            key: Rate limit key
        
        Returns:
            Seconds until reset (0 if not limited)
        """
        if not self.requests[key]:
            return 0.0
        
        oldest_request = min(self.requests[key])
        reset_time = oldest_request + self.window_seconds
        current_time = time.time()
        
        return max(0.0, reset_time - current_time)


# Optional: Import statement for typing
from typing import Optional