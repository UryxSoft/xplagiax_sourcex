"""
Search Result Model
"""
import re
from dataclasses import dataclass
from typing import Optional
from app.models.enums import PlagiarismLevel
from app.utils.html_cleaner import strip_html


@dataclass
class SearchResult:
    """Represents a plagiarism detection result"""
    
    fuente: str
    texto_original: str
    texto_encontrado: str
    porcentaje_match: float
    documento_coincidente: str
    autor: str
    type_document: str
    plagiarism_level: str  # Will be converted to PlagiarismLevel
    publication_date: Optional[str] = None
    doi: Optional[str] = None
    url: Optional[str] = None
    
    def __post_init__(self):
        """Sanitize and validate fields"""
        # Sanitize text fields
        self.texto_original = strip_html(self.texto_original)
        self.texto_encontrado = strip_html(self.texto_encontrado)
        self.documento_coincidente = strip_html(self.documento_coincidente)
        self.autor = strip_html(self.autor)
        
        # Validate and convert plagiarism_level
        if isinstance(self.plagiarism_level, str):
            try:
                # Convert string to enum
                self.plagiarism_level = PlagiarismLevel(self.plagiarism_level)
            except ValueError:
                # If invalid, recalculate from similarity
                self.plagiarism_level = PlagiarismLevel.from_similarity(
                    self.porcentaje_match
                )
    
    @staticmethod
    def _sanitize_html(text: str) -> str:
        """Remove HTML tags for security"""
        if not text:
            return ""
        
        # Remove script tags
        text = re.sub(r'<script.*?</script>', '', text, flags=re.DOTALL | re.IGNORECASE)
        
        # Remove all HTML tags
        text = re.sub(r'<.*?>', '', text)
        
        return text.strip()
    
    def get_level_color(self) -> str:
        """Get color for this plagiarism level"""
        if isinstance(self.plagiarism_level, PlagiarismLevel):
            return self.plagiarism_level.get_color()
        return "#6c757d"  # Default gray
    
    def get_level_description(self) -> str:
        """Get description for this plagiarism level"""
        if isinstance(self.plagiarism_level, PlagiarismLevel):
            return self.plagiarism_level.get_description()
        return "Unknown level"
    
    def to_dict(self) -> dict:
        """Convert to dictionary"""
        return {
            'fuente': self.fuente,
            'texto_original': self.texto_original,
            'texto_encontrado': self.texto_encontrado,
            'porcentaje_match': self.porcentaje_match,
            'documento_coincidente': self.documento_coincidente,
            'autor': self.autor,
            'type_document': self.type_document,
            'plagiarism_level': self.plagiarism_level.value if isinstance(self.plagiarism_level, PlagiarismLevel) else self.plagiarism_level,
            'publication_date': self.publication_date,
            'doi': self.doi,
            'url': self.url
        }