"""
Academic Paper Model
"""
from dataclasses import dataclass
from typing import Optional


@dataclass
class Paper:
    """Represents an academic paper"""
    
    title: str
    authors: str
    source: str
    type: str = 'article'
    abstract: Optional[str] = None
    doi: Optional[str] = None
    url: Optional[str] = None
    date: Optional[str] = None
    
    def to_dict(self) -> dict:
        """Convert to dictionary"""
        return {
            'title': self.title,
            'authors': self.authors,
            'abstract': self.abstract,
            'doi': self.doi,
            'url': self.url,
            'date': self.date,
            'type': self.type,
            'source': self.source
        }