"""
Schemas for search endpoints
"""
from marshmallow import Schema, fields, validate, validates, ValidationError, post_load


class TextInputSchema(Schema):
    """Schema for individual text input [page, paragraph, text]"""
    page = fields.String(required=True, validate=validate.Length(max=50))
    paragraph = fields.String(required=True, validate=validate.Length(max=50))
    text = fields.String(required=True, validate=validate.Length(min=10, max=5000))
    
    @post_load
    def make_tuple(self, data, **kwargs):
        """Convert to tuple format"""
        return (data['page'], data['paragraph'], data['text'])


class SimilaritySearchSchema(Schema):
    """Schema for /api/similarity-search endpoint"""
    
    theme = fields.String(
        required=True,
        validate=validate.Length(min=1, max=200),
        metadata={"description": "Search theme/topic"}
    )
    
    idiom = fields.String(
        required=True,
        validate=validate.OneOf([
            'en', 'es', 'fr', 'de', 'pt', 'it', 'ru', 'zh', 'ja', 'ko'
        ]),
        metadata={"description": "Language code"}
    )
    
    texts = fields.List(
        fields.List(fields.String()),
        required=True,
        validate=validate.Length(min=1, max=100),
        metadata={"description": "List of [page, paragraph, text] arrays"}
    )
    
    threshold = fields.Float(
        missing=0.70,
        validate=validate.Range(min=0.0, max=1.0),
        metadata={"description": "Similarity threshold (0.0-1.0)"}
    )
    
    use_faiss = fields.Boolean(
        missing=True,
        metadata={"description": "Use FAISS for fast search"}
    )
    
    sources = fields.List(
        fields.String(),
        missing=None,
        validate=validate.ContainsOnly([
            'crossref', 'pubmed', 'semantic_scholar', 'arxiv',
            'openalex', 'europepmc', 'doaj', 'zenodo',
            'core', 'base', 'internet_archive', 'hal'
        ]),
        metadata={"description": "Specific sources to search (optional)"}
    )
    
    @validates('texts')
    def validate_texts(self, value):
        """Validate texts structure"""
        for idx, item in enumerate(value):
            if not isinstance(item, (list, tuple)):
                raise ValidationError(f"Text {idx} must be a list/tuple")
            
            if len(item) < 3:
                raise ValidationError(f"Text {idx} must have [page, para, text]")
            
            # Validate text length
            text = item[2]
            if len(text.strip()) < 10:
                raise ValidationError(f"Text {idx} is too short (min 10 chars)")


class PlagiarismCheckSchema(SimilaritySearchSchema):
    """Schema for /api/plagiarism-check endpoint"""
    
    chunk_mode = fields.String(
        missing='sentences',
        validate=validate.OneOf(['sentences', 'sliding']),
        metadata={"description": "Text chunking mode"}
    )
    
    min_chunk_words = fields.Integer(
        missing=15,
        validate=validate.Range(min=5, max=100),
        metadata={"description": "Minimum words per chunk"}
    )


class SearchResultSchema(Schema):
    """Schema for individual search result"""
    fuente = fields.String(required=True)
    texto_original = fields.String(required=True)
    texto_encontrado = fields.String(required=True)
    porcentaje_match = fields.Float(required=True)
    documento_coincidente = fields.String(required=True)
    autor = fields.String(required=True)
    type_document = fields.String(required=True)
    plagiarism_level = fields.String(required=True)
    publication_date = fields.String(allow_none=True)
    doi = fields.String(allow_none=True)
    url = fields.String(allow_none=True)


class SearchResponseSchema(Schema):
    """Schema for search response"""
    results = fields.List(fields.Nested(SearchResultSchema))
    count = fields.Integer()
    processed_texts = fields.Integer()
    threshold_used = fields.Float()
    faiss_enabled = fields.Boolean()


class PlagiarismResponseSchema(Schema):
    """Schema for plagiarism check response"""
    plagiarism_detected = fields.Boolean(required=True)
    chunks_analyzed = fields.Integer(required=True)
    total_matches = fields.Integer(required=True)
    
    summary = fields.Dict(
        keys=fields.String(),
        values=fields.Integer(),
        metadata={"description": "Count by plagiarism level"}
    )
    
    by_level = fields.Dict(
        keys=fields.String(),
        values=fields.Dict(),
        metadata={"description": "Results grouped by level"}
    )
    
    threshold_used = fields.Float()
    faiss_enabled = fields.Boolean()