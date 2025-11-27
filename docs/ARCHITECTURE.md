# Architecture Documentation

XPLAGIAX SourceX v2.1.0 - System Architecture

## Overview

XPLAGIAX SourceX follows a **Clean Architecture** pattern with clear separation of concerns across layers.

## High-Level Architecture
```
┌─────────────────────────────────────────────────────────────┐
│                     Presentation Layer                       │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐        │
│  │   Routes    │→ │ Controllers │→ │  Schemas    │        │
│  │  (Flask BP) │  │  (Request)  │  │(Validation) │        │
│  └─────────────┘  └─────────────┘  └─────────────┘        │
└──────────────────────────┬──────────────────────────────────┘
                           │
┌──────────────────────────▼──────────────────────────────────┐
│                    Business Logic Layer                      │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐     │
│  │ Similarity   │  │    FAISS     │  │ Deduplication│     │
│  │   Service    │  │   Service    │  │   Service    │     │
│  └──────────────┘  └──────────────┘  └──────────────┘     │
│  ┌──────────────┐  ┌──────────────┐                        │
│  │   External   │  │     Text     │                        │
│  │ API Manager  │  │  Processing  │                        │
│  └──────────────┘  └──────────────┘                        │
└──────────────────────────┬──────────────────────────────────┘
                           │
┌──────────────────────────▼──────────────────────────────────┐
│                     Data Access Layer                        │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐     │
│  │    FAISS     │  │    Redis     │  │   SQLite     │     │
│  │  Repository  │  │  Repository  │  │  Repository  │     │
│  └──────────────┘  └──────────────┘  └──────────────┘     │
└──────────────────────────────────────────────────────────────┘
```

## Layer Details

### 1. Presentation Layer (`app/api/`)

**Responsibilities:**
- HTTP request handling
- Input validation
- Response formatting
- Rate limiting
- Error handling

**Components:**

- **Routes** (`routes/`): Flask blueprints for endpoint organization
  - `search_routes.py`: Search and plagiarism check endpoints
  - `faiss_routes.py`: FAISS management endpoints
  - `admin_routes.py`: Admin operations
  - `diagnostics_routes.py`: Health checks and metrics

- **Controllers** (`controllers/`): Business logic orchestration
  - `search_controller.py`: Handles search requests
  - `faiss_controller.py`: FAISS operations
  - `admin_controller.py`: Admin tasks
  - `diagnostics_controller.py`: System health

- **Schemas** (`schemas/`): Request/response validation (Marshmallow)
  - `search_schema.py`: Search input validation
  - `faiss_schema.py`: FAISS operation schemas

### 2. Business Logic Layer (`app/services/`)

**Responsibilities:**
- Core business logic
- Algorithm implementation
- External API integration
- Data transformation

**Components:**

- **SimilarityService**: Core plagiarism detection
  - Text preprocessing
  - Embedding generation
  - FAISS + External API search
  - Similarity calculation
  - Result ranking

- **FAISSService**: Vector index management
  - Index creation/loading
  - Vector addition with deduplication
  - Similarity search
  - Index optimization

- **DeduplicationService**: Duplicate detection
  - Bloom filter (probabilistic)
  - SQLite verification (ground truth)
  - Content hash generation

- **External APIs** (`external_apis/`):
  - **BaseSearcher**: Template Method pattern
  - 12 concrete searchers (Crossref, PubMed, etc.)
  - **APIManager**: Orchestrates all searchers

- **Text Processing** (`text_processing/`):
  - **Preprocessor**: Text cleaning, normalization
  - **EmbeddingService**: Sentence-transformers integration
  - **Chunker**: Text segmentation strategies

### 3. Data Access Layer (`app/repositories/`)

**Responsibilities:**
- Data persistence
- CRUD operations
- Query optimization

**Components:**

- **FAISSRepository**: Vector index persistence
  - Multiple strategies (Flat, IVF, HNSW)
  - Save/load operations
  - Metadata management

- **RedisRepository**: Cache operations
  - Get/set with TTL
  - Batch operations
  - Pattern-based operations

- **SQLiteRepository**: Metadata persistence
  - Paper storage
  - Search history
  - Usage statistics

### 4. Core Layer (`app/core/`)

**Cross-cutting concerns:**

- **config.py**: Environment-specific settings
- **extensions.py**: Shared resources (Redis, HTTP client, FAISS)
- **security.py**: Authentication, authorization
- **middleware.py**: Request/response processing
- **errors.py**: Error handling, custom exceptions

### 5. Models Layer (`app/models/`)

**Data structures:**

- **SearchResult**: Plagiarism detection result
- **Paper**: Academic paper metadata
- **Enums**: Constants and enumerations
  - PlagiarismLevel, DocumentType, SearchSource, etc.

### 6. Utils Layer (`app/utils/`)

**Helper functions:**

- **asyncio_compat.py**: Sync/async bridging
- **cache.py**: Cache management utilities
- **validators.py**: Input validation
- **logging_config.py**: Structured logging
- **html_cleaner.py**: HTML sanitization
- **stopwords.py**: Language-specific stopword removal
- **rate_limiter.py**: Rate limiting logic
- **profiling.py**: Performance monitoring
- **api_validator.py**: External API health checks

## Design Patterns

### 1. Template Method Pattern

**Used in**: External API searchers
```python
class BaseSearcher(ABC):
    async def search(self, query, theme, http_client):
        # Template method - defines algorithm skeleton
        if not await self.rate_limiter.check_limit(source):
            return error_response
        
        url, params, headers = self.build_request(query, theme)  # Hook
        response = await http_client.get(url, params, headers)
        papers = self.parse_response(response.json())  # Hook
        
        return SearchResponse(papers, source, success=True)
    
    @abstractmethod
    def build_request(self, query, theme):
        pass  # Implemented by subclasses
    
    @abstractmethod
    def parse_response(self, data):
        pass  # Implemented by subclasses
```

**Benefits:**
- Eliminates 90% code duplication
- Easy to add new APIs (15 lines of code)
- Centralized error handling

### 2. Repository Pattern

**Used in**: Data access layer
```python
class FAISSRepository:
    def add(self, embeddings, papers):
        # Encapsulates FAISS operations
        ...
    
    def search(self, query_embedding, k, threshold):
        # Hides implementation details
        ...
```

**Benefits:**
- Separation of concerns
- Testability (easy to mock)
- Swappable implementations

### 3. Factory Pattern

**Used in**: Application initialization
```python
def create_app(config_name=None):
    app = Flask(__name__)
    config_class = get_config(config_name)
    app.config.from_object(config_class)
    # Initialize components
    return app
```

**Benefits:**
- Environment-specific configuration
- Centralized initialization
- Testing isolation

### 4. Singleton Pattern

**Used in**: Shared resources
```python
_deduplicator = None

async def get_deduplicator():
    global _deduplicator
    if _deduplicator is None:
        async with _deduplicator_lock:
            if _deduplicator is None:
                _deduplicator = DeduplicationService()
    return _deduplicator
```

**Benefits:**
- Single Bloom filter instance
- Resource efficiency
- Thread-safe initialization

## Data Flow

### Similarity Search Flow
```
1. Client Request
   ↓
2. Route (search_routes.py)
   ↓
3. Controller (search_controller.py)
   - Validate input (Marshmallow schema)
   ↓
4. SimilarityService
   ├─→ Preprocess text (remove HTML, stopwords)
   ├─→ Check cache (Redis)
   │   └─→ Cache HIT? → Return cached results
   ├─→ Generate embedding (sentence-transformers)
   ├─→ Search FAISS (vector similarity)
   ├─→ Search External APIs (12 sources in parallel)
   ├─→ Deduplicate results (Bloom filter + SQLite)
   ├─→ Calculate similarities (cosine similarity)
   ├─→ Save to cache (Redis)
   └─→ Save new papers to FAISS
   ↓
5. Controller
   - Format response
   ↓
6. Client Response
```

### FAISS Index Build Flow
```
1. Papers collected from APIs
   ↓
2. Generate content hash (SHA256)
   ↓
3. Check Bloom filter (O(1))
   ├─→ Possibly exists? → Verify in SQLite
   └─→ Definitely new? → Continue
   ↓
4. Generate embedding (sentence-transformers)
   ↓
5. Add to FAISS index
   ↓
6. Add hash to Bloom filter
   ↓
7. Save metadata to SQLite
   ↓
8. Persist FAISS index to disk
```

## Scalability Considerations

### Horizontal Scaling

**Current Limitations:**
- In-memory Bloom filter (per-instance)
- File-based FAISS index
- File-based SQLite

**Solutions for Scale:**

1. **Shared State**:
   - Move Bloom filter to Redis (RedisBloom)
   - Use PostgreSQL instead of SQLite
   - Distributed FAISS (multiple shards)

2. **Load Balancing**:
   - Multiple API instances behind NGINX
   - Sticky sessions for cache affinity
   - Redis Cluster for cache

3. **Async Workers**:
   - Celery for background tasks
   - RabbitMQ/Redis as message broker
   - Separate workers for embedding generation

### Vertical Scaling

**Optimizations:**

1. **GPU Acceleration**:
   - Set `EMBEDDING_DEVICE=cuda`
   - 10x faster embedding generation
   - Batch size: 256 (GPU) vs 32 (CPU)

2. **FAISS Strategy**:
   - Flat: <100K papers (exact search)
   - IVF: 100K-1M papers (approximate)
   - IVF+PQ: 1M-10M+ papers (compressed)

3. **Connection Pooling**:
   - Redis connection pool (50 connections)
   - HTTP/2 with connection reuse
   - Async I/O throughout

## Security Architecture

### Defense in Depth

**Layer 1: Input Validation**
- Marshmallow schemas
- HTML sanitization
- SQL injection prevention (parameterized queries)
- XSS prevention (output encoding)

**Layer 2: Authentication/Authorization**
- API key for admin endpoints
- Rate limiting per IP
- CORS configuration

**Layer 3: Transport Security**
- HTTPS only in production
- SSL certificate verification
- Secure session cookies

**Layer 4: Data Security**
- API keys in environment variables
- Sanitizing formatter (removes secrets from logs)
- No sensitive data in error messages

**Layer 5: Monitoring**
- Error tracking (Sentry)
- Audit logs
- Security scanning (Bandit, Trivy)

## Performance Metrics

### Target Metrics

| Metric | Target | Current |
|--------|--------|---------|
| API Response Time (p50) | <500ms | ~350ms |
| API Response Time (p95) | <1000ms | ~750ms |
| FAISS Search | <20ms | ~12ms |
| Embedding Generation | >500 texts/sec | ~650/sec (CPU) |
| Cache Hit Rate | >80% | ~87% |
| Memory Usage | <2GB | ~1.7GB |

### Bottlenecks

1. **External API Calls**: 200-500ms per API
   - **Solution**: Parallel requests, caching

2. **Embedding Generation**: CPU-bound
   - **Solution**: GPU acceleration, batching

3. **Text Preprocessing**: String operations
   - **Solution**: Cython compilation (future)

## Monitoring & Observability

### Logging

**Levels:**
- DEBUG: Development
- INFO: Production
- WARNING: Issues (not critical)
- ERROR: Failures (requires attention)

**Structured Logging:**
- JSON format in production
- Sanitizes sensitive data
- Request ID correlation

### Metrics

**Application Metrics:**
- Request count
- Response time (avg, p50, p95, p99)
- Error rate
- Cache hit rate

**System Metrics:**
- CPU usage
- Memory usage
- Disk I/O
- Network I/O

**Business Metrics:**
- Papers indexed
- Searches performed
- Plagiarism detected (by level)

### Tracing

**Future:** OpenTelemetry integration
- End-to-end request tracing
- Service dependency mapping
- Bottleneck identification

## Testing Strategy

### Test Pyramid
```
        ┌─────────────┐
        │   E2E (5%)  │  ← Full system tests
        ├─────────────┤
        │Integration  │  ← API tests (20%)
        │  (20%)      │
        ├─────────────┤
        │   Unit      │  ← Component tests (75%)
        │   (75%)     │
        └─────────────┘
```

### Test Coverage

**Target:** 80%+ code coverage

**Critical Paths:**
- Input validation (100%)
- Business logic (90%+)
- Data access (80%+)

## Future Enhancements

### Phase 1 (Q1 2024)
- [ ] PostgreSQL migration
- [ ] Distributed FAISS
- [ ] Celery background tasks
- [ ] OpenTelemetry tracing

### Phase 2 (Q2 2024)
- [ ] GraphQL API
- [ ] WebSocket support (real-time)
- [ ] Multi-tenancy
- [ ] Advanced analytics dashboard

### Phase 3 (Q3 2024)
- [ ] Machine learning model improvements
- [ ] Custom model training
- [ ] Citation graph analysis
- [ ] Automated report generation

---

**Last Updated:** 2024-11-27
**Version:** 2.1.0