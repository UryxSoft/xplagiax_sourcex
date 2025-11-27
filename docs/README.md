# XPLAGIAX SourceX - Academic Plagiarism Detection API

![Version](https://img.shields.io/badge/version-2.1.0-blue)
![Python](https://img.shields.io/badge/python-3.11+-green)
![License](https://img.shields.io/badge/license-MIT-orange)

## Overview

**XPLAGIAX SourceX** is a comprehensive academic plagiarism detection API that searches across 12 academic databases to identify similar papers and potential plagiarism using advanced semantic similarity techniques.

### Key Features

- 🔍 **12 Academic Sources**: Crossref, PubMed, Semantic Scholar, arXiv, OpenAlex, Europe PMC, DOAJ, Zenodo, CORE, Internet Archive, Unpaywall, HAL
- 🚀 **Fast Vector Search**: FAISS-powered similarity search with 384-dimensional embeddings
- 🧠 **AI-Powered**: Sentence-transformers (all-MiniLM-L6-v2) for semantic similarity
- 💾 **Intelligent Caching**: Redis caching with smart deduplication (Bloom filters + SQLite)
- 📊 **Advanced Analytics**: Plagiarism level detection (HIGH/MEDIUM/LOW)
- 🌍 **Multi-language**: Supports 12 languages with stopwords removal
- ⚡ **High Performance**: GPU support, async operations, batch processing

## Quick Start

### Prerequisites

- Python 3.11+
- Redis 6+
- 2GB+ RAM (4GB+ recommended)
- Optional: CUDA-capable GPU for faster embeddings

### Installation
```bash
# Clone repository
git clone https://github.com/yourusername/xplagiax_sourcex.git
cd xplagiax_sourcex

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Download NLTK data
python -c "import nltk; nltk.download('stopwords')"

# Setup environment
cp .env.example .env
# Edit .env with your configuration

# Initialize database
python scripts/init_db.py --seed

# Run development server
python run.py
```

### Docker Quick Start
```bash
# Using Docker Compose
docker-compose up -d

# Check logs
docker-compose logs -f

# API available at: http://localhost:5000
```

## API Usage

### Similarity Search
```bash
curl -X POST http://localhost:5000/api/similarity-search \
  -H "Content-Type: application/json" \
  -d '{
    "data": [
      "machine learning",
      "en",
      [
        ["1", "1", "This paper presents a novel deep learning approach for image classification using convolutional neural networks."]
      ]
    ],
    "threshold": 0.70,
    "use_faiss": true
  }'
```

### Plagiarism Check
```bash
curl -X POST http://localhost:5000/api/plagiarism-check \
  -H "Content-Type: application/json" \
  -d '{
    "data": [
      "artificial intelligence",
      "en",
      [
        ["1", "1", "Machine learning is a subset of AI that enables computers to learn from data."]
      ]
    ],
    "threshold": 0.75,
    "chunk_mode": "sentences",
    "min_chunk_words": 15
  }'
```

### Response Format
```json
{
  "results": [
    {
      "fuente": "arxiv",
      "texto_original": "This paper presents...",
      "texto_encontrado": "We present a novel...",
      "porcentaje_match": 0.89,
      "documento_coincidente": "Deep Learning for Image Classification",
      "autor": "John Doe, Jane Smith",
      "type_document": "article",
      "plagiarism_level": "high",
      "publication_date": "2023-05-15",
      "doi": "10.1234/example.001",
      "url": "https://arxiv.org/abs/2305.12345"
    }
  ],
  "count": 1,
  "processed_texts": 1,
  "threshold_used": 0.70,
  "faiss_enabled": true
}
```

## Architecture
```
┌─────────────┐
│   Client    │
└──────┬──────┘
       │
┌──────▼──────────────────────────────────────┐
│              API Layer                       │
│  (Flask Routes + Controllers + Schemas)      │
└──────┬──────────────────────────────────────┘
       │
┌──────▼──────────────────────────────────────┐
│          Services Layer                      │
│  ┌──────────────┐  ┌──────────────┐        │
│  │ Similarity   │  │   FAISS      │        │
│  │   Service    │  │  Service     │        │
│  └──────────────┘  └──────────────┘        │
│  ┌──────────────┐  ┌──────────────┐        │
│  │  External    │  │Deduplication │        │
│  │  API Manager │  │  Service     │        │
│  └──────────────┘  └──────────────┘        │
└──────┬──────────────────────────────────────┘
       │
┌──────▼──────────────────────────────────────┐
│        Data Layer (Repositories)             │
│  ┌─────────┐  ┌─────────┐  ┌─────────┐    │
│  │  FAISS  │  │  Redis  │  │ SQLite  │    │
│  └─────────┘  └─────────┘  └─────────┘    │
└──────────────────────────────────────────────┘
```

## Configuration

### Environment Variables
```bash
# Flask
FLASK_ENV=development
FLASK_SECRET_KEY=your-secret-key

# Security
ADMIN_API_KEY=your-admin-key

# Redis
REDIS_URL=redis://localhost:6379/0
REDIS_PASSWORD=

# External APIs
CORE_API_KEY=YOUR_API_KEY

# Features
ENABLE_FAISS=true
ENABLE_CACHE=true

# Performance
EMBEDDING_DEVICE=cpu  # or 'cuda' for GPU
EMBEDDING_BATCH_SIZE=32
```

See `.env.example` for complete list.

## Project Structure
```
xplagiax_sourcex/
├── app/
│   ├── api/                    # API routes, controllers, schemas
│   ├── services/               # Business logic
│   ├── repositories/           # Data access layer
│   ├── models/                 # Data models
│   ├── core/                   # Core utilities (config, errors, security)
│   └── utils/                  # Helper functions
├── configs/                    # Environment configurations
├── scripts/                    # Maintenance scripts
├── tests/                      # Test suite
├── docker/                     # Docker configuration
└── docs/                       # Documentation
```

## Testing
```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=app --cov-report=html

# Run specific test file
pytest tests/unit/test_validators.py -v

# Run integration tests
pytest tests/integration/ -v
```

## Performance

### Benchmarks

- **Embedding Generation**: 500+ texts/sec (CPU), 5000+ texts/sec (GPU)
- **FAISS Search**: <20ms for 1M+ papers (Flat), <5ms (IVF+PQ)
- **API Response Time**: 200-800ms (depending on sources queried)
- **Memory Usage**: ~1.5GB base + ~100MB per 100K papers in FAISS

### Optimization Tips

1. **Enable GPU**: Set `EMBEDDING_DEVICE=cuda` for 10x faster embeddings
2. **Use IVF+PQ**: Switch to `FAISS_STRATEGY=ivf_pq` for 10M+ papers
3. **Enable Caching**: Keep `ENABLE_CACHE=true` for 90%+ cache hit rate
4. **Limit Sources**: Query only needed sources to reduce latency

## Troubleshooting

### Common Issues

**Issue**: FAISS index corrupted
```bash
# Rebuild index
python scripts/migrate_faiss.py rebuild
```

**Issue**: Redis connection failed
```bash
# Check Redis is running
redis-cli ping
# Should return: PONG
```

**Issue**: Slow embedding generation
```bash
# Enable GPU if available
export EMBEDDING_DEVICE=cuda

# Or increase batch size
export EMBEDDING_BATCH_SIZE=256
```

**Issue**: High memory usage
```bash
# Use IVF+PQ strategy for large datasets
python scripts/migrate_faiss.py upgrade --strategy ivf_pq
```

## Contributing

Contributions are welcome! Please read our [Contributing Guide](CONTRIBUTING.md).

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## License

This project is licensed under the MIT License - see [LICENSE](LICENSE) file.

## Support

- 📧 Email: support@xplagiax.com
- 🐛 Issues: [GitHub Issues](https://github.com/yourusername/xplagiax_sourcex/issues)
- 📖 Docs: [Full Documentation](https://docs.xplagiax.com)

## Acknowledgments

- [FAISS](https://github.com/facebookresearch/faiss) - Fast similarity search
- [Sentence-Transformers](https://www.sbert.net/) - Semantic embeddings
- All the amazing open academic APIs we integrate with

---

**Made with ❤️ by the XPLAGIAX Team**