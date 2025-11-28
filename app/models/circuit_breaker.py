from enum import Enum
from dataclasses import dataclass
from typing import Dict
import time

class CircuitState(Enum):
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"

@dataclass
class CircuitBreaker:
    failure_threshold: int = 5
    timeout: int = 60
    
    def __post_init__(self):
        self.failure_count = 0
        self.last_failure_time = None
        self.state = CircuitState.CLOSED