"""
FAISS Repository - Vector index CRUD operations
"""
import os
import pickle
import logging
import numpy as np
from typing import List, Dict, Optional, Tuple
import faiss

from app.models.enums import FAISSStrategy

logger = logging.getLogger(__name__)


class FAISSRepository:
    """
    Repository for FAISS vector index operations
    
    Handles:
    - Index creation with different strategies
    - Vector addition with deduplication
    - Similarity search
    - Index persistence (save/load)
    - Index management (clear, rebuild, stats)
    """
    
    def __init__(
        self,
        dimension: int = 384,
        index_path: str = "data/faiss_index.index",
        metadata_path: str = "data/faiss_index_metadata.pkl",
        strategy: FAISSStrategy = FAISSStrategy.FLAT_IDMAP
    ):
        """
        Initialize FAISS repository
        
        Args:
            dimension: Embedding dimension
            index_path: Path to save/load index
            metadata_path: Path to save/load metadata
            strategy: FAISS indexing strategy
        """
        self.dimension = dimension
        self.index_path = index_path
        self.metadata_path = metadata_path
        self.current_strategy = strategy
        
        # Initialize index
        self.index: Optional[faiss.Index] = None
        self.metadata: Dict[int, Dict] = {}  # id -> paper metadata
        
        # Load existing index if available
        if os.path.exists(index_path) and os.path.exists(metadata_path):
            self.load()
        else:
            self._create_index(strategy)
        
        logger.info(
            f"✅ FAISS repository initialized: "
            f"strategy={strategy.value}, dimension={dimension}, "
            f"papers={self.index.ntotal if self.index else 0}"
        )
    
    # ==================== INDEX CREATION ====================
    
    def _create_index(self, strategy: FAISSStrategy) -> faiss.Index:
        """
        Create FAISS index based on strategy
        
        Args:
            strategy: FAISS indexing strategy
        
        Returns:
            FAISS index
        """
        if strategy == FAISSStrategy.FLAT_L2:
            index = faiss.IndexFlatL2(self.dimension)
        
        elif strategy == FAISSStrategy.FLAT_IP:
            index = faiss.IndexFlatIP(self.dimension)
        
        elif strategy == FAISSStrategy.FLAT_IDMAP:
            # Flat index with ID mapping (supports removal)
            base_index = faiss.IndexFlatL2(self.dimension)
            index = faiss.IndexIDMap(base_index)
        
        elif strategy == FAISSStrategy.IVF_FLAT:
            # Inverted file with flat quantizer
            nlist = 100  # Number of clusters
            quantizer = faiss.IndexFlatL2(self.dimension)
            index = faiss.IndexIVFFlat(quantizer, self.dimension, nlist)
            # Note: Needs training before use
        
        elif strategy == FAISSStrategy.IVF_PQ:
            # IVF with product quantization (memory efficient)
            nlist = 4096
            m = 64  # Number of sub-quantizers
            quantizer = faiss.IndexFlatL2(self.dimension)
            index = faiss.IndexIVFPQ(quantizer, self.dimension, nlist, m, 8)
            # Note: Needs training before use
        
        elif strategy == FAISSStrategy.HNSW:
            # Hierarchical NSW graph
            M = 32  # Number of connections per layer
            index = faiss.IndexHNSWFlat(self.dimension, M)
        
        else:
            # Default to Flat IDMap
            base_index = faiss.IndexFlatL2(self.dimension)
            index = faiss.IndexIDMap(base_index)
        
        self.index = index
        self.current_strategy = strategy
        
        logger.info(f"Created FAISS index: {strategy.value}")
        
        return index
    
    # ==================== CRUD OPERATIONS ====================
    
    def add(
        self,
        embeddings: np.ndarray,
        papers: List[Dict],
        ids: Optional[np.ndarray] = None
    ) -> int:
        """
        Add vectors to index with metadata
        
        Args:
            embeddings: Numpy array of embeddings (shape: [N, dimension])
            papers: List of paper metadata dicts
            ids: Optional custom IDs (if None, auto-generate)
        
        Returns:
            Number of vectors added
        """
        if embeddings.shape[0] != len(papers):
            raise ValueError(
                f"Mismatch: {embeddings.shape[0]} embeddings but {len(papers)} papers"
            )
        
        if embeddings.shape[1] != self.dimension:
            raise ValueError(
                f"Embedding dimension {embeddings.shape[1]} != index dimension {self.dimension}"
            )
        
        # Ensure float32 (FAISS requirement)
        if embeddings.dtype != np.float32:
            embeddings = embeddings.astype(np.float32)
        
        # Normalize vectors for cosine similarity
        faiss.normalize_L2(embeddings)
        
        # Generate IDs if not provided
        if ids is None:
            start_id = self.index.ntotal
            ids = np.arange(start_id, start_id + len(papers), dtype=np.int64)
        else:
            ids = ids.astype(np.int64)
        
        # Add to index
        if isinstance(self.index, faiss.IndexIDMap):
            self.index.add_with_ids(embeddings, ids)
        else:
            self.index.add(embeddings)
        
        # Store metadata
        for idx, paper in zip(ids, papers):
            self.metadata[int(idx)] = paper
        
        logger.info(f"Added {len(papers)} papers to FAISS index")
        
        return len(papers)
    
    def search(
        self,
        query_embedding: np.ndarray,
        k: int = 10,
        threshold: float = 0.7
    ) -> List[Dict]:
        """
        Search for similar vectors
        
        Args:
            query_embedding: Query vector (shape: [dimension])
            k: Number of results to return
            threshold: Similarity threshold (0.0-1.0)
        
        Returns:
            List of paper dicts with similarity scores
        """
        if self.index.ntotal == 0:
            logger.warning("FAISS index is empty")
            return []
        
        # Ensure correct shape and type
        if query_embedding.ndim == 1:
            query_embedding = query_embedding.reshape(1, -1)
        
        if query_embedding.dtype != np.float32:
            query_embedding = query_embedding.astype(np.float32)
        
        # Normalize for cosine similarity
        faiss.normalize_L2(query_embedding)
        
        # Search
        distances, indices = self.index.search(query_embedding, k)
        
        # Convert L2 distances to cosine similarities
        # similarity = 1 - (L2_distance^2 / 2)
        similarities = 1 - (distances[0] ** 2 / 2)
        
        # Filter by threshold and collect results
        results = []
        
        for idx, similarity in zip(indices[0], similarities):
            if idx == -1:  # FAISS returns -1 for empty slots
                continue
            
            if similarity >= threshold:
                paper = self.metadata.get(int(idx), {}).copy()
                paper['similarity'] = float(similarity)
                results.append(paper)
        
        logger.debug(f"FAISS search returned {len(results)} results above threshold {threshold}")
        
        return results
    
    def search_batch(
        self,
        query_embeddings: np.ndarray,
        k: int = 10,
        threshold: float = 0.7
    ) -> List[List[Dict]]:
        """
        Batch search for multiple queries
        
        Args:
            query_embeddings: Batch of query vectors (shape: [N, dimension])
            k: Number of results per query
            threshold: Similarity threshold
        
        Returns:
            List of result lists (one per query)
        """
        if self.index.ntotal == 0:
            return [[] for _ in range(len(query_embeddings))]
        
        # Ensure correct type
        if query_embeddings.dtype != np.float32:
            query_embeddings = query_embeddings.astype(np.float32)
        
        # Normalize
        faiss.normalize_L2(query_embeddings)
        
        # Search
        distances, indices = self.index.search(query_embeddings, k)
        
        # Convert to similarities
        similarities = 1 - (distances ** 2 / 2)
        
        # Collect results for each query
        all_results = []
        
        for query_idx in range(len(query_embeddings)):
            query_results = []
            
            for idx, similarity in zip(indices[query_idx], similarities[query_idx]):
                if idx == -1:
                    continue
                
                if similarity >= threshold:
                    paper = self.metadata.get(int(idx), {}).copy()
                    paper['similarity'] = float(similarity)
                    query_results.append(paper)
            
            all_results.append(query_results)
        
        logger.debug(f"Batch search: {len(query_embeddings)} queries processed")
        
        return all_results
    
    def remove(self, ids: List[int]) -> int:
        """
        Remove vectors by ID (only works with IndexIDMap)
        
        Args:
            ids: List of IDs to remove
        
        Returns:
            Number of vectors removed
        """
        if not isinstance(self.index, faiss.IndexIDMap):
            logger.warning(
                f"Remove operation not supported for {self.current_strategy.value}"
            )
            return 0
        
        # Convert to numpy array
        ids_array = np.array(ids, dtype=np.int64)
        
        # Remove from index
        try:
            self.index.remove_ids(ids_array)
        except Exception as e:
            logger.error(f"Error removing IDs: {e}")
            return 0
        
        # Remove from metadata
        removed_count = 0
        for idx in ids:
            if idx in self.metadata:
                del self.metadata[idx]
                removed_count += 1
        
        logger.info(f"Removed {removed_count} papers from FAISS index")
        
        return removed_count
    
    def clear(self):
        """Clear entire index (DESTRUCTIVE)"""
        self._create_index(self.current_strategy)
        self.metadata = {}
        
        logger.warning("FAISS index cleared")
    
    # ==================== PERSISTENCE ====================
    
    def save(self) -> bool:
        """
        Save index and metadata to disk
        
        Returns:
            True if successful, False otherwise
        """
        try:
            # Create data directory if needed
            os.makedirs(os.path.dirname(self.index_path), exist_ok=True)
            
            # Save FAISS index
            faiss.write_index(self.index, self.index_path)
            
            # Save metadata
            with open(self.metadata_path, 'wb') as f:
                pickle.dump({
                    'metadata': self.metadata,
                    'strategy': self.current_strategy.value,
                    'dimension': self.dimension
                }, f)
            
            logger.info(
                f"FAISS index saved: {self.index.ntotal} papers, "
                f"{len(self.metadata)} metadata entries"
            )
            
            return True
        
        except Exception as e:
            logger.error(f"Error saving FAISS index: {e}", exc_info=True)
            return False
    
    def load(self) -> bool:
        """
        Load index and metadata from disk
        
        Returns:
            True if successful, False otherwise
        """
        try:
            # Load FAISS index
            if not os.path.exists(self.index_path):
                logger.warning(f"Index file not found: {self.index_path}")
                return False
            
            self.index = faiss.read_index(self.index_path)
            
            # Load metadata
            if not os.path.exists(self.metadata_path):
                logger.warning(f"Metadata file not found: {self.metadata_path}")
                self.metadata = {}
            else:
                with open(self.metadata_path, 'rb') as f:
                    data = pickle.load(f)
                    self.metadata = data.get('metadata', {})
                    self.current_strategy = FAISSStrategy(
                        data.get('strategy', FAISSStrategy.FLAT_IDMAP.value)
                    )
                    self.dimension = data.get('dimension', self.dimension)
            
            logger.info(
                f"✅ FAISS index loaded: {self.index.ntotal} papers, "
                f"{len(self.metadata)} metadata entries"
            )
            
            return True
        
        except Exception as e:
            logger.error(f"Error loading FAISS index: {e}", exc_info=True)
            return False
    
    # ==================== UTILITIES ====================
    
    def get_stats(self) -> Dict:
        """
        Get index statistics
        
        Returns:
            Dict with index statistics
        """
        return {
            'total_papers': self.index.ntotal if self.index else 0,
            'dimension': self.dimension,
            'metadata_count': len(self.metadata),
            'strategy': self.current_strategy.value,
            'supports_removal': self.current_strategy.supports_removal(),
            'is_approximate': self.current_strategy.is_approximate(),
            'corrupted': self.index.ntotal != len(self.metadata) if self.index else False
        }
    
    def rebuild_from_metadata(self, embedding_service) -> bool:
        """
        Rebuild index from metadata (useful after corruption)
        
        Args:
            embedding_service: Service to generate embeddings
        
        Returns:
            True if successful
        """
        if not self.metadata:
            logger.warning("No metadata available for rebuild")
            return False
        
        logger.info(f"Rebuilding FAISS index from {len(self.metadata)} papers")
        
        # Extract texts
        papers = list(self.metadata.values())
        texts = [
            p.get('abstract', p.get('title', ''))
            for p in papers
        ]
        
        # Generate embeddings
        embeddings = embedding_service.encode(texts)
        
        # Create new index
        self._create_index(self.current_strategy)
        
        # Add papers
        self.add(embeddings, papers)
        
        # Save
        self.save()
        
        logger.info("✅ FAISS index rebuilt successfully")
        
        return True
    
    def get_paper_by_id(self, paper_id: int) -> Optional[Dict]:
        """Get paper metadata by ID"""
        return self.metadata.get(paper_id)
    
    def get_all_papers(self) -> List[Dict]:
        """Get all paper metadata"""
        return list(self.metadata.values())
    
    def compact(self) -> int:
        """
        Remove orphaned metadata (metadata without index entry)
        
        Returns:
            Number of orphaned entries removed
        """
        valid_ids = set(range(self.index.ntotal))
        orphaned = [
            idx for idx in self.metadata.keys()
            if idx not in valid_ids
        ]
        
        for idx in orphaned:
            del self.metadata[idx]
        
        if orphaned:
            logger.info(f"Compacted: removed {len(orphaned)} orphaned metadata entries")
        
        return len(orphaned)