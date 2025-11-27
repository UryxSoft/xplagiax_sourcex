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
# xplagiax_sourcex - Academic Plagiarism Detection API

> **Production-grade Flask API** for detecting plagiarism through semantic similarity search across 12 academic databases with local FAISS vector indexing.

[![Python 3.11](https://img.shields.io/badge/python-3.11-blue.svg)](https://www.python.org/downloads/)
[![Flask](https://img.shields.io/badge/flask-3.1-green.svg)](https://flask.palletsprojects.com/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

---

## 🚀 Quick Start

```bash
# 1. Clone & setup
git clone <repo-url>
cd xplagiax_sourcex

# 2. Configure environment
cp .env.example .env
# Edit .env - IMPORTANT: Set ADMIN_API_KEY and FLASK_SECRET_KEY

# 3. Start with Docker
docker-compose up --build

# 4. Verify
curl http://localhost:5000/api/health
```

---

## 📊 Architecture

```
┌─────────────────────────────────────────────────────┐
│   Client Request                                    │
└──────────────┬──────────────────────────────────────┘
               ↓
┌──────────────────────────────────────────────────────┐
│   Flask + Gunicorn (4 workers)                       │
│   • Blueprints (modular routes)                      │
│   • Rate limiting (Redis-backed)                     │
│   • Input validation & sanitization                  │
│   • Circuit breakers                                 │
│   • Admin endpoints (API key protected)              │
└──────────────┬───────────────────────────────────────┘
               ↓
        ┌──────┴──────┐
        ↓             ↓
┌──────────────┐ ┌────────────────────┐
│ Redis Cache  │ │ FAISS Vector Index │
│ (24h TTL)    │ │ (384D embeddings)  │
│ orjson       │ │ IndexIDMap         │
└──────────────┘ └────────────────────┘
        ↓             ↓
┌───────────────────────────────────────────────┐
│ Academic APIs (12 sources, parallel search)   │
│ Crossref • PubMed • Semantic Scholar • arXiv  │
│ OpenAlex • Europe PMC • DOAJ • Zenodo         │
│ CORE • BASE • Internet Archive • HAL          │
└───────────────────────────────────────────────┘
```

---

## ✨ Key Features

### 🔍 Search & Detection
- **Vector Similarity Search**: <200ms for 1M papers via FAISS
- **12 Academic APIs**: Parallel search with circuit breakers
- **Semantic Analysis**: 384-dimensional embeddings (MiniLM)
- **Plagiarism Levels**: 5-tier classification (very_high → minimal)

### 🚀 Performance
- **Redis Caching**: 24h TTL, orjson serialization (5x faster than pickle)
- **Bloom Filter Dedup**: O(1) duplicate detection
- **HTTP/2 Connection Pool**: 20 persistent connections
- **Batch Processing**: 64 embeddings per batch

### 🔒 Security
- **API Key Authentication**: Admin endpoints protected
- **CORS Configuration**: Whitelist-based (no wildcards in production)
- **Input Sanitization**: XSS/injection protection
- **Rate Limiting**: Redis-backed, per-IP and per-endpoint

### 📈 Observability
- **Prometheus Metrics**: `/api/metrics` endpoint
- **Health Checks**: Comprehensive system diagnostics
- **Structured Logging**: JSON format (optional)
- **Performance Profiling**: Built-in bottleneck detection

---

## 🔌 API Endpoints

### Search Endpoints

#### POST `/api/similarity-search`
Main similarity search endpoint.

**Request:**
```json
{
  "data": [
    "machine learning",  // theme
    "en",                // language (en, es, fr, de, pt, it, ru, zh, ja, ko)
    [
      ["page1", "para1", "Neural networks are computational models..."]
    ]
  ],
  "threshold": 0.75,  // optional (0.0-1.0, default: 0.70)
  "use_faiss": true,  // optional (default: true)
  "sources": ["semantic_scholar", "arxiv"]  // optional
}
```

**Response:**
```json
{
  "results": [
    {
      "fuente": "semantic_scholar",
      "porcentaje_match": 89.2,
      "documento_coincidente": "Deep Learning Book",
      "autor": "Goodfellow et al.",
      "type_document": "article",
      "plagiarism_level": "very_high",
      "publication_date": "2016",
      "doi": "10.1234/example",
      "url": "https://..."
    }
  ],
  "count": 10,
  "threshold_used": 0.75,
  "faiss_enabled": true
}
```

#### POST `/api/plagiarism-check`
Specialized plagiarism detection with text chunking.

**Request:**
```json
{
  "data": ["theme", "en", [["page", "para", "text"]]],
  "threshold": 0.70,
  "chunk_mode": "sentences",  // "sentences" or "sliding"
  "min_chunk_words": 15
}
```

**Response:**
```json
{
  "plagiarism_detected": true,
  "chunks_analyzed": 25,
  "total_matches": 12,
  "summary": {
    "very_high": 2,
    "high": 3,
    "moderate": 5,
    "low": 2,
    "minimal": 0
  },
  "by_level": {
    "very_high": {
      "count": 2,
      "results": [...]
    }
  }
}
```

### FAISS Management

| Endpoint | Method | Auth | Description |
|----------|--------|------|-------------|
| `/api/faiss/stats` | GET | No | Get index statistics |
| `/api/faiss/search` | POST | No | Direct FAISS search |
| `/api/faiss/save` | POST | ✅ | Save index to disk |
| `/api/faiss/clear` | POST | ✅ | Clear entire index |
| `/api/faiss/backup` | POST | ✅ | Create backup |
| `/api/faiss/remove-duplicates` | POST | ✅ | Remove duplicates |

### Administration

| Endpoint | Method | Auth | Description |
|----------|--------|------|-------------|
| `/api/reset-limits` | POST | ✅ | Reset rate limits |
| `/api/cache/clear` | POST | ✅ | Clear Redis cache |
| `/api/benchmark` | POST | No | Performance test |
| `/api/deduplication/stats` | GET | No | Dedup statistics |

### Monitoring

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/health` | GET | Health check with metrics |
| `/api/metrics` | GET | Prometheus format |
| `/api/diagnostics/full` | GET | Complete diagnostics |
| `/api/validate-apis` | POST | Test external APIs |
| `/api/profiler/stats` | GET | Performance stats |
| `/api/profiler/bottlenecks` | GET | Identify bottlenecks |

---

## 🔐 Security

### Authentication

Protected endpoints require `X-API-Key` header:

```bash
curl -X POST http://localhost:5000/api/faiss/clear \
  -H "X-API-Key: your-admin-key-here"
```

### Configuration Checklist

- [ ] **Set `ADMIN_API_KEY`** in `.env` (generate with `openssl rand -base64 48`)
- [ ] **Set `FLASK_SECRET_KEY`** in `.env`
- [ ] **Set `REDIS_PASSWORD`** for Redis authentication
- [ ] **Configure `ALLOWED_ORIGINS`** with specific domains (no `*` in production)
- [ ] **Enable HTTPS** via reverse proxy (Nginx/Traefik)
- [ ] **Rotate API keys** periodically

### Rate Limits

- **Global**: 200 req/day, 50 req/hour per IP
- **Search**: 10 req/minute
- **Plagiarism Check**: 5 req/minute
- **Benchmark**: 5 req/hour

---

## 🛠️ Development

### Local Setup

```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Download NLTK data
python -c "import nltk; nltk.download('punkt'); nltk.download('stopwords')"

# Run development server
FLASK_DEBUG=1 python app.py
```

### Running Tests

```bash
# Install test dependencies
pip install pytest pytest-asyncio pytest-cov

# Run tests
pytest

# With coverage
pytest --cov=. --cov-report=html

# View coverage
open htmlcov/index.html
```

### Code Quality

```bash
# Linting
flake8 . --max-line-length=120

# Type checking
mypy . --ignore-missing-imports

# Format code
black .
```

---

## 🐳 Docker Deployment

### Production Configuration

```yaml
# docker-compose.yml
services:
  app:
    build: .
    environment:
      - FLASK_ENV=production
      - ADMIN_API_KEY=${ADMIN_API_KEY}
      - REDIS_PASSWORD=${REDIS_PASSWORD}
      - ALLOWED_ORIGINS=https://yourdomain.com
    deploy:
      resources:
        limits:
          cpus: '2'
          memory: 2G
```

### Scaling

```bash
# Scale with Docker Compose
docker-compose up -d --scale app=3

# Or use Kubernetes
kubectl apply -f k8s/deployment.yaml
kubectl scale deployment xplagiax --replicas=5
```

---

## 📊 Monitoring

### Prometheus + Grafana

```yaml
# prometheus.yml
scrape_configs:
  - job_name: 'xplagiax'
    static_configs:
      - targets: ['app:5000']
    metrics_path: '/api/metrics'
```

**Key Metrics:**
- `api_requests_total`: Total requests
- `api_latency_ms`: Average latency
- `api_error_rate`: Error percentage
- `cache_hit_rate`: Cache efficiency
- `faiss_indexed_papers`: Index size

### Grafana Dashboard

```json
{
  "panels": [
    {
      "title": "Request Rate",
      "targets": ["rate(api_requests_total[5m])"]
    },
    {
      "title": "Latency P95",
      "targets": ["histogram_quantile(0.95, api_latency_ms)"]
    }
  ]
}
```

---

## 🔧 Configuration

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `ADMIN_API_KEY` | **Required** | API key for admin endpoints |
| `FLASK_SECRET_KEY` | **Required** | Flask session secret |
| `REDIS_PASSWORD` | - | Redis auth password |
| `REDIS_HOST` | `localhost` | Redis hostname |
| `REDIS_PORT` | `6379` | Redis port |
| `ALLOWED_ORIGINS` | `localhost` | CORS allowed origins |
| `LOG_LEVEL` | `INFO` | Logging level |
| `CORE_API_KEY` | - | Optional: CORE search API key |

### Model Configuration

```python
# config.py
class Config:
    EMBEDDING_MODEL = "sentence-transformers/all-MiniLM-L6-v2"
    SIMILARITY_THRESHOLD = 0.70  # 0.0-1.0
    EMBEDDING_BATCH_SIZE = 32
    MAX_RESULTS_PER_SOURCE = 5
```

---

## 🚨 Troubleshooting

### FAISS not available
```bash
pip install faiss-cpu
# For GPU support:
pip install faiss-gpu
```

### Redis connection refused
```bash
docker-compose logs redis
docker-compose restart redis
```

### High memory usage
```bash
# Clear FAISS index
curl -X POST http://localhost:5000/api/faiss/clear \
  -H "X-API-Key: your-key"

# Clear Redis cache
curl -X POST http://localhost:5000/api/cache/clear \
  -H "X-API-Key: your-key"
```

### Slow searches
```bash
# Check FAISS stats
curl http://localhost:5000/api/faiss/stats

# Remove duplicates (speeds up index)
curl -X POST http://localhost:5000/api/faiss/remove-duplicates \
  -H "X-API-Key: your-key"

# Check profiler
curl http://localhost:5000/api/profiler/bottlenecks?top=5
```

---

## 📚 Documentation

- [Architecture Details](docs/ARCHITECTURE.md)
- [API Reference](docs/API.md)
- [FAISS Usage Guide](FAISS_USAGE.md)
- [Contributing Guide](docs/CONTRIBUTING.md)

---

## 🗺️ Roadmap

### v2.1 (Current - Refactored)
- ✅ Blueprints architecture
- ✅ API key authentication
- ✅ Secure CORS configuration
- ✅ Improved error handling

### v2.2 (Planned)
- [ ] Complete test suite (80% coverage)
- [ ] OpenAPI/Swagger documentation
- [ ] Redis cluster support
- [ ] Celery background jobs

### v3.0 (Future)
- [ ] Migrate to Quart (native async)
- [ ] PostgreSQL for metadata
- [ ] Qdrant for vector search
- [ ] Kubernetes deployment templates

---

## 🤝 Contributing

1. Fork the repository
2. Create feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit changes (`git commit -m 'Add AmazingFeature'`)
4. Push to branch (`git push origin feature/AmazingFeature`)
5. Open Pull Request

---

## 📄 License

This project is licensed under the MIT License - see [LICENSE](LICENSE) file.

---

## 👥 Authors

- **xplagiax Team** - *Initial work*

---

## 🙏 Acknowledgments

- [Sentence Transformers](https://www.sbert.net/)
- [FAISS](https://github.com/facebookresearch/faiss) by Facebook AI
- [Flask](https://flask.palletsprojects.com/)
- All academic API providers

---

## 📞 Support

- **Email**: support@xplagiax.com
- **Documentation**: https://docs.xplagiax.com
- **Issues**: https://github.com/xplagiax/sourcex/issues

---

**Built with ❤️ for academic integrity**