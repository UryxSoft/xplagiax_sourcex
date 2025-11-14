"""
Utilidades para procesamiento de texto y embeddings
"""
import re
import functools
import logging
from typing import List, Optional
import numpy as np

import nltk
from nltk.corpus import stopwords
from nltk.tokenize import word_tokenize
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity

from config import Config, CompiledPatterns

logger = logging.getLogger(__name__)

# Descargar stopwords si no están disponibles
try:
    stopwords.words('english')
except LookupError:
    nltk.download('stopwords', quiet=True)
    nltk.download('punkt', quiet=True)

# Cache global del modelo
_model: Optional[SentenceTransformer] = None


def get_model() -> SentenceTransformer:
    """
    Retorna instancia global del modelo de embeddings
    Lazy loading con caché para evitar cargar múltiples veces
    """
    global _model
    
    if _model is None:
        logger.info(f"Cargando modelo: {Config.EMBEDDING_MODEL}")
        try:
            _model = SentenceTransformer(Config.EMBEDDING_MODEL)
            logger.info("Modelo cargado exitosamente")
        except Exception as e:
            logger.error(f"Error cargando modelo: {e}")
            raise
    
    return _model


@functools.lru_cache(maxsize=10000)
def preprocess_text_cached(text: str) -> str:
    """
    Preprocesa texto con caché LRU
    
    Args:
        text: Texto a preprocesar
    
    Returns:
        Texto normalizado (lowercase, sin caracteres especiales)
    """
    if not text:
        return ""
    
    # Lowercase
    text = text.lower()
    
    # Eliminar caracteres especiales (mantener solo alfanuméricos y espacios)
    text = CompiledPatterns.NON_ALPHANUMERIC.sub(' ', text)
    
    # Normalizar espacios múltiples
    text = CompiledPatterns.WHITESPACE.sub(' ', text).strip()
    
    return text


# Stopwords por idioma (pre-cargados)
STOPWORDS_CACHE = {
    'en': set(stopwords.words('english')),
    'es': set(stopwords.words('spanish')),
    'fr': set(stopwords.words('french')),
    'de': set(stopwords.words('german')),
    'pt': set(stopwords.words('portuguese')),
    'it': set(stopwords.words('italian')),
    'ru': set(stopwords.words('russian'))
}


def remove_stopwords_optimized(text: str, language: str = 'en') -> str:
    """
    Remueve stopwords de forma optimizada con pre-carga
    
    Args:
        text: Texto preprocesado
        language: Código de idioma ('en', 'es', 'fr', etc)
    
    Returns:
        Texto sin stopwords
    """
    if not text:
        return ""
    
    # Obtener stopwords del idioma
    stop_words = STOPWORDS_CACHE.get(language, STOPWORDS_CACHE['en'])
    
    # Tokenizar (split simple, más rápido que word_tokenize)
    words = text.split()
    
    # Filtrar stopwords
    filtered_words = [w for w in words if w not in stop_words]
    
    return ' '.join(filtered_words)


def calculate_similarities_batch(
    queries: List[str], 
    documents: List[str]
) -> np.ndarray:
    """
    Calcula similitud coseno entre queries y documentos en batch
    
    Args:
        queries: Lista de queries (texto preprocesado)
        documents: Lista de documentos (texto preprocesado)
    
    Returns:
        Matriz numpy [len(queries), len(documents)] con similitudes
    """
    if not queries or not documents:
        logger.warning("calculate_similarities_batch llamado con listas vacías")
        return np.array([])
    
    try:
        model = get_model()
        
        # Generar embeddings en batch (mucho más rápido)
        query_embeddings = model.encode(
            queries,
            convert_to_tensor=False,
            show_progress_bar=False,
            batch_size=Config.EMBEDDING_BATCH_SIZE,
            normalize_embeddings=True
        )
        
        doc_embeddings = model.encode(
            documents,
            convert_to_tensor=False,
            show_progress_bar=False,
            batch_size=Config.EMBEDDING_BATCH_SIZE,
            normalize_embeddings=True
        )
        
        # Calcular similitud coseno (vectorizado con NumPy)
        similarities = cosine_similarity(query_embeddings, doc_embeddings)
        
        logger.debug(f"Similitudes calculadas", extra={
            "queries": len(queries),
            "documents": len(documents),
            "shape": similarities.shape
        })
        
        return similarities
    
    except Exception as e:
        logger.error(f"Error calculando similitudes: {e}")
        # Retornar matriz de ceros como fallback
        return np.zeros((len(queries), len(documents)))


def calculate_similarity_single(text1: str, text2: str) -> float:
    """
    Calcula similitud entre dos textos
    
    Args:
        text1: Primer texto
        text2: Segundo texto
    
    Returns:
        Similitud entre 0 y 1
    """
    try:
        similarities = calculate_similarities_batch([text1], [text2])
        return float(similarities[0][0])
    except Exception as e:
        logger.error(f"Error calculando similitud: {e}")
        return 0.0


def truncate_text(text: str, max_length: int = None) -> str:
    """
    Trunca texto a longitud máxima
    
    Args:
        text: Texto a truncar
        max_length: Longitud máxima (default: Config.MAX_TEXT_LENGTH)
    
    Returns:
        Texto truncado
    """
    if max_length is None:
        max_length = Config.MAX_TEXT_LENGTH
    
    if len(text) <= max_length:
        return text
    
    return text[:max_length]


def batch_texts(texts: List[str], batch_size: int = None) -> List[List[str]]:
    """
    Divide lista de textos en batches
    
    Args:
        texts: Lista de textos
        batch_size: Tamaño de batch (default: Config.EMBEDDING_BATCH_SIZE)
    
    Returns:
        Lista de batches
    """
    if batch_size is None:
        batch_size = Config.EMBEDDING_BATCH_SIZE
    
    batches = []
    for i in range(0, len(texts), batch_size):
        batches.append(texts[i:i + batch_size])
    
    return batches


def normalize_score(score: float) -> float:
    """
    Normaliza score a rango 0-100
    
    Args:
        score: Score entre 0-1
    
    Returns:
        Score entre 0-100
    """
    return round(float(score) * 100, 1)


def get_top_n_indices(similarities: np.ndarray, n: int = 10) -> List[int]:
    """
    Obtiene índices de los top N scores más altos
    
    Args:
        similarities: Array de similitudes
        n: Número de top resultados
    
    Returns:
        Lista de índices ordenados por similitud (descendente)
    """
    if len(similarities) == 0:
        return []
    
    # argsort devuelve índices ordenados ascendente, invertir con [::-1]
    top_indices = np.argsort(similarities)[::-1][:n]
    
    return top_indices.tolist()


def filter_by_threshold(
    similarities: np.ndarray, 
    threshold: float = None
) -> np.ndarray:
    """
    Filtra similitudes por threshold
    
    Args:
        similarities: Array de similitudes
        threshold: Umbral mínimo (default: Config.SIMILARITY_THRESHOLD)
    
    Returns:
        Índices de similitudes por encima del threshold
    """
    if threshold is None:
        threshold = Config.SIMILARITY_THRESHOLD
    
    return np.where(similarities >= threshold)[0]


# Cache de modelos adicionales (para futuras expansiones)
_models_cache = {}


def get_multilingual_model() -> SentenceTransformer:
    """
    Retorna modelo multilingüe (para futuro uso)
    """
    if 'multilingual' not in _models_cache:
        logger.info("Cargando modelo multilingüe")
        _models_cache['multilingual'] = SentenceTransformer('paraphrase-multilingual-MiniLM-L12-v2')
    
    return _models_cache['multilingual']


def clear_model_cache():
    """
    Limpia caché de modelos (útil para pruebas o reiniciar)
    """
    global _model, _models_cache
    
    logger.info("Limpiando caché de modelos")
    
    if _model is not None:
        del _model
        _model = None
    
    _models_cache.clear()
    
    import gc
    gc.collect()


# Funciones de validación
def is_valid_text(text: str, min_length: int = 10) -> bool:
    """
    Valida que el texto sea válido para procesamiento
    
    Args:
        text: Texto a validar
        min_length: Longitud mínima requerida
    
    Returns:
        True si es válido
    """
    if not text or not isinstance(text, str):
        return False
    
    # Después de limpieza
    cleaned = text.strip()
    
    if len(cleaned) < min_length:
        return False
    
    # Debe tener al menos algunas palabras
    words = cleaned.split()
    if len(words) < 3:
        return False
    
    return True


def extract_keywords(text: str, n: int = 5) -> List[str]:
    """
    Extrae palabras clave del texto (simple - por frecuencia)
    
    Args:
        text: Texto a analizar
        n: Número de keywords
    
    Returns:
        Lista de keywords
    """
    from collections import Counter
    
    # Preprocesar
    processed = preprocess_text_cached(text)
    
    # Remover stopwords
    words = processed.split()
    stop_words = STOPWORDS_CACHE.get('en', set())
    filtered = [w for w in words if w not in stop_words and len(w) > 3]
    
    # Contar frecuencias
    counter = Counter(filtered)
    
    # Top N
    keywords = [word for word, _ in counter.most_common(n)]
    
    return keywords


# Funciones de debugging
def debug_text_processing(text: str, language: str = 'en') -> dict:
    """
    Muestra paso a paso el procesamiento de texto
    
    Args:
        text: Texto a procesar
        language: Idioma
    
    Returns:
        Dict con cada paso del procesamiento
    """
    steps = {
        "original": text,
        "length_original": len(text),
        "preprocessed": preprocess_text_cached(text),
        "without_stopwords": remove_stopwords_optimized(preprocess_text_cached(text), language),
        "word_count_original": len(text.split()),
        "word_count_final": len(remove_stopwords_optimized(preprocess_text_cached(text), language).split()),
        "keywords": extract_keywords(text)
    }
    
    return steps

"""""
if __name__ == "__main__":
    # Tests básicos
    print("=== Test utils.py ===\n")
    
    # Test 1: Preprocesamiento
    text = "This is a TEST! With special characters: @#$%"
    print(f"Original: {text}")
    print(f"Processed: {preprocess_text_cached(text)}")
    print()
    
    # Test 2: Stopwords
    text_clean = preprocess_text_cached(text)
    print(f"With stopwords: {text_clean}")
    print(f"Without stopwords: {remove_stopwords_optimized(text_clean, 'en')}")
    print()
    
    # Test 3: Similitud
    text1 = "machine learning algorithms"
    text2 = "algorithms for machine learning"
    sim = calculate_similarity_single(text1, text2)
    print(f"Similitud entre '{text1}' y '{text2}': {sim:.2%}")
    print()
    
    # Test 4: Keywords
    long_text = "Machine learning is a subset of artificial intelligence. Neural networks are computational models inspired by biological neurons."
    keywords = extract_keywords(long_text)
    print(f"Keywords: {keywords}")
    print()
    
    # Test 5: Debug
    debug_info = debug_text_processing(long_text)
    print("Debug info:")
    for key, value in debug_info.items():
        print(f"  {key}: {value}")
    
    print("\n Tests completados")

"""""