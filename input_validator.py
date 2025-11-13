"""
Validador de entrada para prevenir ataques y errores
"""
import re
from typing import List, Tuple
from markupsafe import escape

# Constantes de validación
MAX_THEME_LENGTH = 200
MAX_TEXT_LENGTH = 5000
MAX_TEXTS_PER_REQUEST = 100
MAX_PAGE_LENGTH = 50
MAX_PARAGRAPH_LENGTH = 50
ALLOWED_IDIOMS = ['en', 'es', 'fr', 'de', 'pt', 'it', 'ru', 'zh', 'ja', 'ko']

# Regex para sanitización
ALPHA_NUMERIC_PATTERN = re.compile(r'[^\w\s-]')
WHITESPACE_PATTERN = re.compile(r'\s+')


def sanitize_string(text: str, max_length: int, allow_special_chars: bool = False) -> str:
    """
    Sanitiza una cadena de texto
    
    Args:
        text: Texto a sanitizar
        max_length: Longitud máxima
        allow_special_chars: Si permite caracteres especiales
    
    Returns:
        Texto sanitizado
    """
    if not isinstance(text, str):
        text = str(text)
    
    # Escapar HTML
    text = escape(text)
    
    # Eliminar caracteres especiales si no están permitidos
    if not allow_special_chars:
        text = ALPHA_NUMERIC_PATTERN.sub(' ', text)
    
    # Normalizar espacios
    text = WHITESPACE_PATTERN.sub(' ', text).strip()
    
    # Truncar a longitud máxima
    if len(text) > max_length:
        text = text[:max_length]
    
    return text


def validate_similarity_input(data: List) -> Tuple[str, str, List[Tuple[str, str, str]]]:
    """
    Valida y sanitiza la entrada del endpoint similarity-search
    
    Args:
        data: Lista [theme, idiom, [[page, paragraph, text], ...]]
    
    Returns:
        Tupla (theme, idiom, validated_texts)
    
    Raises:
        ValueError: Si la entrada es inválida
    """
    if not isinstance(data, list):
        raise ValueError("data debe ser una lista")
    
    if len(data) < 3:
        raise ValueError("data debe contener al menos 3 elementos: [theme, idiom, texts]")
    
    # Validar theme
    theme_raw = data[0]
    if not theme_raw or (isinstance(theme_raw, str) and not theme_raw.strip()):
        raise ValueError("theme no puede estar vacío")
    
    theme = sanitize_string(theme_raw, MAX_THEME_LENGTH, allow_special_chars=False)
    
    if not theme:
        raise ValueError("theme inválido después de sanitización")
    
    # Validar idiom
    idiom_raw = str(data[1])[:2].lower()
    
    if idiom_raw not in ALLOWED_IDIOMS:
        # Default a inglés si el idioma no es soportado
        idiom = 'en'
    else:
        idiom = idiom_raw
    
    # Validar texts
    texts_raw = data[2]
    
    if not isinstance(texts_raw, list):
        raise ValueError("texts debe ser una lista")
    
    if len(texts_raw) == 0:
        raise ValueError("texts no puede estar vacío")
    
    if len(texts_raw) > MAX_TEXTS_PER_REQUEST:
        raise ValueError(f"Máximo {MAX_TEXTS_PER_REQUEST} textos permitidos por request")
    
    # Validar cada texto
    validated_texts = []
    
    for idx, item in enumerate(texts_raw[:MAX_TEXTS_PER_REQUEST]):
        if not isinstance(item, (list, tuple)):
            raise ValueError(f"Texto {idx} debe ser una lista o tupla")
        
        if len(item) < 3:
            raise ValueError(f"Texto {idx} debe tener al menos 3 elementos: [page, paragraph, text]")
        
        # Extraer y sanitizar campos
        page = sanitize_string(item[0], MAX_PAGE_LENGTH, allow_special_chars=False)
        paragraph = sanitize_string(item[1], MAX_PARAGRAPH_LENGTH, allow_special_chars=False)
        text = sanitize_string(item[2], MAX_TEXT_LENGTH, allow_special_chars=True)
        
        # Validar que el texto no esté vacío después de sanitización
        if not text or len(text.strip()) < 10:
            # Ignorar textos muy cortos
            continue
        
        validated_texts.append((page, paragraph, text))
    
    if len(validated_texts) == 0:
        raise ValueError("No se encontraron textos válidos después de la validación")
    
    return theme, idiom, validated_texts


def validate_sources(sources: List[str]) -> List[str]:
    """
    Valida lista de fuentes
    
    Args:
        sources: Lista de nombres de fuentes
    
    Returns:
        Lista de fuentes válidas
    """
    VALID_SOURCES = [
        "crossref", "pubmed", "semantic_scholar", "arxiv",
        "openalex", "europepmc", "doaj", "zenodo"
    ]
    
    if not isinstance(sources, list):
        return []
    
    validated = []
    for source in sources:
        if isinstance(source, str) and source.lower() in VALID_SOURCES:
            validated.append(source.lower())
    
    return validated