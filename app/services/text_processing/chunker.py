"""
Text Chunker - Split text into meaningful chunks
"""
import re
from typing import List


class TextChunker:
    """Split text into chunks for plagiarism detection"""
    
    def __init__(self):
        self.sentence_pattern = re.compile(r'[.!?]+\s+')
    
    def chunk_by_sentences(
        self,
        text: str,
        min_words: int = 15
    ) -> List[str]:
        """
        Chunk text by sentences
        
        Args:
            text: Input text
            min_words: Minimum words per chunk
        
        Returns:
            List of text chunks
        """
        # Split into sentences
        sentences = self.sentence_pattern.split(text)
        sentences = [s.strip() for s in sentences if s.strip()]
        
        chunks = []
        current_chunk = []
        current_word_count = 0
        
        for sentence in sentences:
            words = sentence.split()
            current_chunk.append(sentence)
            current_word_count += len(words)
            
            # If we've reached min_words, save the chunk
            if current_word_count >= min_words:
                chunks.append(' '.join(current_chunk))
                current_chunk = []
                current_word_count = 0
        
        # Add remaining chunk if any
        if current_chunk:
            chunks.append(' '.join(current_chunk))
        
        return chunks
    
    def chunk_sliding_window(
        self,
        text: str,
        window_size: int = 20,
        overlap: int = 5
    ) -> List[str]:
        """
        Chunk text using sliding window
        
        Args:
            text: Input text
            window_size: Words per window
            overlap: Overlapping words between windows
        
        Returns:
            List of text chunks
        """
        words = text.split()
        
        if len(words) <= window_size:
            return [text]
        
        chunks = []
        step = window_size - overlap
        
        for i in range(0, len(words) - window_size + 1, step):
            chunk = ' '.join(words[i:i + window_size])
            chunks.append(chunk)
        
        return chunks
    
    def chunk_by_paragraphs(self, text: str) -> List[str]:
        """
        Chunk text by paragraphs
        
        Args:
            text: Input text
        
        Returns:
            List of paragraphs
        """
        paragraphs = text.split('\n\n')
        return [p.strip() for p in paragraphs if p.strip()]