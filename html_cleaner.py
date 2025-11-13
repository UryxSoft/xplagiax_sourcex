"""
Limpiador de HTML en abstracts
"""
import re
from html import unescape

def clean_html(text: str) -> str:
    """
    Elimina tags HTML y decodifica entidades
    """
    if not text:
        return ""
    
    # Eliminar tags HTML
    text = re.sub(r'<[^>]+>', '', text)
    
    # Decodificar entidades HTML (&nbsp;, &lt;, etc)
    text = unescape(text)
    
    # Normalizar espacios
    text = re.sub(r'\s+', ' ', text).strip()
    
    return text