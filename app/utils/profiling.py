"""
Performance Profiling Utilities
"""
import time
import logging
from functools import wraps
from typing import Dict, Any
import psutil

logger = logging.getLogger(__name__)


class PerformanceProfiler:
    """Track performance metrics"""
    
    def __init__(self):
        self.metrics: Dict[str, list] = {}
    
    def record(self, operation: str, duration: float):
        """Record operation duration"""
        if operation not in self.metrics:
            self.metrics[operation] = []
        
        self.metrics[operation].append(duration)
    
    def get_stats(self, operation: str) -> Dict[str, Any]:
        """Get statistics for an operation"""
        if operation not in self.metrics or not self.metrics[operation]:
            return {}
        
        durations = self.metrics[operation]
        
        return {
            'count': len(durations),
            'total': sum(durations),
            'avg': sum(durations) / len(durations),
            'min': min(durations),
            'max': max(durations)
        }
    
    def generate_report(self) -> Dict[str, Any]:
        """Generate full performance report"""
        report = {
            'operations': {},
            'system': self._get_system_stats()
        }
        
        for operation in self.metrics:
            report['operations'][operation] = self.get_stats(operation)
        
        return report
    
    def _get_system_stats(self) -> Dict[str, Any]:
        """Get system resource stats"""
        try:
            cpu_percent = psutil.cpu_percent(interval=0.1)
            memory = psutil.virtual_memory()
            
            return {
                'cpu': {
                    'percent': cpu_percent,
                    'count': psutil.cpu_count()
                },
                'memory': {
                    'total_mb': memory.total / (1024 * 1024),
                    'used_mb': memory.used / (1024 * 1024),
                    'percent': memory.percent
                }
            }
        
        except Exception as e:
            logger.error(f"Error getting system stats: {e}")
            return {}


# Global profiler instance
_profiler = PerformanceProfiler()


def get_profiler() -> PerformanceProfiler:
    """Get global profiler instance"""
    return _profiler


def profile(func):
    """Decorator to profile function execution time"""
    @wraps(func)
    def wrapper(*args, **kwargs):
        start = time.time()
        result = func(*args, **kwargs)
        duration = time.time() - start
        
        _profiler.record(func.__name__, duration)
        
        logger.debug(f"{func.__name__} took {duration:.3f}s")
        
        return result
    
    return wrapper