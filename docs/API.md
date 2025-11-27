# API Documentation

Complete API reference for XPLAGIAX SourceX v2.1.0

## Base URL
```
http://localhost:5000/api
```

## Authentication

Admin endpoints require an API key in the header:
```bash
Authorization: Bearer YOUR_ADMIN_API_KEY
```

---

## Endpoints

### Search Endpoints

#### POST /api/similarity-search

Search for similar academic papers.

**Request Body:**
```json
{
  "data": [
    "theme",              // string: Search theme/topic
    "language",           // string: Language code (en, es, fr, de, pt, it, nl, ru, zh, ja, ko)
    [                     // array: List of texts to check
      ["page", "para", "text"],
      ...
    ]
  ],
  "threshold": 0.70,      // float: Similarity threshold (0.0-1.0)
  "use_faiss": true,      // boolean: Use FAISS for fast search
  "sources": []           // array (optional): Specific sources to search
}
```

**Response:**
```json
{
  "results": [
    {
      "fuente": "arxiv",
      "texto_original": "Original text...",
      "texto_encontrado": "Found text...",
      "porcentaje_match": 0.89,
      "documento_coincidente": "Paper Title",
      "autor": "Author Names",
      "type_document": "article",
      "plagiarism_level": "high",
      "publication_date": "2023-05-15",
      "doi": "10.1234/example.001",
      "url": "https://..."
    }
  ],
  "count": 1,
  "processed_texts": 1,
  "threshold_used": 0.70,
  "faiss_enabled": true
}
```

**Rate Limit:** 10 requests/minute

---

#### POST /api/plagiarism-check

Comprehensive plagiarism detection with text chunking.

**Request Body:**
```json
{
  "data": ["theme", "language", [["page", "para", "text"], ...]],
  "threshold": 0.70,
  "chunk_mode": "sentences",      // "sentences" or "sliding"
  "min_chunk_words": 15,
  "sources": []
}
```

**Response:**
```json
{
  "plagiarism_detected": true,
  "chunks_analyzed": 5,
  "total_matches": 3,
  "coverage_percent": 60.0,
  "summary": {
    "high": 1,
    "medium": 1,
    "low": 1
  },
  "by_level": {
    "high": [...],
    "medium": [...],
    "low": [...]
  },
  "threshold_used": 0.70,
  "faiss_enabled": true,
  "chunk_mode": "sentences"
}
```

**Rate Limit:** 5 requests/minute

---

### FAISS Endpoints

#### GET /api/faiss/stats

Get FAISS index statistics.

**Response:**
```json
{
  "total_papers": 150000,
  "dimension": 384,
  "metadata_count": 150000,
  "strategy": "flat_idmap",
  "supports_removal": true,
  "is_approximate": false,
  "corrupted": false
}
```

---

#### POST /api/faiss/search

Direct FAISS search.

**Request Body:**
```json
{
  "query": "machine learning",
  "k": 10,
  "threshold": 0.7
}
```

**Response:**
```json
{
  "query": "machine learning",
  "results": [...],
  "count": 10
}
```

---

#### POST /api/faiss/save

Save FAISS index to disk. **Requires API key.**

**Response:**
```json
{
  "message": "Index saved successfully",
  "stats": {...}
}
```

---

#### POST /api/faiss/clear

Clear entire FAISS index. **Requires API key. DESTRUCTIVE.**

**Response:**
```json
{
  "message": "Index cleared successfully"
}
```

---

### Admin Endpoints

All admin endpoints require API key authentication.

#### POST /api/reset-limits

Reset rate limits and circuit breakers.

**Response:**
```json
{
  "message": "Limits and circuit breakers reset successfully"
}
```

---

#### POST /api/cache/clear

Clear Redis cache. **DESTRUCTIVE.**

**Response:**
```json
{
  "message": "Cache cleared successfully"
}
```

---

#### POST /api/benchmark

Run performance benchmark.

**Request Body:**
```json
{
  "num_texts": 10  // 1-50
}
```

**Response:**
```json
{
  "benchmark_type": "faiss_only",
  "num_queries": 10,
  "total_results": 100,
  "elapsed_seconds": 0.123,
  "throughput_queries_per_sec": 81.3,
  "avg_latency_ms": 12.3,
  "faiss_index_size": 150000,
  "faiss_strategy": "flat_idmap"
}
```

**Rate Limit:** 5 requests/hour

---

### Diagnostics Endpoints

#### GET /api/health

Health check endpoint.

**Response:**
```json
{
  "status": "healthy",
  "version": "2.1.0",
  "redis": "connected",
  "http_pool": "active",
  "faiss": {...},
  "metrics": {
    "requests": 1234,
    "avg_latency_ms": 245.5,
    "error_rate": 0.5,
    "cache_hit_rate": 85.2,
    "uptime_seconds": 3600.5
  }
}
```

---

#### GET /api/metrics

Prometheus-compatible metrics.

**Response:** Plain text in Prometheus format
```
# HELP api_requests_total Total number of API requests
# TYPE api_requests_total counter
api_requests_total 1234

# HELP api_latency_ms Average request latency
# TYPE api_latency_ms gauge
api_latency_ms 245.5
...
```

---

#### GET /api/diagnostics/full

Complete system diagnostics.

**Response:**
```json
{
  "timestamp": 1234567890.123,
  "overall_health": "healthy",
  "components": {
    "faiss": {...},
    "redis": {...},
    "http_pool": {...},
    "apis": {...},
    "performance": {...}
  },
  "recommendations": [...]
}
```

---

#### POST /api/validate-apis

Validate external APIs.

**Request Body:**
```json
{
  "sources": ["crossref", "pubmed"]  // Optional
}
```

**Response:**
```json
{
  "summary": {
    "total_apis": 12,
    "available": 11,
    "unavailable": 1,
    "overall_health": "degraded",
    "avg_response_time_ms": 234.5
  },
  "apis": {
    "crossref": {
      "available": true,
      "response_time_ms": 123.4,
      "error": null
    },
    ...
  }
}
```

---

## Error Responses

All errors follow this format:
```json
{
  "error": "Error type",
  "message": "Detailed error message",
  "status_code": 400
}
```

### Common Error Codes

- **400 Bad Request**: Invalid input data
- **401 Unauthorized**: Missing or invalid API key
- **404 Not Found**: Endpoint not found
- **429 Too Many Requests**: Rate limit exceeded
- **500 Internal Server Error**: Server error
- **503 Service Unavailable**: Service temporarily unavailable

---

## Rate Limiting

Rate limits are enforced per IP address:

| Endpoint | Limit |
|----------|-------|
| /similarity-search | 10/minute |
| /plagiarism-check | 5/minute |
| /benchmark | 5/hour |
| Others | 60/minute |

**Rate Limit Headers:**
```
X-RateLimit-Limit: 10
X-RateLimit-Remaining: 7
X-RateLimit-Reset: 1234567890
```

---

## SDKs & Libraries

### Python
```python
import requests

def search_similarity(text, theme="AI", language="en"):
    response = requests.post(
        "http://localhost:5000/api/similarity-search",
        json={
            "data": [theme, language, [["1", "1", text]]],
            "threshold": 0.70,
            "use_faiss": True
        }
    )
    return response.json()

# Usage
results = search_similarity("This is my text to check for plagiarism.")
```

### JavaScript
```javascript
async function searchSimilarity(text, theme = "AI", language = "en") {
  const response = await fetch("http://localhost:5000/api/similarity-search", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      data: [theme, language, [["1", "1", text]]],
      threshold: 0.70,
      use_faiss: true
    })
  });
  return response.json();
}

// Usage
const results = await searchSimilarity("This is my text to check.");
```

---

## Pagination

For large result sets, use FAISS search with pagination:
```json
{
  "query": "machine learning",
  "k": 100,
  "threshold": 0.7
}
```

Results are sorted by similarity (highest first).

---

## Changelog

See [CHANGELOG.md](CHANGELOG.md) for version history.