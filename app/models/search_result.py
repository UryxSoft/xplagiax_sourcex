"""
Search Result Model
"""
import re
from dataclasses import dataclass
from typing import Optional


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
    plagiarism_level: str
    publication_date: Optional[str] = None
    doi: Optional[str] = None
    url: Optional[str] = None
    
    def __post_init__(self):
        """Sanitize text fields to prevent XSS"""
        self.texto_original = self._sanitize_html(self.texto_original)
        self.texto_encontrado = self._sanitize_html(self.texto_encontrado)
        self.documento_coincidente = self._sanitize_html(self.documento_coincidente)
        self.autor = self._sanitize_html(self.autor)
    
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
            'plagiarism_level': self.plagiarism_level,
            'publication_date': self.publication_date,
            'doi': self.doi,
            'url': self.url
        }