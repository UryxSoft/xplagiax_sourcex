"""
Stopwords Removal - Optimized with caching
"""
import logging
from functools import lru_cache
from typing import Set

logger = logging.getLogger(__name__)

# Supported languages
SUPPORTED_LANGUAGES = {
    'en', 'es', 'fr', 'de', 'it', 'pt', 'nl'
}


@lru_cache(maxsize=10)
def get_stopwords(language: str) -> Set[str]:
    """
    Get stopwords for a language (cached)
    
    Args:
        language: Language code (en, es, fr, etc.)
    
    Returns:
        Set of stopwords
    """
    if language not in SUPPORTED_LANGUAGES:
        logger.warning(
            f"Language '{language}' not supported, falling back to English"
        )
        language = 'en'
    
    try:
        from nltk.corpus import stopwords
        return set(stopwords.words(_language_code_to_nltk(language)))
    
    except Exception as e:
        logger.error(f"Error loading stopwords: {e}")
        return set()


def _language_code_to_nltk(lang_code: str) -> str:
    """Convert language code to NLTK language name"""
    mapping = {
        'en': 'english',
        'es': 'spanish',
        'fr': 'french',
        'de': 'german',
        'it': 'italian',
        'pt': 'portuguese',
        'nl': 'dutch'
    }
    
    return mapping.get(lang_code, 'english')


def remove_stopwords_optimized(text: str, language: str = 'en') -> str:
    """
    Remove stopwords from text (optimized with caching)
    
    Args:
        text: Input text
        language: Language code
    
    Returns:
        Text with stopwords removed
    """
    if not text:
        return ""
    
    stopwords_set = get_stopwords(language)
    
    if not stopwords_set:
        return text
    
    words = text.split()
    filtered_words = [w for w in words if w.lower() not in stopwords_set]
    
    return ' '.join(filtered_words)