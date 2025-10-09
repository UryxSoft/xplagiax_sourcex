"""
Modelos de datos y estructuras
"""
import time
from dataclasses import dataclass
from enum import Enum
from typing import Dict, Any

from config import Config


@dataclass
class SearchResult:
    fuente: str
    texto_original: str
    texto_encontrado: str
    porcentaje_match: float
    documento_coincidente: str
    autor: str
    type_document: str


class CircuitState(Enum):
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


@dataclass
class CircuitBreaker:
    """Circuit breaker para APIs lentas/caídas"""
    failure_count: int = 0
    last_failure_time: float = 0
    state: CircuitState = CircuitState.CLOSED
    
    def record_failure(self):
        self.failure_count += 1
        self.last_failure_time = time.time()
        if self.failure_count >= Config.CIRCUIT_FAILURE_THRESHOLD:
            self.state = CircuitState.OPEN
    
    def record_success(self):
        self.failure_count = 0
        self.state = CircuitState.CLOSED
    
    def can_attempt(self) -> bool:
        if self.state == CircuitState.CLOSED:
            return True
        if self.state == CircuitState.OPEN:
            if time.time() - self.last_failure_time > Config.CIRCUIT_TIMEOUT:
                self.state = CircuitState.HALF_OPEN
                return True
        return self.state == CircuitState.HALF_OPEN


class PerformanceMetrics:
    """Tracking de métricas de performance"""
    def __init__(self):
        self.request_count = 0
        self.total_latency = 0.0
        self.error_count = 0
        self.cache_hits = 0
        self.cache_misses = 0
    
    def record_request(self, latency: float, error: bool = False):
        self.request_count += 1
        self.total_latency += latency
        if error:
            self.error_count += 1
    
    def record_cache(self, hit: bool):
        if hit:
            self.cache_hits += 1
        else:
            self.cache_misses += 1
    
    def get_stats(self) -> Dict[str, Any]:
        avg_latency = self.total_latency / self.request_count if self.request_count > 0 else 0
        cache_rate = self.cache_hits / (self.cache_hits + self.cache_misses) if (self.cache_hits + self.cache_misses) > 0 else 0
        
        return {
            "requests": self.request_count,
            "avg_latency_ms": round(avg_latency * 1000, 2),
            "error_rate": round(self.error_count / self.request_count * 100, 2) if self.request_count > 0 else 0,
            "cache_hit_rate": round(cache_rate * 100, 2),
        }