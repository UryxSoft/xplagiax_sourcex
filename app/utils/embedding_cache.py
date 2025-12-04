"""
Persistent embedding cache
"""
import pickle
from functools import lru_cache
from app.utils.serialization import dumps_msgpack, loads_msgpack


class PersistentEmbeddingCache:
    """
    Cache de embeddings en disco + memoria
    """
    
    def __init__(self, cache_path: str = "data/embedding_cache.msgpack"):
        self.cache_path = cache_path
        self.cache = self._load_cache()
        self.hits = 0
        self.misses = 0
    
    def _load_cache(self) -> dict:
        """Load from disk"""
        try:
            with open(self.cache_path, 'rb') as f:
                return loads_msgpack(f.read())
        except FileNotFoundError:
            return {}
    
    def save(self):
        """Save to disk"""
        try:
            with open(self.cache_path, 'wb') as f:
                f.write(dumps_msgpack(self.cache))
        except Exception as e:
            logger.error(f"Save embedding cache error: {e}")
    
    @lru_cache(maxsize=10000)
    def get(self, text: str):
        """Get con LRU memory cache"""
        if text in self.cache:
            self.hits += 1
            return self.cache[text]
        
        self.misses += 1
        return None
    
    def put(self, text: str, embedding):
        """Put embedding"""
        self.cache[text] = embedding.tolist()
        
        # Auto-save cada 100 inserts
        if len(self.cache) % 100 == 0:
            self.save()
    
    def precompute_common_queries(self, embedding_service):
        """Precomputar queries comunes"""
        common_queries = [
            "machine learning",
            "deep learning",
            "neural networks",
            "artificial intelligence",
            "computer vision",
            "natural language processing",
            # ... agregar más ...
        ]
        
        for query in common_queries:
            if query not in self.cache:
                emb = embedding_service.encode_single(query, use_cache=False)
                self.put(query, emb)
        
        self.save()