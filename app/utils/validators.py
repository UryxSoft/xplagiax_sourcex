"""
Input Validators - Sanitize and validate user input
"""
import re
import logging
from typing import List, Optional, Tuple
from app.models.enums import Constants, LanguageCode, SearchSource

logger = logging.getLogger(__name__)


def sanitize_string(text: str, max_length: int = 10000) -> str:
    """
    Sanitize user input string
    
    Args:
        text: Input text
        max_length: Maximum allowed length
    
    Returns:
        Sanitized text
    
    Examples:
        >>> sanitize_string("<script>alert('xss')</script>Hello")
        'Hello'
        >>> sanitize_string("A" * 20000, max_length=100)
        'AAAA...'  # Truncated to 100 chars
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
    
    # Remove excessive whitespace
    text = re.sub(r'\s+', ' ', text)
    
    return text.strip()


def validate_similarity_input(
    theme: str,
    idiom: str,
    texts: List[Tuple[str, str, str]],
    threshold: float,
    sources: Optional[List[str]] = None
) -> Tuple[bool, Optional[str]]:
    """
    Validate similarity search input
    
    Args:
        theme: Search theme
        idiom: Language code
        texts: List of (page, paragraph, text) tuples
        threshold: Similarity threshold
        sources: Optional list of sources
    
    Returns:
        Tuple of (is_valid, error_message)
    
    Examples:
        >>> valid, error = validate_similarity_input(
        ...     theme="AI",
        ...     idiom="en",
        ...     texts=[("1", "1", "This is a test text with enough words.")],
        ...     threshold=0.7
        ... )
        >>> valid
        True
        >>> error is None
        True
    """
    # Validate theme
    if not theme or len(theme.strip()) == 0:
        return False, "Theme is required"
    
    if len(theme) > 200:
        return False, "Theme is too long (max 200 characters)"
    
    # Validate language
    if idiom not in Constants.SUPPORTED_LANGUAGES:
        return False, f"Unsupported language: {idiom}. Supported: {Constants.SUPPORTED_LANGUAGES}"
    
    # Validate texts
    if not texts or len(texts) == 0:
        return False, "At least one text is required"
    
    if len(texts) > 100:
        return False, "Too many texts (max 100)"
    
    for idx, item in enumerate(texts):
        if not isinstance(item, (list, tuple)):
            return False, f"Text {idx} must be a list/tuple"
        
        if len(item) < 3:
            return False, f"Text {idx} must have [page, paragraph, text]"
        
        page, paragraph, text = item[0], item[1], item[2]
        
        # Validate text length
        if len(text.strip()) < Constants.MIN_TEXT_LENGTH:
            return False, f"Text {idx} is too short (min {Constants.MIN_TEXT_LENGTH} characters)"
        
        if len(text) > Constants.MAX_TEXT_LENGTH:
            return False, f"Text {idx} is too long (max {Constants.MAX_TEXT_LENGTH} characters)"
    
    # Validate threshold
    if not (Constants.MIN_THRESHOLD <= threshold <= Constants.MAX_THRESHOLD):
        return False, f"Threshold must be between {Constants.MIN_THRESHOLD} and {Constants.MAX_THRESHOLD}"
    
    # Validate sources
    if sources:
        invalid_sources = [s for s in sources if s not in Constants.SUPPORTED_SOURCES]
        if invalid_sources:
            return False, f"Invalid sources: {invalid_sources}. Supported: {Constants.SUPPORTED_SOURCES}"
    
    return True, None


def validate_sources(sources: List[str]) -> Tuple[bool, Optional[str]]:
    """
    Validate source list
    
    Args:
        sources: List of source names
    
    Returns:
        Tuple of (is_valid, error_message)
    
    Examples:
        >>> valid, error = validate_sources(["crossref", "pubmed"])
        >>> valid
        True
    """
    if not sources:
        return True, None
    
    if not isinstance(sources, list):
        return False, "Sources must be a list"
    
    invalid_sources = [
        s for s in sources
        if s not in Constants.SUPPORTED_SOURCES
    ]
    
    if invalid_sources:
        return False, (
            f"Invalid sources: {invalid_sources}. "
            f"Supported: {Constants.SUPPORTED_SOURCES}"
        )
    
    return True, None


def validate_threshold(threshold: float) -> Tuple[bool, Optional[str]]:
    """
    Validate threshold value
    
    Args:
        threshold: Threshold value
    
    Returns:
        Tuple of (is_valid, error_message)
    """
    if not isinstance(threshold, (int, float)):
        return False, "Threshold must be a number"
    
    if not (Constants.MIN_THRESHOLD <= threshold <= Constants.MAX_THRESHOLD):
        return False, (
            f"Threshold must be between {Constants.MIN_THRESHOLD} "
            f"and {Constants.MAX_THRESHOLD}"
        )
    
    return True, None


def validate_language(language: str) -> Tuple[bool, Optional[str]]:
    """
    Validate language code
    
    Args:
        language: Language code
    
    Returns:
        Tuple of (is_valid, error_message)
    """
    if not language:
        return False, "Language is required"
    
    if language not in Constants.SUPPORTED_LANGUAGES:
        return False, (
            f"Unsupported language: {language}. "
            f"Supported: {Constants.SUPPORTED_LANGUAGES}"
        )
    
    return True, None