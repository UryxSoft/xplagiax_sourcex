"""
Enums and Constants
"""
from enum import Enum
from typing import Dict, Tuple


class PlagiarismLevel(str, Enum):
    """
    Plagiarism severity levels based on similarity score
    
    Levels:
        HIGH: 85%+ similarity - Direct copy or minimal paraphrasing
        MEDIUM: 75-84% similarity - Significant overlap with modifications
        LOW: 70-74% similarity - Moderate similarity, possibly coincidental
    """
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    
    @classmethod
    def from_similarity(cls, similarity: float) -> 'PlagiarismLevel':
        """
        Determine plagiarism level from similarity score
        
        Args:
            similarity: Similarity score (0.0 - 1.0)
        
        Returns:
            PlagiarismLevel enum
        
        Examples:
            >>> PlagiarismLevel.from_similarity(0.92)
            <PlagiarismLevel.HIGH: 'high'>
            
            >>> PlagiarismLevel.from_similarity(0.78)
            <PlagiarismLevel.MEDIUM: 'medium'>
            
            >>> PlagiarismLevel.from_similarity(0.71)
            <PlagiarismLevel.LOW: 'low'>
        """
        if similarity >= 0.85:
            return cls.HIGH
        elif similarity >= 0.75:
            return cls.MEDIUM
        else:
            return cls.LOW
    
    def get_color(self) -> str:
        """
        Get color code for UI display
        
        Returns:
            Hex color code
        """
        colors = {
            self.HIGH: "#dc3545",      # Red
            self.MEDIUM: "#ffc107",    # Yellow/Orange
            self.LOW: "#28a745"        # Green
        }
        return colors[self]
    
    def get_description(self) -> str:
        """
        Get human-readable description
        
        Returns:
            Description string
        """
        descriptions = {
            self.HIGH: "High confidence plagiarism detected (85%+ similarity)",
            self.MEDIUM: "Moderate plagiarism detected (75-84% similarity)",
            self.LOW: "Low confidence match (70-74% similarity)"
        }
        return descriptions[self]
    
    def get_recommendation(self) -> str:
        """
        Get recommendation for this level
        
        Returns:
            Recommendation string
        """
        recommendations = {
            self.HIGH: "Immediate review required - likely plagiarism",
            self.MEDIUM: "Manual review recommended - significant similarity",
            self.LOW: "Review if concerned - may be coincidental or common phrasing"
        }
        return recommendations[self]


class DocumentType(str, Enum):
    """
    Academic document types
    """
    ARTICLE = "article"
    PREPRINT = "preprint"
    CONFERENCE = "conference_paper"
    THESIS = "thesis"
    BOOK = "book"
    CHAPTER = "book_chapter"
    REPORT = "report"
    PATENT = "patent"
    DATASET = "dataset"
    OTHER = "other"
    
    @classmethod
    def from_string(cls, doc_type: str) -> 'DocumentType':
        """
        Parse document type from string
        
        Args:
            doc_type: Document type string
        
        Returns:
            DocumentType enum (defaults to OTHER if unknown)
        """
        # Normalize input
        doc_type = doc_type.lower().replace('-', '_').replace(' ', '_')
        
        # Map common variations
        mapping = {
            'journal_article': cls.ARTICLE,
            'journal-article': cls.ARTICLE,
            'proceedings_article': cls.CONFERENCE,
            'conference_proceeding': cls.CONFERENCE,
            'monograph': cls.BOOK,
            'dissertation': cls.THESIS,
            'technical_report': cls.REPORT,
        }
        
        # Check if it's a direct match
        try:
            return cls(doc_type)
        except ValueError:
            # Check mapping
            return mapping.get(doc_type, cls.OTHER)


class SearchSource(str, Enum):
    """
    External API sources for academic search
    """
    CROSSREF = "crossref"
    PUBMED = "pubmed"
    SEMANTIC_SCHOLAR = "semantic_scholar"
    ARXIV = "arxiv"
    OPENALEX = "openalex"
    EUROPEPMC = "europepmc"
    DOAJ = "doaj"
    ZENODO = "zenodo"
    CORE = "core"
    BASE = "base"
    INTERNET_ARCHIVE = "internet_archive"
    UNPAYWALL = "unpaywall"
    HAL = "hal"
    
    def get_display_name(self) -> str:
        """Get human-readable name"""
        names = {
            self.CROSSREF: "Crossref",
            self.PUBMED: "PubMed",
            self.SEMANTIC_SCHOLAR: "Semantic Scholar",
            self.ARXIV: "arXiv",
            self.OPENALEX: "OpenAlex",
            self.EUROPEPMC: "Europe PMC",
            self.DOAJ: "DOAJ",
            self.ZENODO: "Zenodo",
            self.CORE: "CORE",
            self.BASE: "BASE",
            self.INTERNET_ARCHIVE: "Internet Archive",
            self.UNPAYWALL: "Unpaywall",
            self.HAL: "HAL"
        }
        return names.get(self, self.value.title())
    
    def get_url(self) -> str:
        """Get homepage URL"""
        urls = {
            self.CROSSREF: "https://www.crossref.org",
            self.PUBMED: "https://pubmed.ncbi.nlm.nih.gov",
            self.SEMANTIC_SCHOLAR: "https://www.semanticscholar.org",
            self.ARXIV: "https://arxiv.org",
            self.OPENALEX: "https://openalex.org",
            self.EUROPEPMC: "https://europepmc.org",
            self.DOAJ: "https://doaj.org",
            self.ZENODO: "https://zenodo.org",
            self.CORE: "https://core.ac.uk",
            self.BASE: "https://www.base-search.net",
            self.INTERNET_ARCHIVE: "https://archive.org/details/texts",
            self.UNPAYWALL: "https://unpaywall.org",
            self.HAL: "https://hal.science"
        }
        return urls.get(self, "")

    def get_description(self) -> str:
        """Get source description"""
        descriptions = {
            self.CROSSREF: "Metadata for scholarly publications with DOI",
            self.PUBMED: "Biomedical and life sciences literature",
            self.SEMANTIC_SCHOLAR: "AI-powered research tool",
            self.ARXIV: "Preprints in physics, math, CS, and more",
            self.OPENALEX: "Free and open catalog of scholarly papers",
            self.EUROPEPMC: "Life sciences literature database",
            self.DOAJ: "Directory of open access journals",
            self.ZENODO: "General-purpose research repository",
            self.CORE: "Aggregator of open access research",
            self.INTERNET_ARCHIVE: "Full-text scholarly articles archive",
            self.UNPAYWALL: "Open access versions of papers",
            self.HAL: "French national open science repository"
        }
        return descriptions.get(self, "")
    
    def requires_api_key(self) -> bool:
        """Check if source requires API key"""
        return self in [self.CORE, self.SEMANTIC_SCHOLAR]
    
    @classmethod
    def get_all_sources(cls) -> list:
        """Get list of all source names"""
        return [s.value for s in cls]
    
    @classmethod
    def get_free_sources(cls) -> list:
        """Get sources that don't require API keys"""
        return [s.value for s in cls if not s.requires_api_key()]


class ChunkingMode(str, Enum):
    """
    Text chunking strategies for plagiarism detection
    """
    SENTENCES = "sentences"
    SLIDING = "sliding"
    PARAGRAPHS = "paragraphs"
    FIXED = "fixed"
    
    def get_description(self) -> str:
        """Get description of chunking mode"""
        descriptions = {
            self.SENTENCES: "Split by sentences, combine until minimum word count",
            self.SLIDING: "Sliding window with configurable overlap",
            self.PARAGRAPHS: "Split by paragraph breaks",
            self.FIXED: "Fixed word count chunks"
        }
        return descriptions[self]


class LanguageCode(str, Enum):
    """
    Supported language codes (ISO 639-1)
    """
    ENGLISH = "en"
    SPANISH = "es"
    FRENCH = "fr"
    GERMAN = "de"
    PORTUGUESE = "pt"
    ITALIAN = "it"
    DUTCH = "nl"
    RUSSIAN = "ru"
    CHINESE = "zh"
    JAPANESE = "ja"
    KOREAN = "ko"
    ARABIC = "ar"
    
    def get_display_name(self) -> str:
        """Get language name"""
        names = {
            self.ENGLISH: "English",
            self.SPANISH: "Spanish",
            self.FRENCH: "French",
            self.GERMAN: "German",
            self.PORTUGUESE: "Portuguese",
            self.ITALIAN: "Italian",
            self.DUTCH: "Dutch",
            self.RUSSIAN: "Russian",
            self.CHINESE: "Chinese",
            self.JAPANESE: "Japanese",
            self.KOREAN: "Korean",
            self.ARABIC: "Arabic"
        }
        return names.get(self, self.value)
    
    def has_stopwords_support(self) -> bool:
        """Check if stopwords are available for this language"""
        supported = {
            self.ENGLISH, self.SPANISH, self.FRENCH, 
            self.GERMAN, self.PORTUGUESE, self.ITALIAN, self.DUTCH
        }
        return self in supported
    
    @classmethod
    def get_supported_languages(cls) -> list:
        """Get list of supported language codes"""
        return [lang.value for lang in cls]


class FAISSStrategy(str, Enum):
    """
    FAISS indexing strategies
    """
    FLAT_L2 = "flat_l2"
    FLAT_IP = "flat_ip"
    FLAT_IDMAP = "flat_idmap"
    IVF_FLAT = "ivf_flat"
    IVF_PQ = "ivf_pq"
    HNSW = "hnsw"
    
    def get_description(self) -> str:
        """Get strategy description"""
        descriptions = {
            self.FLAT_L2: "Flat index with L2 distance (exact search)",
            self.FLAT_IP: "Flat index with inner product (exact search)",
            self.FLAT_IDMAP: "Flat index with ID mapping (supports remove)",
            self.IVF_FLAT: "Inverted file index with flat quantizer (approximate)",
            self.IVF_PQ: "IVF with product quantization (memory efficient)",
            self.HNSW: "Hierarchical NSW graph (fast approximate)"
        }
        return descriptions[self]
    
    def supports_removal(self) -> bool:
        """Check if strategy supports vector removal"""
        return self in [self.FLAT_IDMAP]
    
    def is_approximate(self) -> bool:
        """Check if strategy uses approximate search"""
        return self in [self.IVF_FLAT, self.IVF_PQ, self.HNSW]
    
    def get_recommended_size(self) -> Tuple[int, int]:
        """
        Get recommended dataset size range (min, max)
        
        Returns:
            Tuple of (min_papers, max_papers)
        """
        sizes = {
            self.FLAT_L2: (0, 100_000),
            self.FLAT_IP: (0, 100_000),
            self.FLAT_IDMAP: (0, 100_000),
            self.IVF_FLAT: (10_000, 1_000_000),
            self.IVF_PQ: (100_000, 10_000_000),
            self.HNSW: (10_000, 10_000_000)
        }
        return sizes.get(self, (0, 100_000))


class CacheStrategy(str, Enum):
    """
    Cache invalidation strategies
    """
    TTL = "ttl"              # Time-to-live
    LRU = "lru"              # Least recently used
    LFU = "lfu"              # Least frequently used
    FIFO = "fifo"            # First in, first out
    NO_CACHE = "no_cache"    # Disable caching
    
    def get_description(self) -> str:
        """Get strategy description"""
        descriptions = {
            self.TTL: "Time-based expiration (default)",
            self.LRU: "Evict least recently accessed items",
            self.LFU: "Evict least frequently accessed items",
            self.FIFO: "Evict oldest items first",
            self.NO_CACHE: "No caching (always fetch fresh)"
        }
        return descriptions[self]


class HTTPMethod(str, Enum):
    """HTTP methods"""
    GET = "GET"
    POST = "POST"
    PUT = "PUT"
    DELETE = "DELETE"
    PATCH = "PATCH"
    HEAD = "HEAD"
    OPTIONS = "OPTIONS"


class ErrorCode(str, Enum):
    """
    Application error codes
    """
    # Validation errors (4000-4099)
    INVALID_INPUT = "ERR_4000"
    MISSING_FIELD = "ERR_4001"
    INVALID_LANGUAGE = "ERR_4002"
    TEXT_TOO_SHORT = "ERR_4003"
    TEXT_TOO_LONG = "ERR_4004"
    INVALID_THRESHOLD = "ERR_4005"
    INVALID_SOURCE = "ERR_4006"
    
    # Authentication errors (4010-4019)
    MISSING_API_KEY = "ERR_4010"
    INVALID_API_KEY = "ERR_4011"
    EXPIRED_API_KEY = "ERR_4012"
    
    # Rate limit errors (4290-4299)
    RATE_LIMIT_EXCEEDED = "ERR_4290"
    
    # Server errors (5000-5099)
    INTERNAL_ERROR = "ERR_5000"
    DATABASE_ERROR = "ERR_5001"
    CACHE_ERROR = "ERR_5002"
    FAISS_ERROR = "ERR_5003"
    EMBEDDING_ERROR = "ERR_5004"
    
    # External API errors (5030-5039)
    EXTERNAL_API_ERROR = "ERR_5030"
    EXTERNAL_API_TIMEOUT = "ERR_5031"
    EXTERNAL_API_UNAVAILABLE = "ERR_5032"
    
    def get_message(self) -> str:
        """Get default error message"""
        messages = {
            self.INVALID_INPUT: "Invalid input provided",
            self.MISSING_FIELD: "Required field is missing",
            self.INVALID_LANGUAGE: "Unsupported language code",
            self.TEXT_TOO_SHORT: "Text is too short for analysis",
            self.TEXT_TOO_LONG: "Text exceeds maximum length",
            self.INVALID_THRESHOLD: "Threshold must be between 0.0 and 1.0",
            self.INVALID_SOURCE: "Invalid or unsupported source",
            self.MISSING_API_KEY: "API key is required",
            self.INVALID_API_KEY: "Invalid API key",
            self.EXPIRED_API_KEY: "API key has expired",
            self.RATE_LIMIT_EXCEEDED: "Rate limit exceeded, please try again later",
            self.INTERNAL_ERROR: "Internal server error",
            self.DATABASE_ERROR: "Database operation failed",
            self.CACHE_ERROR: "Cache operation failed",
            self.FAISS_ERROR: "FAISS operation failed",
            self.EMBEDDING_ERROR: "Embedding generation failed",
            self.EXTERNAL_API_ERROR: "External API request failed",
            self.EXTERNAL_API_TIMEOUT: "External API request timed out",
            self.EXTERNAL_API_UNAVAILABLE: "External API is unavailable"
        }
        return messages.get(self, "Unknown error")


# ==================== CONSTANTS ====================

class Constants:
    """Application-wide constants"""
    
    # Text processing
    MIN_TEXT_LENGTH = 10
    MAX_TEXT_LENGTH = 10_000
    DEFAULT_CHUNK_SIZE = 20
    DEFAULT_CHUNK_OVERLAP = 5
    
    # Similarity thresholds
    MIN_THRESHOLD = 0.0
    MAX_THRESHOLD = 1.0
    DEFAULT_THRESHOLD = 0.70
    HIGH_SIMILARITY_THRESHOLD = 0.85
    MEDIUM_SIMILARITY_THRESHOLD = 0.75
    
    # FAISS settings
    EMBEDDING_DIMENSION = 384  # all-MiniLM-L6-v2
    DEFAULT_K_RESULTS = 10
    MAX_K_RESULTS = 100
    FAISS_BATCH_SIZE = 1000
    
    # Cache settings
    DEFAULT_CACHE_TTL = 3600  # 1 hour
    MAX_CACHE_TTL = 86400     # 24 hours
    
    # Rate limiting
    DEFAULT_RATE_LIMIT = 10    # requests per minute
    BURST_RATE_LIMIT = 20      # burst allowance
    RATE_LIMIT_WINDOW = 60     # seconds
    
    # API timeouts
    DEFAULT_API_TIMEOUT = 10.0   # seconds
    LONG_API_TIMEOUT = 30.0      # for slow APIs
    
    # Batch sizes
    DEFAULT_BATCH_SIZE = 32
    GPU_BATCH_SIZE = 256
    
    # Version
    API_VERSION = "2.1.0"
    
    # Supported formats
    SUPPORTED_LANGUAGES = [lang.value for lang in LanguageCode]
    SUPPORTED_SOURCES = [source.value for source in SearchSource]


# ==================== HELPER FUNCTIONS ====================

def get_plagiarism_stats() -> Dict[str, str]:
    """
    Get plagiarism level statistics with colors and descriptions
    
    Returns:
        Dict mapping level to metadata
    """
    return {
        level.value: {
            'color': level.get_color(),
            'description': level.get_description(),
            'recommendation': level.get_recommendation()
        }
        for level in PlagiarismLevel
    }


def get_source_metadata() -> Dict[str, Dict]:
    """
    Get all source metadata
    
    Returns:
        Dict mapping source name to metadata
    """
    return {
        source.value: {
            'display_name': source.get_display_name(),
            'url': source.get_url(),
            'requires_api_key': source.requires_api_key()
        }
        for source in SearchSource
    }


def validate_similarity_threshold(threshold: float) -> bool:
    """
    Validate similarity threshold
    
    Args:
        threshold: Threshold value
    
    Returns:
        True if valid, False otherwise
    """
    return Constants.MIN_THRESHOLD <= threshold <= Constants.MAX_THRESHOLD


def validate_language_code(lang_code: str) -> bool:
    """
    Validate language code
    
    Args:
        lang_code: Language code
    
    Returns:
        True if supported, False otherwise
    """
    return lang_code in Constants.SUPPORTED_LANGUAGES


def validate_source(source: str) -> bool:
    """
    Validate source name
    
    Args:
        source: Source name
    
    Returns:
        True if supported, False otherwise
    """
    return source in Constants.SUPPORTED_SOURCES


# ==================== EXPORT ====================

__all__ = [
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
    'get_plagiarism_stats',
    'get_source_metadata',
    'validate_similarity_threshold',
    'validate_language_code',
    'validate_source',
]