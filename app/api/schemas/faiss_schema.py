"""
Schemas for FAISS endpoints
"""
from marshmallow import Schema, fields, validate


class FAISSSearchSchema(Schema):
    """Schema for /api/faiss/search endpoint"""
    
    query = fields.String(
        required=True,
        validate=validate.Length(min=1, max=500),
        metadata={"description": "Search query"}
    )
    
    k = fields.Integer(
        missing=10,
        validate=validate.Range(min=1, max=100),
        metadata={"description": "Number of results to return"}
    )
    
    threshold = fields.Float(
        missing=0.7,
        validate=validate.Range(min=0.0, max=1.0),
        metadata={"description": "Similarity threshold"}
    )


class FAISSStatsSchema(Schema):
    """Schema for FAISS stats response"""
    total_papers = fields.Integer()
    dimension = fields.Integer()
    metadata_count = fields.Integer()
    unique_hashes = fields.Integer()
    strategy = fields.String()
    corrupted = fields.Boolean()
    has_duplicates = fields.Boolean()


class FAISSSearchResponseSchema(Schema):
    """Schema for FAISS search response"""
    query = fields.String()
    results = fields.List(fields.Dict())
    count = fields.Integer()