# xplagiax_sourcex
data source research services

# 1. Construir
docker-compose up --build

# 2. Probar
curl -X POST http://localhost:5000/api/similarity-search \
  -H "Content-Type: application/json" \
  -d '{
    "data": [
      "machine learning",
      "en",
      [
        ["page1", "para1", "Neural networks are computational models"],
        ["page1", "para2", "Deep learning uses multiple layers"]
      ]
    ]
  }'

# 3. Ver estadísticas FAISS
curl http://localhost:5000/api/faiss/stats


# Búsqueda básica
curl -X POST http://localhost:5000/api/similarity-search \
  -H "Content-Type: application/json" \
  -d '{
    "data": [
      "machine learning",
      "en",
      [
        ["page1", "para1", "Neural networks are computational models inspired by biological neurons"],
        ["page1", "para2", "Deep learning uses multiple layers to extract features"],
        ["page2", "para1", "Convolutional networks excel at image recognition tasks"]
      ]
    ]
  }'

# Búsqueda con fuentes específicas
curl -X POST http://localhost:5000/api/similarity-search \
  -H "Content-Type: application/json" \
  -d '{
    "data": [
      "artificial intelligence",
      "en",
      [
        ["page1", "para1", "AI systems can learn from data"]
      ]
    ],
    "sources": ["semantic_scholar", "arxiv", "pubmed"]
  }'

# Búsqueda sin FAISS (solo APIs)
curl -X POST http://localhost:5000/api/similarity-search \
  -H "Content-Type: application/json" \
  -d '{
    "data": [
      "quantum computing",
      "en",
      [
        ["page1", "para1", "Quantum computers use qubits"]
      ]
    ],
    "use_faiss": false
  }'

# Búsqueda en español
curl -X POST http://localhost:5000/api/similarity-search \
  -H "Content-Type: application/json" \
  -d '{
    "data": [
      "aprendizaje automático",
      "es",
      [
        ["pagina1", "parrafo1", "Las redes neuronales son modelos computacionales"],
        ["pagina1", "parrafo2", "El aprendizaje profundo utiliza múltiples capas"]
      ]
    ]
  }'


# Búsqueda simple
curl -X POST http://localhost:5000/api/faiss/search \
  -H "Content-Type: application/json" \
  -d '{
    "query": "deep learning neural networks"
  }'

# Búsqueda con parámetros personalizados
curl -X POST http://localhost:5000/api/faiss/search \
  -H "Content-Type: application/json" \
  -d '{
    "query": "convolutional neural networks image recognition",
    "k": 20,
    "threshold": 0.75
  }'

# 🔬 xplagiax_sourcex - Academic Search Service

Sistema de búsqueda académica con similitud semántica utilizando FAISS, múltiples APIs y machine learning.

## 🚀 Inicio Rápido

### 1. Configuración

```bash
# Clonar repositorio
git clone <repo-url>
cd xplagiax_sourcex

# Copiar configuración
cp .env.example .env

# Generar secretos (Linux/Mac)
echo "REDIS_PASSWORD=$(openssl rand -base64 32)" >> .env
echo "FLASK_SECRET_KEY=$(openssl rand -base64 48)" >> .env

# Editar .env con tu configuración
nano .env
```

### 2. Construir y Ejecutar

```bash
# Construir e iniciar servicios
docker-compose up --build

# En segundo plano
docker-compose up -d

# Ver logs
docker-compose logs -f app
```

### 3. Verificar Estado

```bash
# Health check
curl http://localhost:5000/api/health

# Estadísticas FAISS
curl http://localhost:5000/api/faiss/stats
```

## 📊 Arquitectura

```
┌─────────────┐
│   Cliente   │
└──────┬──────┘
       │
       ▼
┌─────────────────────────┐
│   Flask + Gunicorn      │
│   (4 workers)           │
└──────┬──────────────────┘
       │
       ├──► Redis (Caché)
       ├──► FAISS (Búsqueda vectorial)
       └──► APIs Externas:
            • Crossref
            • PubMed
            • Semantic Scholar
            • arXiv
            • OpenAlex
            • Europe PMC
            • DOAJ
            • Zenodo
```

## 🔌 Endpoints Principales

### Búsqueda de Similitud

```bash
POST /api/similarity-search
Content-Type: application/json

{
  "data": [
    "machine learning",
    "en",
    [
      ["page1", "para1", "Neural networks are computational models"],
      ["page1", "para2", "Deep learning uses multiple layers"]
    ]
  ],
  "use_faiss": true,
  "sources": ["semantic_scholar", "arxiv"]
}
```

**Respuesta:**

```json
{
  "results": [
    {
      "fuente": "semantic_scholar",
      "texto_original": "Neural networks are...",
      "texto_encontrado": "This paper presents...",
      "porcentaje_match": 89.2,
      "documento_coincidente": "Deep Learning Book",
      "autor": "Goodfellow",
      "type_document": "article"
    }
  ],
  "count": 10,
  "processed_texts": 2,
  "faiss_enabled": true
}
```

### FAISS

```bash
# Estadísticas
GET /api/faiss/stats

# Búsqueda directa
POST /api/faiss/search
{
  "query": "deep learning neural networks",
  "k": 20,
  "threshold": 0.75
}

# Guardar índice
POST /api/faiss/save

# Backup
POST /api/faiss/backup

# Limpiar
POST /api/faiss/clear
```

### Monitoreo

```bash
# Health check
GET /api/health

# Métricas Prometheus
GET /api/metrics

# Diagnóstico completo
GET /api/diagnostics/full

# Validar APIs externas
POST /api/validate-apis

# Profiler
GET /api/profiler/stats
GET /api/profiler/bottlenecks?top=10
```

### Administración

```bash
# Limpiar caché
POST /api/cache/clear

# Reiniciar rate limits
POST /api/reset-limits

# Benchmark
POST /api/benchmark
{
  "num_texts": 50
}
```

## 🔐 Seguridad

### Rate Limiting

- **Global**: 200 req/día, 50 req/hora por IP
- **Búsqueda**: 10 req/minuto por IP

### Validación de Entrada

- Sanitización automática de HTML/XSS
- Límites de longitud
- Validación de tipos

### Autenticación Redis

Configurar contraseña en `.env`:

```bash
REDIS_PASSWORD=your_strong_password
```

### CORS

Configurar dominios permitidos:

```bash
ALLOWED_ORIGINS=https://domain1.com,https://domain2.com
```

## 📈 Optimización

### Estrategias FAISS

| Tamaño | Estrategia | Velocidad | Memoria | Recall |
|--------|------------|-----------|---------|--------|
| <10k | Flat | ⚡⚡⚡ | 🔴🔴🔴 | 100% |
| 10k-100k | HNSW | ⚡⚡ | 🔴🔴 | 95% |
| 100k-1M | IVF+Flat | ⚡ | 🔴 | 90% |
| >1M | IVF+PQ | 🐌 | ✅ | 85% |

FAISS auto-upgrade automáticamente según el tamaño.

### Caché

- **Redis**: 24 horas de TTL
- **Serialización**: orjson (5x más rápido que pickle)
- **Compresión**: LRU con 512MB límite

### Performance

- **HTTP/2**: Pool de 20 conexiones persistentes
- **Batch processing**: 64 embeddings por batch
- **Async/await**: Búsquedas paralelas en APIs

## 🧪 Testing

```bash
# Instalar dependencias de testing
pip install pytest pytest-asyncio pytest-cov

# Ejecutar tests
pytest

# Con cobertura
pytest --cov=. --cov-report=html

# Ver reporte
open htmlcov/index.html
```

## 📊 Métricas

### Prometheus

```bash
# Scrape endpoint
GET /api/metrics
```

Métricas disponibles:
- `api_requests_total`: Total de requests
- `api_latency_ms`: Latencia promedio
- `api_error_rate`: % de errores
- `cache_hit_rate`: % de cache hits
- `faiss_indexed_papers`: Papers en FAISS

### Grafana Dashboard

```json
{
  "panels": [
    {
      "title": "Request Rate",
      "targets": ["rate(api_requests_total[5m])"]
    },
    {
      "title": "FAISS Index Size",
      "targets": ["faiss_indexed_papers"]
    }
  ]
}
```

## 🐛 Troubleshooting

### Error: FAISS no disponible

```bash
# Instalar FAISS
pip install faiss-cpu

# O para GPU
pip install faiss-gpu
```

### Error: Redis connection refused

```bash
# Verificar que Redis esté corriendo
docker-compose ps

# Ver logs
docker-compose logs redis

# Reiniciar servicios
docker-compose restart
```

### Memoria insuficiente

```bash
# Limpiar índice FAISS
curl -X POST http://localhost:5000/api/faiss/clear

# O reducir límites en docker-compose.yml
deploy:
  resources:
    limits:
      memory: 1G  # Reducir de 2G a 1G
```

### Índice corrupto

```bash
# Auto-reparación
curl -X POST http://localhost:5000/api/faiss/save

# O limpiar y reconstruir
curl -X POST http://localhost:5000/api/faiss/clear
```

## 🔄 Backup y Recuperación

### Backup Manual

```bash
# Backup FAISS
curl -X POST http://localhost:5000/api/faiss/backup

# Copiar datos
docker cp academic_search_app:/app/backups ./backups_local
```

### Backup Automático (Cron)

```bash
# Agregar a crontab
0 2 * * * docker exec academic_search_app curl -X POST http://localhost:5000/api/faiss/backup
```

### Restauración

```bash
# Copiar backup
docker cp ./backups_local/faiss_20231215_020000/ academic_search_app:/app/data/

# Renombrar archivos
docker exec academic_search_app mv data/faiss_20231215_020000/faiss_index.index data/faiss_index.index

# Reiniciar
docker-compose restart app
```

## 📝 Logs

### Ver Logs

```bash
# Tiempo real
docker-compose logs -f app

# Últimas 100 líneas
docker-compose logs --tail=100 app

# Logs de archivo
docker exec academic_search_app tail -f logs/app_$(date +%Y%m%d).log
```

### Niveles de Log

Configurar en `.env`:

```bash
LOG_LEVEL=DEBUG  # DEBUG, INFO, WARNING, ERROR, CRITICAL
```

## 🚀 Producción

### Checklist

- [ ] Cambiar `REDIS_PASSWORD` y `FLASK_SECRET_KEY`
- [ ] Configurar `ALLOWED_ORIGINS` con dominios reales
- [ ] Establecer `LOG_LEVEL=WARNING`
- [ ] Configurar backup automático
- [ ] Configurar monitoreo (Prometheus + Grafana)
- [ ] Habilitar HTTPS en reverse proxy
- [ ] Limitar recursos en docker-compose
- [ ] Configurar alertas

### Reverse Proxy (Nginx)

```nginx
server {
    listen 80;
    server_name api.yourdomain.com;

    location / {
        proxy_pass http://localhost:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    }
}
```

### Escalado

```bash
# Aumentar workers de Gunicorn
# En Dockerfile, cambiar:
CMD ["gunicorn", "--workers", "8", ...]  # De 4 a 8

# Escalar con Docker Compose
docker-compose up -d --scale app=3
```

## 📚 Documentación Adicional

- [FAISS Usage Guide](FAISS_USAGE.md)
- [API Reference](docs/API.md)
- [Architecture](docs/ARCHITECTURE.md)

## 🤝 Contribución

1. Fork el proyecto
2. Crear branch (`git checkout -b feature/AmazingFeature`)
3. Commit cambios (`git commit -m 'Add AmazingFeature'`)
4. Push al branch (`git push origin feature/AmazingFeature`)
5. Abrir Pull Request

## 📄 Licencia

Este proyecto está bajo la licencia MIT.

## 👥 Autores

- **Equipo xplagiax** - Desarrollo inicial

## 🙏 Agradecimientos

- Sentence Transformers
- FAISS (Facebook AI)
- Flask
- Todas las APIs académicas utilizadas

  ┌─────────────────────────────────────────────────────────────────┐
│ USUARIO ENVÍA REQUEST                                           │
│ POST /api/similarity-search                                     │
│ {                                                               │
│   "data": [                                                     │
│     "machine learning",                                         │
│     "en",                                                       │
│     [                                                           │
│       ["page1", "para1", "Neural networks are models"],        │
│       ["page1", "para2", "Deep learning uses layers"]          │
│     ]                                                           │
│   ]                                                             │
│ }                                                               │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│ PASO 1: Flask recibe el request                                │
│ Archivo: app.py línea 43                                       │
│ Función: @app.route('/api/similarity-search')                  │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│ PASO 2: Validación de datos                                    │
│ Archivo: app.py líneas 51-77                                   │
│                                                                 │
│ ✓ Verifica que exista campo 'data'                            │
│ ✓ Extrae: theme = "machine learning"                          │
│ ✓ Extrae: idiom = "en"                                        │
│ ✓ Extrae: texts = [[page, para, text], ...]                  │
│ ✓ Extrae: sources = None (opcional)                           │
│ ✓ Extrae: use_faiss = True (default)                          │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│ PASO 3: Llama al procesador principal                          │
│ Archivo: app.py línea 80                                       │
│                                                                 │
│ process_similarity_batch(                                       │
│   texts,              # Los párrafos a buscar                  │
│   theme,              # "machine learning"                     │
│   idiom,              # "en"                                   │
│   redis_client,       # Para caché                             │
│   http_client,        # Para APIs                              │
│   rate_limiter,       # Control de rate limits                 │
│   sources,            # APIs a usar                            │
│   use_faiss           # Si usar FAISS o no                     │
│ )                                                               │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│ PASO 4: Inicio del procesamiento batch                         │
│ Archivo: search_service.py línea 49                            │
│ Función: process_similarity_batch()                            │
│                                                                 │
│ • Inicia timer para métricas                                   │
│ • Verifica salud del índice FAISS                             │
│ • Agrupa textos únicos (deduplicación)                        │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│ PASO 5: Preprocesamiento de textos                            │
│ Archivo: search_service.py líneas 61-80                       │
│                                                                 │
│ Para cada texto:                                               │
│   1. preprocess_text_cached()                                  │
│      • Convierte a minúsculas                                  │
│      • Elimina caracteres especiales                           │
│      • Normaliza espacios                                      │
│                                                                 │
│   Entrada: "Neural networks are computational Models!"         │
│   Salida: "neural networks are computational models"           │
│                                                                 │
│   2. remove_stopwords_optimized()                              │
│      • Tokeniza el texto                                       │
│      • Elimina palabras comunes (are, the, is...)             │
│                                                                 │
│   Entrada: "neural networks are computational models"          │
│   Salida: "neural networks computational models"               │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│ PASO 6: Verificar caché Redis                                  │
│ Archivo: search_service.py línea 70                            │
│                                                                 │
│ • Genera clave única: hash(theme + idiom + texto)             │
│ • Busca en Redis: "search:abc123..."                          │
│                                                                 │
│ SI ENCUENTRA en caché:                                         │
│   → Retorna resultados inmediatamente ✅                       │
│   → Salta al PASO 14                                           │
│                                                                 │
│ SI NO ENCUENTRA:                                               │
│   → Continúa al PASO 7 ⏬                                       │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│ PASO 7: Búsqueda en FAISS (si disponible)                     │
│ Archivo: search_service.py líneas 85-100                      │
│                                                                 │
│ SI FAISS tiene papers indexados:                               │
│   1. Llama a faiss_index.search_batch()                       │
│      • Genera embeddings de las queries                        │
│      • Busca vectores similares en el índice                   │
│      • Retorna top 20 por query                                │
│                                                                 │
│   Ejemplo:                                                      │
│   Query: "neural networks computational models"                │
│   ↓                                                             │
│   Embedding: [0.12, -0.45, 0.78, ..., 0.34] (384 dims)       │
│   ↓                                                             │
│   FAISS busca vectores similares                               │
│   ↓                                                             │
│   Encuentra:                                                    │
│     - "Deep Learning Book" (89.2% match)                       │
│     - "Neural Network Basics" (85.7% match)                    │
│     - "CNN Tutorial" (82.1% match)                             │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│ PASO 8: Evaluar resultados de FAISS                           │
│ Archivo: search_service.py líneas 102-122                     │
│                                                                 │
│ Para cada query:                                               │
│   SI encontró ≥5 resultados en FAISS:                         │
│     → Convierte a SearchResult                                 │
│     → Guarda en caché                                          │
│     → Marca como "completo" ✅                                 │
│                                                                 │
│   SI encontró <5 resultados:                                   │
│     → Marca para buscar en APIs 🌐                            │
│     → Continúa al PASO 9 ⏬                                    │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│ PASO 9: Búsqueda en APIs externas (si es necesario)             │
│ Archivo: search_service.py línea 127                            │
│ Función: search_all_sources()                                   │
│                                                                 │
│ Busca en PARALELO en todas las APIs:                            │
│   • Crossref                                                    │
│   • PubMed                                                      │
│   • Semantic Scholar                                            │
│   • arXiv                                                       │
│   • OpenAlex                                                    │
│   • Europe PMC                                                  │
│   • DOAJ                                                        │
│   • Zenodo                                                      │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│ PASO 10: Detalle de búsqueda en UNA API (ej: Semantic Scholar)  │
│ Archivo: searchers.py línea 112                                 │
│ Función: search_semantic_scholar()                              │
│                                                                 │
│ 1. Verifica rate limit (100 req/min)                            │
│    SI excede límite → Retorna [] vacío                          │
│                                                                 │
│ 2. Construye request HTTP:                                      │
│    GET https://api.semanticscholar.org/graph/v1/paper/search    │
│    params: {                                                    │
│      query: "machine learning neural networks models",          │
│      limit: 5,                                                  │
│      fields: "title,abstract,authors,publicationTypes"          │
│    }                                                            │
│                                                                 │
│ 3. Espera respuesta (timeout 8s)                                │
│                                                                 │
│ 4. Parsea JSON:                                                 │
│    {                                                            │
│      "data": [                                                  │
│        {                                                        │
│          "title": "Deep Learning",                              │
│          "abstract": "This paper presents...",                  │
│          "authors": [{"name": "Goodfellow"}],                   │
│          "publicationTypes": ["JournalArticle"]                 │
│        },                                                       │
│        ...                                                      │
│      ]                                                          │
│    }                                                            │
│                                                                 │
│ 5. Retorna lista de papers:                                     │
│    [                                                            │
│      {                                                          │
│        "title": "Deep Learning",                                │
│        "abstract": "This paper presents...",                    │
│        "author": "Goodfellow",                                  │
│        "type": "JournalArticle"                                 │
│      }                                                          │
│    ]                                                            │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│ PASO 11: Agregar papers nuevos a FAISS                        │
│ Archivo: search_service.py líneas 133-148                     │
│                                                                 │
│ Para cada paper encontrado en APIs:                            │
│   1. Extrae abstract                                           │
│   2. Genera metadata:                                          │
│      {                                                          │
│        "title": "Deep Learning",                               │
│        "author": "Goodfellow",                                 │
│        "abstract": "This paper...",                            │
│        "source": "semantic_scholar",                           │
│        "type": "JournalArticle"                                │
│      }                                                          │
│                                                                 │
│   3. Llama a faiss_index.add_papers()                         │
│      • Genera embeddings de abstracts                          │
│      • Los normaliza (L2)                                      │
│      • Los agrega al índice FAISS                             │
│      • Guarda metadata asociada                                │
│                                                                 │
│ RESULTADO: Papers quedan guardados para futuras búsquedas 💾  │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│ PASO 12: Calcular similitud con embeddings                    │
│ Archivo: search_service.py línea 151                          │
│ Función: calculate_similarities_batch()                        │
│                                                                 │
│ 1. Preprocesa abstracts de papers encontrados                 │
│    Abstract: "This paper presents deep learning methods..."    │
│    →                                                            │
│    Procesado: "paper presents deep learning methods"           │
│                                                                 │
│ 2. Genera embeddings en BATCH (rápido):                       │
│    Query: [0.12, -0.45, 0.78, ..., 0.34]                     │
│    Papers: [                                                   │
│      [0.15, -0.42, 0.81, ..., 0.31],  ← Paper 1              │
│      [0.08, -0.52, 0.65, ..., 0.29],  ← Paper 2              │
│      [-0.20, 0.15, -0.10, ..., 0.45]  ← Paper 3              │
│    ]                                                            │
│                                                                 │
│ 3. Calcula similitud coseno (NumPy vectorizado):              │
│    similarities = cosine_similarity(query, papers)             │
│    → [0.892, 0.857, 0.234]  # Paper 1=89%, Paper 2=85%, ...  │
│                                                                 │
│ 4. Filtra por threshold (70%):                                │
│    Papers con similitud ≥70%:                                 │
│      ✅ Paper 1: 89.2%                                         │
│      ✅ Paper 2: 85.7%                                         │
│      ❌ Paper 3: 23.4% (descartado)                           │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│ PASO 13: Construir objetos SearchResult                       │
│ Archivo: search_service.py líneas 153-168                     │
│                                                                 │
│ Para cada paper con similitud ≥70%:                           │
│   SearchResult(                                                │
│     fuente = "semantic_scholar",                               │
│     texto_original = "Neural networks are models",             │
│     texto_encontrado = "This paper presents deep...",          │
│     porcentaje_match = 89.2,                                   │
│     documento_coincidente = "Deep Learning Book",              │
│     autor = "Goodfellow",                                      │
│     type_document = "JournalArticle"                           │
│   )                                                             │
│                                                                 │
│ • Ordena por similitud (descendente)                          │
│ • Toma top 10 por query                                       │
│ • Guarda en caché Redis                                       │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│ PASO 14: Guardar índice FAISS actualizado                     │
│ Archivo: search_service.py línea 175                          │
│                                                                 │
│ • Llama a faiss_index.save()                                   │
│ • Guarda índice en: data/faiss_index.index                    │
│ • Guarda metadata en: data/faiss_index_metadata.pkl           │
│                                                                 │
│ AHORA los nuevos papers están disponibles para próximas       │
│ búsquedas sin necesidad de llamar APIs otra vez 🚀            │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│ PASO 15: Calcular métricas de performance                     │
│ Archivo: search_service.py líneas 179-183                     │
│                                                                 │
│ elapsed = tiempo_final - tiempo_inicial                        │
│ throughput = textos_procesados / elapsed                       │
│                                                                 │
│ Imprime:                                                         │
│   ⚡ Procesamiento completado en 2.34s                          │
│   📈 Throughput: 4.3 textos/s                                   │
│   💾 FAISS: 1523 papers indexados                               │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│ PASO 16: Retornar al endpoint Flask                             │
│ Archivo: search_service.py línea 185                            │
│                                                                 │
│ Retorna lista de SearchResult:                                  │
│   [                                                             │
│     SearchResult(fuente="semantic_scholar", ...),               │
│     SearchResult(fuente="arxiv", ...),                          │
│     SearchResult(fuente="pubmed", ...)                          │
│   ]                                                             │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│ PASO 17: Flask convierte a JSON                                 │
│ Archivo: app.py líneas 89-96                                    │
│                                                                 │
│ response = [asdict(r) for r in results]                         │
│                                                                 │
│ Convierte SearchResult → Dict:                                  │
│   {                                                             │
│     "fuente": "semantic_scholar",                               │
│     "texto_original": "Neural networks are models",             │
│     "texto_encontrado": "This paper presents...",               │
│     "porcentaje_match": 89.2,                                   │
│     "documento_coincidente": "Deep Learning Book",              │
│     "autor": "Goodfellow",                                      │
│     "type_document": "JournalArticle"                           │
│   }                                                             │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│ PASO 18: Enviar respuesta HTTP                                  │
│ Archivo: app.py líneas 98-102                                   │
│                                                                 │
│ return jsonify({                                                │
│   "results": [                                                  │
│     {                                                           │
│       "fuente": "semantic_scholar",                             │
│       "texto_original": "Neural networks are models",           │
│       "texto_encontrado": "This paper presents deep...",        │
│       "porcentaje_match": 89.2,                                 │
│       "documento_coincidente": "Deep Learning Book",            │
│       "autor": "Goodfellow",                                    │
│       "type_document": "JournalArticle"                         │
│     },                                                          │
│     {                                                           │
│       "fuente": "arxiv",                                        │
│       "texto_original": "Deep learning uses layers",            │
│       "texto_encontrado": "We propose a novel...",              │
│       "porcentaje_match": 85.7,                                 │
│       "documento_coincidente": "CNN Architecture",              │
│       "autor": "LeCun",                                         │
│       "type_document": "preprint"                               │
│     }                                                           │
│   ],                                                            │
│   "count": 2,                                                   │
│   "processed_texts": 2,                                         │
│   "faiss_enabled": true                                         │
│ }), 200                                                         │
│                                                                 │
│ Status: 200 OK                                                  │
│ Content-Type: application/json                                  │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│ USUARIO RECIBE RESPUESTA                                        │
│                                                                 │
│ JSON con papers similares encontrados ✅                        │
└─────────────────────────────────────────────────────────────────┘