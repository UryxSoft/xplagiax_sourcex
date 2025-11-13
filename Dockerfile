# ====== STAGE 1: Builder ======
FROM python:3.11-slim AS builder

WORKDIR /app

# Instalar dependencias del sistema necesarias para compilación
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

# Copiar solo requirements para aprovechar caché de Docker
COPY requirements.txt .

# Crear virtual environment e instalar dependencias
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Descargar datos NLTK
RUN python -c "import nltk; nltk.download('punkt'); nltk.download('stopwords')"

# ====== STAGE 2: Runtime ======
FROM python:3.11-slim

WORKDIR /app

# Instalar solo dependencias runtime (sin compiladores)
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copiar virtual environment desde builder
COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Copiar datos NLTK
COPY --from=builder /root/nltk_data /root/nltk_data

# Copiar código de la aplicación
COPY config.py .
COPY models.py .
COPY rate_limiter.py .
COPY cache.py .
COPY utils.py .
COPY decorators.py .
COPY searchers.py .
COPY search_service.py .
COPY resources.py .
COPY faiss_service.py .
COPY logging_config.py .
COPY input_validator.py .
COPY api_validator.py .
COPY profiler.py .
COPY app.py .

# Crear directorios necesarios
RUN mkdir -p data logs backups

# Crear usuario no-root (seguridad)
RUN useradd -m -u 1000 appuser && \
    chown -R appuser:appuser /app

USER appuser

# Exponer puerto
EXPOSE 5000

# Variables de entorno
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    REDIS_HOST=redis \
    REDIS_PORT=6379

# Health check
HEALTHCHECK --interval=30s --timeout=10s --retries=3 --start-period=40s \
    CMD curl -f http://localhost:5000/api/health || exit 1

# Comando para producción con gunicorn
CMD ["gunicorn", \
     "--workers", "4", \
     "--bind", "0.0.0.0:5000", \
     "--timeout", "120", \
     "--access-logfile", "-", \
     "--error-logfile", "-", \
     "--log-level", "info", \
     "app:create_app()"]