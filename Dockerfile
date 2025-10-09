FROM python:3.11-slim

WORKDIR /app

# Instalar dependencias del sistema
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

# Copiar requirements
COPY requirements.txt .

# Instalar dependencias Python
RUN pip install --no-cache-dir -r requirements.txt

# Descargar datos NLTK
RUN python -c "import nltk; nltk.download('punkt'); nltk.download('stopwords')"

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
COPY app.py .

# Exponer puerto
EXPOSE 5000

# Variables de entorno
ENV PYTHONUNBUFFERED=1
ENV REDIS_HOST=redis
ENV REDIS_PORT=6379

# Comando para producción con gunicorn
CMD ["gunicorn", "-w", "4", "-b", "0.0.0.0:5000", "--timeout", "120", "app:app"]