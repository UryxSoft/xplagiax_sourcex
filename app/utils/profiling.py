"""
Performance Profiling Utilities
"""
import time
import logging
from functools import wraps
from typing import Dict, Any, List
import psutil

logger = logging.getLogger(__name__)


class PerformanceProfiler:
    """
    Track performance metrics for operations
    
    Tracks:
    - Operation execution times
    - Call counts
    - System resources (CPU, memory)
    """
    
    def __init__(self):
        """Initialize performance profiler"""
        self.metrics: Dict[str, List[float]] = {}
        self.call_counts: Dict[str, int] = {}
    
    def record(self, operation: str, duration: float):
        """
        Record operation duration
        
        Args:
            operation: Operation name
            duration: Duration in seconds
        """
        if operation not in self.metrics:
            self.metrics[operation] = []
            self.call_counts[operation] = 0
        
        self.metrics[operation].append(duration)
        self.call_counts[operation] += 1
    
    def get_stats(self, operation: str) -> Dict[str, Any]:
        """
        Get statistics for an operation
        
        Args:
            operation: Operation name
        
        Returns:
            Dict with statistics
        """
        if operation not in self.metrics or not self.metrics[operation]:
            return {}
        
        durations = self.metrics[operation]
        
        return {
            'count': len(durations),
            'total_seconds': sum(durations),
            'avg_seconds': sum(durations) / len(durations),
            'min_seconds': min(durations),
            'max_seconds': max(durations),
            'last_seconds': durations[-1] if durations else 0
        }
    
    def generate_report(self) -> Dict[str, Any]:
        """
        Generate full performance report
        
        Returns:
            Dict with all metrics and system stats
        """
        report = {
            'operations': {},
            'system': self._get_system_stats(),
            'recommendations': []
        }
        
        for operation in self.metrics:
            stats = self.get_stats(operation)
            report['operations'][operation] = stats
            
            # Add recommendations
            if stats.get('avg_seconds', 0) > 1.0:
                report['recommendations'].append(
                    f"⚠️ {operation} is slow (avg: {stats['avg_seconds']:.2f}s)"
                )
        
        return report
    
    def _get_system_stats(self) -> Dict[str, Any]:
        """
        Get system resource statistics
        
        Returns:
            Dict with CPU and memory stats
        """
        try:
            cpu_percent = psutil.cpu_percent(interval=0.1)
            memory = psutil.virtual_memory()
            
            return {
                'cpu': {
                    'percent': cpu_percent,
                    'count': psutil.cpu_count(),
                    'status': 'high' if cpu_percent > 80 else 'normal'
                },
                'memory': {
                    'total_mb': round(memory.total / (1024 * 1024), 2),
                    'used_mb': round(memory.used / (1024 * 1024), 2),
                    'available_mb': round(memory.available / (1024 * 1024), 2),
                    'percent': memory.percent,
                    'status': 'high' if memory.percent > 80 else 'normal'
                }
            }
        
        except Exception as e:
            logger.error(f"Error getting system stats: {e}")
            return {}
    
    def reset(self):
        """Reset all metrics"""
        self.metrics.clear()
        self.call_counts.clear()
        logger.debug("Performance metrics reset")


# Global profiler instance
_profiler = PerformanceProfiler()


def get_profiler() -> PerformanceProfiler:
    """
    Get global profiler instance
    
    Returns:
        PerformanceProfiler singleton
    """
    return _profiler


def profile(func):
    """
    Decorator to profile function execution time
    
    Examples:
        >>> @profile
        ... def slow_function():
        ...     time.sleep(1)
        ...     return "done"
        >>> 
        >>> result = slow_function()
        >>> # Logs: "slow_function took 1.000s"
    """
    @wraps(func)
    def wrapper(*args, **kwargs):
        start = time.time()
        result = func(*args, **kwargs)
        duration = time.time() - start
        
        _profiler.record(func.__name__, duration)
        
        if duration > 0.5:  # Log slow operations
            logger.warning(f"{func.__name__} took {duration:.3f}s")
        else:
            logger.debug(f"{func.__name__} took {duration:.3f}s")
        
        return result
    
    return wrapper


def profile_async(func):
    """
    Decorator to profile async function execution time
    
    Examples:
        >>> @profile_async
        ... async def async_operation():
        ...     await asyncio.sleep(1)
        ...     return "done"
    """
    @wraps(func)
    async def wrapper(*args, **kwargs):
        start = time.time()
        result = await func(*args, **kwargs)
        duration = time.time() - start
        
        _profiler.record(func.__name__, duration)
        
        if duration > 0.5:
            logger.warning(f"{func.__name__} took {duration:.3f}s")
        else:
            logger.debug(f"{func.__name__} took {duration:.3f}s")
        
        return result
    
    return wrapper