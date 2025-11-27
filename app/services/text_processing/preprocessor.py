"""
Text Preprocessor - Clean and normalize text
"""
import re
import logging
from typing import Set
from app.utils.stopwords import remove_stopwords_optimized

logger = logging.getLogger(__name__)


class TextPreprocessor:
    """Preprocess text for similarity comparison"""
    
    def __init__(self):
        self.url_pattern = re.compile(r'https?://\S+|www\.\S+')
        self.email_pattern = re.compile(r'\S+@\S+')
        self.number_pattern = re.compile(r'\b\d+\b')
        self.special_chars_pattern = re.compile(r'[^\w\s]')
        self.whitespace_pattern = re.compile(r'\s+')
    
    def preprocess(self, text: str, language: str = 'en') -> str:
        """
        Preprocess text for similarity comparison
        
        Args:
            text: Input text
            language: Language code (en, es, fr, etc.)
        
        Returns:
            Cleaned and normalized text
        """
        if not text or not text.strip():
            return ""
        
        # 1. Lowercase
        text = text.lower()
        
        # 2. Remove URLs
        text = self.url_pattern.sub('', text)
        
        # 3. Remove emails
        text = self.email_pattern.sub('', text)
        
        # 4. Remove numbers (optional - can be configured)
        # text = self.number_pattern.sub('', text)
        
        # 5. Remove special characters (keep spaces and alphanumeric)
        text = self.special_chars_pattern.sub(' ', text)
        
        # 6. Normalize whitespace
        text = self.whitespace_pattern.sub(' ', text)
        
        # 7. Remove stopwords
        text = remove_stopwords_optimized(text, language)
        
        # 8. Strip
        text = text.strip()
        
        return text
    
    def sanitize_input(self, text: str, max_length: int = 10000) -> str:
        """
        Sanitize user input (security)
        
        Args:
            text: Input text
            max_length: Maximum allowed length
        
        Returns:
            Sanitized text
        """
        if not text:
            return ""
        
        # Truncate
        text = text[:max_length]
        
        # Remove potential XSS
        text = re.sub(r'<script.*?</script>', '', text, flags=re.DOTALL | re.IGNORECASE)
        text = re.sub(r'<.*?>', '', text)
        
        # Remove null bytes
        text = text.replace('\x00', '')
        
        return text.strip()