"""
Configuración del sistema
"""
import re


class Config:
    # Modelo y procesamiento
    EMBEDDING_MODEL = "sentence-transformers/all-MiniLM-L6-v2"
    SIMILARITY_THRESHOLD = 0.70
    MAX_TEXT_LENGTH = 512
    EMBEDDING_BATCH_SIZE = 32
    
    # HTTP y timeouts
    REQUEST_TIMEOUT = 8.0
    POOL_CONNECTIONS = 20
    POOL_MAXSIZE = 50
    MAX_RESULTS_PER_SOURCE = 5
    
    # Caché
    CACHE_TTL = 86400  # 24 horas
    CACHE_BINARY = True
    
    # Rate limiting (por minuto)
    RATE_LIMITS = {
        "crossref": 50,
        "europepmc": 50,
        "pubmed": 10,
        "openalex": 100,
        "semantic_scholar": 100,
        "arxiv": 30,
        "doaj": 30,
        "core": 30,
        "biorxiv": 30,
        "zenodo": 60,
        "osf": 50,
    }
    
    # Circuit breaker
    CIRCUIT_FAILURE_THRESHOLD = 3
    CIRCUIT_TIMEOUT = 60
    
    # Threading
    MAX_WORKERS = 4


class CompiledPatterns:
    """Regex pre-compilados"""
    WHITESPACE = re.compile(r'\s+')
    NON_ALPHANUMERIC = re.compile(r'[^\w\s]')
    MULTIPLE_SPACES = re.compile(r' {2,}')
