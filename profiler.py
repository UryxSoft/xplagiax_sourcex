"""
Sistema de Profiling y Métricas de Performance
"""
import time
import psutil
import tracemalloc
from functools import wraps
from typing import Dict, List, Callable
from dataclasses import dataclass, asdict
from collections import defaultdict
import threading


@dataclass
class PerformanceSnapshot:
    """Snapshot de performance en un momento dado"""
    timestamp: float
    cpu_percent: float
    memory_mb: float
    memory_percent: float
    thread_count: int
    function_name: str
    execution_time_ms: float


class SystemProfiler:
    """
    Profiler de sistema completo
    """
    def __init__(self):
        self.snapshots: List[PerformanceSnapshot] = []
        self.function_stats = defaultdict(lambda: {
            'calls': 0,
            'total_time': 0,
            'avg_time': 0,
            'min_time': float('inf'),
            'max_time': 0
        })
        self.lock = threading.Lock()
        tracemalloc.start()
    
    def profile_function(self, func: Callable) -> Callable:
        """Decorador para perfilar funciones"""
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Snapshot inicial
            start_time = time.time()
            start_memory = tracemalloc.get_traced_memory()[0] / 1024 / 1024  # MB
            cpu_start = psutil.cpu_percent(interval=None)
            
            # Ejecutar función
            result = func(*args, **kwargs)
            
            # Snapshot final
            end_time = time.time()
            end_memory = tracemalloc.get_traced_memory()[0] / 1024 / 1024
            cpu_end = psutil.cpu_percent(interval=None)
            
            execution_time = (end_time - start_time) * 1000  # ms
            memory_used = end_memory - start_memory
            
            # Registrar snapshot
            snapshot = PerformanceSnapshot(
                timestamp=end_time,
                cpu_percent=cpu_end,
                memory_mb=end_memory,
                memory_percent=psutil.virtual_memory().percent,
                thread_count=threading.active_count(),
                function_name=func.__name__,
                execution_time_ms=round(execution_time, 2)
            )
            
            with self.lock:
                self.snapshots.append(snapshot)
                
                # Actualizar estadísticas
                stats = self.function_stats[func.__name__]
                stats['calls'] += 1
                stats['total_time'] += execution_time
                stats['avg_time'] = stats['total_time'] / stats['calls']
                stats['min_time'] = min(stats['min_time'], execution_time)
                stats['max_time'] = max(stats['max_time'], execution_time)
            
            return result
        
        return wrapper
    
    def get_system_stats(self) -> Dict:
        """Retorna estadísticas del sistema"""
        memory = psutil.virtual_memory()
        cpu_count = psutil.cpu_count()
        
        return {
            "cpu": {
                "percent": psutil.cpu_percent(interval=1),
                "count": cpu_count,
                "per_core": psutil.cpu_percent(interval=1, percpu=True)
            },
            "memory": {
                "total_mb": memory.total / 1024 / 1024,
                "used_mb": memory.used / 1024 / 1024,
                "available_mb": memory.available / 1024 / 1024,
                "percent": memory.percent
            },
            "threads": {
                "active": threading.active_count()
            }
        }
    
    def get_function_stats(self) -> Dict:
        """Retorna estadísticas de funciones"""
        with self.lock:
            return {
                func_name: {
                    'calls': stats['calls'],
                    'avg_time_ms': round(stats['avg_time'], 2),
                    'min_time_ms': round(stats['min_time'], 2) if stats['min_time'] != float('inf') else 0,
                    'max_time_ms': round(stats['max_time'], 2),
                    'total_time_ms': round(stats['total_time'], 2)
                }
                for func_name, stats in self.function_stats.items()
            }
    
    def get_bottlenecks(self, top_n: int = 5) -> List[Dict]:
        """Identifica los principales cuellos de botella"""
        with self.lock:
            sorted_funcs = sorted(
                self.function_stats.items(),
                key=lambda x: x[1]['avg_time'],
                reverse=True
            )
            
            return [
                {
                    'function': name,
                    'avg_time_ms': round(stats['avg_time'], 2),
                    'calls': stats['calls'],
                    'impact_score': round(stats['avg_time'] * stats['calls'], 2)
                }
                for name, stats in sorted_funcs[:top_n]
            ]
    
    def generate_report(self) -> Dict:
        """Genera reporte completo de performance"""
        return {
            "system": self.get_system_stats(),
            "functions": self.get_function_stats(),
            "bottlenecks": self.get_bottlenecks(),
            "snapshots_count": len(self.snapshots),
            "recommendations": self._generate_recommendations()
        }
    
    def _generate_recommendations(self) -> List[str]:
        """Genera recomendaciones de optimización"""
        recommendations = []
        system_stats = self.get_system_stats()
        
        # Recomendaciones de CPU
        if system_stats['cpu']['percent'] > 80:
            recommendations.append("⚠️ Alto uso de CPU (>80%). Considerar: 1) Reducir workers, 2) Implementar caché, 3) Optimizar algoritmos")
        
        # Recomendaciones de memoria
        if system_stats['memory']['percent'] > 85:
            recommendations.append("⚠️ Alta memoria (>85%). Considerar: 1) Usar FAISS IVF+PQ, 2) Reducir batch size, 3) Liberar caché")
        
        # Recomendaciones de funciones
        bottlenecks = self.get_bottlenecks(3)
        if bottlenecks and bottlenecks[0]['avg_time_ms'] > 1000:
            func_name = bottlenecks[0]['function']
            recommendations.append(f"🐌 Función lenta detectada: {func_name} ({bottlenecks[0]['avg_time_ms']}ms). Optimizar urgentemente.")
        
        if not recommendations:
            recommendations.append("✅ Sistema operando en rangos óptimos")
        
        return recommendations
    
    def clear_snapshots(self):
        """Limpia snapshots antiguos"""
        with self.lock:
            self.snapshots.clear()


# Instancia global
_profiler: SystemProfiler = SystemProfiler()


def get_profiler() -> SystemProfiler:
    """Retorna instancia global del profiler"""
    return _profiler


def profile(func: Callable) -> Callable:
    """Decorador rápido para perfilar funciones"""
    return get_profiler().profile_function(func)