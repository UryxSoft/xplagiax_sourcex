"""
Data Models
"""
from app.models.search_result import SearchResult
from app.models.paper import Paper
from app.models.enums import (
    PlagiarismLevel,
    DocumentType,
    SearchSource,
    ChunkingMode,
    LanguageCode,
    FAISSStrategy,
    CacheStrategy,
    HTTPMethod,
    ErrorCode,
    Constants
)

__all__ = [
    'SearchResult',
    'Paper',
    'PlagiarismLevel',
    'DocumentType',
    'SearchSource',
    'ChunkingMode',
    'LanguageCode',
    'FAISSStrategy',
    'CacheStrategy',
    'HTTPMethod',
    'ErrorCode',
    'Constants',
]