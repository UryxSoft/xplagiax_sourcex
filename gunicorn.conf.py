"""
Gunicorn configuration - Ultra-optimized for production
"""
import multiprocessing
import os

# ============ WORKERS ============
# Formula: (2 * CPU cores) + 1
workers = (multiprocessing.cpu_count() * 2) + 1

# ✅ Worker class - gthread es mejor para I/O bound
worker_class = 'gthread'

# ✅ Threads por worker (para APIs externas async)
threads = 4  # workers * threads = alta concurrencia

# ✅ Worker connections
worker_connections = 1000

# ============ TIMEOUTS ============
timeout = 300  # 5 minutos (búsquedas pueden ser largas)
graceful_timeout = 30
keepalive = 5  # Keep-alive para reusar conexiones

# ============ PERFORMANCE ============
# ✅ Pre-load app (comparte memoria entre workers)
preload_app = True

# ✅ Max requests antes de reiniciar worker (evita memory leaks)
max_requests = 1000
max_requests_jitter = 50

# ============ LOGGING ============
accesslog = 'logs/gunicorn_access.log'
errorlog = 'logs/gunicorn_error.log'
loglevel = 'info'

# ✅ Log format con timing
access_log_format = '%(h)s %(l)s %(u)s %(t)s "%(r)s" %(s)s %(b)s "%(f)s" "%(a)s" %(D)sµs'

# ============ BINDING ============
bind = '0.0.0.0:5000'
backlog = 2048  # Cola de conexiones pendientes

# ============ PROCESS NAMING ============
proc_name = 'xplagiax_sourcex'

# ============ WORKER TMP DIR ============
worker_tmp_dir = '/dev/shm'  # ✅ RAM disk (más rápido)

# ============ SERVER HOOKS ============
def on_starting(server):
    """Al iniciar servidor"""
    print("=" * 60)
    print("🚀 Starting xplagiax_sourcex API")
    print("=" * 60)

def when_ready(server):
    """Cuando está listo"""
    print(f"✅ Server ready")
    print(f"   Workers: {workers}")
    print(f"   Threads per worker: {threads}")
    print(f"   Total capacity: {workers * threads} concurrent requests")
    print(f"   Preload: {preload_app}")
    print("=" * 60)

def worker_int(worker):
    """Worker interrupted"""
    print(f"⚠️ Worker {worker.pid} interrupted")

def pre_fork(server, worker):
    """Antes de fork"""
    pass

def post_fork(server, worker):
    """
    Después de fork - optimizaciones por worker
    """
    # ✅ Seeds aleatorios por worker
    import random
    import numpy as np
    random.seed(worker.pid)
    np.random.seed(worker.pid)
    
    print(f"✅ Worker {worker.pid} started")

def pre_exec(server):
    """Antes de exec"""
    print("Preexec: Server is reloading")

def on_exit(server):
    """Al salir"""
    print("👋 Server exiting")