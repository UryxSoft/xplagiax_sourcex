"""
Embedding Service - Ultra-optimizado con GPU/CPU y caching
"""
import logging
import torch
import numpy as np
from sentence_transformers import SentenceTransformer
from typing import List
from functools import lru_cache
import concurrent.futures

logger = logging.getLogger(__name__)


class EmbeddingService:
    """
    Service ultra-optimizado para generación de embeddings
    
    Features:
    - GPU acceleration con FP16
    - CPU parallelization
    - LRU cache para embeddings frecuentes
    - Batching inteligente
    """
    
    def __init__(self, model_name: str = 'all-MiniLM-L6-v2'):
        self.model_name = model_name
        self.device = 'cuda' if torch.cuda.is_available() else 'cpu'
        
        logger.info(f"Loading embedding model: {model_name} on {self.device}")
        
        # Cargar modelo
        self.model = SentenceTransformer(model_name, device=self.device)
        
        # ✅ Optimizaciones GPU
        if self.device == 'cuda':
            self.model.half()  # FP16 (2x más rápido)
            torch.backends.cudnn.benchmark = True  # Auto-tune kernels
            torch.set_float32_matmul_precision('medium')  # TensorFloat-32
            logger.info("✅ GPU optimizations enabled: FP16, cudnn benchmark, TF32")
        
        # ✅ Thread pool para CPU
        self.executor = concurrent.futures.ThreadPoolExecutor(
            max_workers=4,
            thread_name_prefix='embedding'
        )
        
        self.dimension = self.model.get_sentence_embedding_dimension()
        
        # Cache stats
        self._cache_hits = 0
        self._cache_misses = 0
        
        logger.info(f"✅ Embedding model loaded: dimension={self.dimension}")
    
    def encode(
        self,
        texts: List[str],
        batch_size: int = None,
        show_progress: bool = False
    ) -> np.ndarray:
        """
        Encode texts into embeddings (optimizado)
        
        Args:
            texts: List of texts
            batch_size: Batch size (auto if None)
            show_progress: Show progress bar
        
        Returns:
            Numpy array of embeddings (shape: [len(texts), dimension])
        """
        if not texts:
            return np.array([])
        
        # ✅ Batch size adaptativo
        if batch_size is None:
            batch_size = 256 if self.device == 'cuda' else 32
        
        # ✅ GPU: usar batching nativo con mixed precision
        if self.device == 'cuda':
            with torch.cuda.amp.autocast():  # Mixed precision
                embeddings = self.model.encode(
                    texts,
                    batch_size=batch_size,
                    show_progress_bar=show_progress,
                    convert_to_numpy=True,
                    normalize_embeddings=True,  # Normalizar en GPU
                    device=self.device
                )
            return embeddings
        
        # ✅ CPU: paralelizar batches
        else:
            def process_batch(batch):
                return self.model.encode(
                    batch,
                    batch_size=batch_size,
                    show_progress_bar=False,
                    convert_to_numpy=True,
                    normalize_embeddings=True,
                    device=self.device
                )
            
            # Dividir en batches
            batches = [
                texts[i:i + batch_size]
                for i in range(0, len(texts), batch_size)
            ]
            
            # Procesar en paralelo
            if len(batches) > 1:
                futures = [
                    self.executor.submit(process_batch, batch)
                    for batch in batches
                ]
                results = [
                    f.result()
                    for f in concurrent.futures.as_completed(futures)
                ]
                return np.vstack(results)
            else:
                return process_batch(batches[0])
    
    @lru_cache(maxsize=10000)
    def encode_single_cached(self, text: str) -> np.ndarray:
        """
        Encode single text con LRU cache (para textos repetidos)
        
        Args:
            text: Text to encode
        
        Returns:
            Embedding vector
        """
        self._cache_hits += 1
        return self.encode([text])[0]
    
    def encode_single(self, text: str, use_cache: bool = True) -> np.ndarray:
        """
        Encode single text
        
        Args:
            text: Text to encode
            use_cache: Use LRU cache
        
        Returns:
            Embedding vector
        """
        if use_cache:
            return self.encode_single_cached(text)
        
        self._cache_misses += 1
        return self.encode([text])[0]
    
    def get_dimension(self) -> int:
        """Get embedding dimension"""
        return self.dimension
    
    def get_cache_stats(self) -> dict:
        """Get cache statistics"""
        total = self._cache_hits + self._cache_misses
        hit_rate = (self._cache_hits / total * 100) if total > 0 else 0
        
        return {
            'cache_hits': self._cache_hits,
            'cache_misses': self._cache_misses,
            'hit_rate': round(hit_rate, 2),
            'cache_size': self.encode_single_cached.cache_info().currsize,
            'cache_maxsize': 10000
        }
    
    def clear_cache(self):
        """Clear LRU cache"""
        self.encode_single_cached.cache_clear()
        self._cache_hits = 0
        self._cache_misses = 0
        logger.info("Embedding cache cleared")
    
    def __del__(self):
        """Cleanup"""
        if hasattr(self, 'executor'):
            self.executor.shutdown(wait=False)