"""
Embedding Service - Convert text to vectors
"""
import logging
import torch
from sentence_transformers import SentenceTransformer
from typing import List
import numpy as np

logger = logging.getLogger(__name__)


class EmbeddingService:
    """Service for generating text embeddings"""
    
    def __init__(self, model_name: str = 'all-MiniLM-L6-v2'):
        self.model_name = model_name
        self.device = 'cuda' if torch.cuda.is_available() else 'cpu'
        
        logger.info(f"Loading embedding model: {model_name} on {self.device}")
        
        self.model = SentenceTransformer(model_name, device=self.device)
        
        # GPU optimization
        if self.device == 'cuda':
            self.model.half()  # Use FP16 for faster inference
            logger.info("✅ GPU acceleration enabled with FP16")
        
        self.dimension = self.model.get_sentence_embedding_dimension()
        
        logger.info(f"✅ Embedding model loaded: dimension={self.dimension}")
    
    def encode(
        self,
        texts: List[str],
        batch_size: int = None,
        show_progress: bool = False
    ) -> np.ndarray:
        """
        Encode texts into embeddings
        
        Args:
            texts: List of texts to encode
            batch_size: Batch size (auto-detect based on device)
            show_progress: Show progress bar
        
        Returns:
            Numpy array of embeddings (shape: [len(texts), dimension])
        """
        if not texts:
            return np.array([])
        
        # Auto batch size
        if batch_size is None:
            batch_size = 256 if self.device == 'cuda' else 32
        
        embeddings = self.model.encode(
            texts,
            batch_size=batch_size,
            show_progress_bar=show_progress,
            convert_to_numpy=True
        )
        
        return embeddings
    
    def encode_single(self, text: str) -> np.ndarray:
        """Encode a single text"""
        return self.encode([text])[0]
    
    def get_dimension(self) -> int:
        """Get embedding dimension"""
        return self.dimension