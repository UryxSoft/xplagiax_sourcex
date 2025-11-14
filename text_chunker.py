"""
Fragmentador de texto para detectar plagio parcial
"""
from typing import List, Tuple
import re


def chunk_text_by_sentences(text: str, min_words: int = 15) -> List[Tuple[int, str]]:
    """
    Divide texto en oraciones para detectar plagio parcial
    
    Args:
        text: Texto completo a fragmentar
        min_words: Mínimo de palabras por oración
    
    Returns:
        Lista de (sentence_index, sentence_text)
    """
    # Dividir por puntos, pero mantener puntos en abreviaciones
    # Patrón: punto seguido de espacio y mayúscula
    sentences = re.split(r'(?<=[.!?])\s+(?=[A-Z])', text)
    
    chunks = []
    for idx, sentence in enumerate(sentences):
        # Limpiar espacios
        sentence = sentence.strip()
        
        # Contar palabras
        words = sentence.split()
        
        # Solo agregar si tiene suficientes palabras
        if len(words) >= min_words:
            chunks.append((idx, sentence))
    
    # Si no hay chunks (texto muy corto), retornar texto completo
    if not chunks and text.strip():
        chunks.append((0, text.strip()))
    
    return chunks


def chunk_text_sliding_window(text: str, window_size: int = 50, overlap: int = 10) -> List[str]:
    """
    Ventana deslizante para capturar plagio que cruza oraciones
    
    Args:
        text: Texto completo
        window_size: Palabras por ventana
        overlap: Palabras de overlap entre ventanas
    
    Returns:
        Lista de chunks de texto
    """
    words = text.split()
    
    # Si el texto es más corto que la ventana, retornar completo
    if len(words) <= window_size:
        return [text]
    
    chunks = []
    start = 0
    
    while start < len(words):
        end = min(start + window_size, len(words))
        chunk = ' '.join(words[start:end])
        chunks.append(chunk)
        
        # Si llegamos al final, salir
        if end >= len(words):
            break
        
        # Avanzar con overlap
        start += (window_size - overlap)
    
    return chunks

#this
def analyze_text_structure(text: str) -> dict:
    """
    Analiza estructura del texto para determinar mejor estrategia
    
    Returns:
        {
            'total_words': int,
            'total_sentences': int,
            'avg_words_per_sentence': float,
            'recommended_strategy': 'sentences' | 'sliding'
        }
    """
    sentences = re.split(r'(?<=[.!?])\s+(?=[A-Z])', text)
    words = text.split()
    
    total_sentences = len(sentences)
    total_words = len(words)
    avg_words = total_words / total_sentences if total_sentences > 0 else 0
    
    # Si las oraciones son muy largas, usar sliding window
    if avg_words > 40:
        recommended = 'sliding'
    else:
        recommended = 'sentences'
    
    return {
        'total_words': total_words,
        'total_sentences': total_sentences,
        'avg_words_per_sentence': round(avg_words, 1),
        'recommended_strategy': recommended
    }