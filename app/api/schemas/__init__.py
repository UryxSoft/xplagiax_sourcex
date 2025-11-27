"""
Request/Response schemas for validation
"""
from app.api.schemas.search_schema import (
    SimilaritySearchSchema,
    PlagiarismCheckSchema,
    SearchResponseSchema
)
from app.api.schemas.faiss_schema import (
    FAISSSearchSchema,
    FAISSStatsSchema
)

__all__ = [
    'SimilaritySearchSchema',
    'PlagiarismCheckSchema',
    'SearchResponseSchema',
    'FAISSSearchSchema',
    'FAISSStatsSchema',
]