"""
Utilidades de procesamiento de texto
"""
from functools import lru_cache
from typing import Set, List

import nltk
from nltk.corpus import stopwords
from nltk.tokenize import word_tokenize
import numpy as np
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity

from config import Config, CompiledPatterns


# Inicialización NLTK
try:
    nltk.data.find('tokenizers/punkt')
    nltk.data.find('corpora/stopwords')
except LookupError:
    nltk.download('punkt', quiet=True)
    nltk.download('stopwords', quiet=True)


# Modelo de embeddings con lazy loading
_model = None

def get_model() -> SentenceTransformer:
    """Lazy loading del modelo (ahorra memoria en workers)"""
    global _model
    if _model is None:
        print("📊 Cargando modelo de embeddings...")
        _model = SentenceTransformer(Config.EMBEDDING_MODEL)
        _model.max_seq_length = Config.MAX_TEXT_LENGTH
    return _model


@lru_cache(maxsize=10000)
def preprocess_text_cached(text: str) -> str:
    """
    Preprocesa texto con caché LRU
    """
    text = text.lower()
    text = CompiledPatterns.NON_ALPHANUMERIC.sub(' ', text)
    text = CompiledPatterns.MULTIPLE_SPACES.sub(' ', text).strip()
    
    # Limitar longitud
    words = text.split()
    if len(words) > Config.MAX_TEXT_LENGTH:
        text = ' '.join(words[:Config.MAX_TEXT_LENGTH])
    
    return text


@lru_cache(maxsize=100)
def get_stopwords_set(language: str) -> Set[str]:
    """Caché de stopwords por idioma"""
    lang_map = {
        'en': 'english', 'es': 'spanish', 'fr': 'french',
        'de': 'german', 'pt': 'portuguese'
    }
    stop_lang = lang_map.get(language[:2], 'english')
    return set(stopwords.words(stop_lang))


def remove_stopwords_optimized(text: str, language: str = 'english') -> str:
    """
    Optimización: Operación vectorizada con set lookup O(1)
    """
    try:
        stop_words = get_stopwords_set(language)
        words = word_tokenize(text)
        filtered = [w for w in words if w.lower() not in stop_words]
        return ' '.join(filtered)
    except:
        return text


def calculate_similarities_batch(texts1: List[str], texts2: List[str]) -> np.ndarray:
    """
    Calcula similitudes en batch (VECTORIZADO)
    
    Returns:
        Array de similitudes [len(texts1) x len(texts2)]
    """
    model = get_model()
    
    # Embeddings en batch
    emb1 = model.encode(
        texts1, 
        convert_to_tensor=False,
        batch_size=Config.EMBEDDING_BATCH_SIZE,
        show_progress_bar=False
    )
    emb2 = model.encode(
        texts2, 
        convert_to_tensor=False,
        batch_size=Config.EMBEDDING_BATCH_SIZE,
        show_progress_bar=False
    )
    
    # Similitud coseno vectorizada
    similarities = cosine_similarity(emb1, emb2)
    return similarities