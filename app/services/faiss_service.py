"""
FAISS Service - Vector index management
"""
import logging
import numpy as np
from typing import List, Dict, Optional
import asyncio

from app.repositories.faiss_repository import FAISSRepository
from app.services.deduplication_service import get_deduplicator
from app.models.enums import FAISSStrategy

logger = logging.getLogger(__name__)


class FAISSService:
    """
    Service for FAISS vector index management
    
    Provides high-level operations for:
    - Adding papers with deduplication
    - Similarity search
    - Index maintenance
    - Statistics and health checks
    """
    
    def __init__(
        self,
        dimension: int = 384,
        strategy: FAISSStrategy = FAISSStrategy.FLAT_IDMAP
    ):
        """
        Initialize FAISS service
        
        Args:
            dimension: Embedding dimension
            strategy: FAISS indexing strategy
        """
        self.repository = FAISSRepository(
            dimension=dimension,
            strategy=strategy
        )
        
        logger.info(f"✅ FAISSService initialized: strategy={strategy.value}")
    
    # ==================== ADD OPERATIONS ====================
    
    async def add_papers(
        self,
        embeddings: np.ndarray,
        papers: List[Dict],
        deduplicate: bool = True
    ) -> int:
        """
        Add papers to FAISS index with optional deduplication
        
        Args:
            embeddings: Numpy array of embeddings
            papers: List of paper metadata
            deduplicate: Whether to check for duplicates
        
        Returns:
            Number of papers added
        """
        if len(embeddings) != len(papers):
            raise ValueError(
                f"Embeddings count {len(embeddings)} != papers count {len(papers)}"
            )
        
        if deduplicate:
            # Get deduplicator
            deduplicator = await get_deduplicator()
            
            # Deduplicate papers
            unique_papers = await deduplicator.deduplicate_papers(papers)
            
            if len(unique_papers) < len(papers):
                logger.info(
                    f"Deduplication: {len(papers)} → {len(unique_papers)} papers"
                )
                
                # Filter embeddings to match unique papers
                unique_indices = [
                    i for i, paper in enumerate(papers)
                    if any(
                        p.get('content_hash') == paper.get('content_hash')
                        for p in unique_papers
                    )
                ]
                
                embeddings = embeddings[unique_indices]
                papers = unique_papers
        
        # Add to repository
        added_count = self.repository.add(embeddings, papers)
        
        logger.info(f"Added {added_count} papers to FAISS index")
        
        return added_count
    
    async def add_single_paper(
        self,
        embedding: np.ndarray,
        paper: Dict
    ) -> bool:
        """
        Add a single paper to index
        
        Args:
            embedding: Single embedding vector
            paper: Paper metadata
        
        Returns:
            True if added successfully
        """
        if embedding.ndim == 1:
            embedding = embedding.reshape(1, -1)
        
        try:
            await self.add_papers(
                embeddings=embedding,
                papers=[paper],
                deduplicate=True
            )
            return True
        
        except Exception as e:
            logger.error(f"Error adding single paper: {e}")
            return False
    
    # ==================== SEARCH OPERATIONS ====================
    
    def search_similar(
        self,
        query_embedding: np.ndarray,
        k: int = 10,
        threshold: float = 0.7
    ) -> List[Dict]:
        """
        Search for similar papers
        
        Args:
            query_embedding: Query vector
            k: Number of results
            threshold: Similarity threshold
        
        Returns:
            List of paper dicts with similarity scores
        """
        return self.repository.search(
            query_embedding=query_embedding,
            k=k,
            threshold=threshold
        )
    
    def search_similar_batch(
        self,
        query_embeddings: np.ndarray,
        k: int = 10,
        threshold: float = 0.7
    ) -> List[List[Dict]]:
        """
        Batch search for multiple queries
        
        Args:
            query_embeddings: Batch of query vectors
            k: Number of results per query
            threshold: Similarity threshold
        
        Returns:
            List of result lists
        """
        return self.repository.search_batch(
            query_embeddings=query_embeddings,
            k=k,
            threshold=threshold
        )
    
    # ==================== MANAGEMENT OPERATIONS ====================
    
    def save(self) -> bool:
        """Save index to disk"""
        return self.repository.save()
    
    def load(self) -> bool:
        """Load index from disk"""
        return self.repository.load()
    
    def clear(self):
        """Clear entire index (DESTRUCTIVE)"""
        self.repository.clear()
        logger.warning("FAISS index cleared")
    
    def remove_papers(self, paper_ids: List[int]) -> int:
        """
        Remove papers by ID
        
        Args:
            paper_ids: List of paper IDs
        
        Returns:
            Number of papers removed
        """
        if not self.repository.current_strategy.supports_removal():
            logger.warning(
                f"Strategy {self.repository.current_strategy.value} "
                "does not support removal"
            )
            return 0
        
        return self.repository.remove(paper_ids)
    
    async def remove_duplicates(self) -> int:
        """
        Find and remove duplicate papers
        
        Returns:
            Number of duplicates removed
        """
        logger.info("Searching for duplicates in FAISS index...")
        
        if self.repository.index.ntotal == 0:
            logger.info("Index is empty, no duplicates to remove")
            return 0
        
        # Get all papers
        all_papers = self.repository.get_all_papers()
        
        if not all_papers:
            return 0
        
        # Get deduplicator
        deduplicator = await get_deduplicator()
        
        # Find duplicates by content hash
        seen_hashes = set()
        duplicate_ids = []
        
        for paper_id, paper in self.repository.metadata.items():
            content_hash = paper.get('content_hash')
            
            if not content_hash:
                continue
            
            if content_hash in seen_hashes:
                duplicate_ids.append(paper_id)
            else:
                seen_hashes.add(content_hash)
        
        if not duplicate_ids:
            logger.info("No duplicates found")
            return 0
        
        # Remove duplicates
        removed_count = self.remove_papers(duplicate_ids)
        
        logger.info(f"Removed {removed_count} duplicate papers")
        
        # Save index
        self.save()
        
        return removed_count
    
    def compact(self) -> int:
        """
        Remove orphaned metadata
        
        Returns:
            Number of orphaned entries removed
        """
        return self.repository.compact()
    
    async def rebuild(self, embedding_service) -> bool:
        """
        Rebuild index from metadata
        
        Args:
            embedding_service: Service to generate embeddings
        
        Returns:
            True if successful
        """
        return self.repository.rebuild_from_metadata(embedding_service)
    
    # ==================== STATISTICS ====================
    
    def get_stats(self) -> Dict:
        """Get index statistics"""
        return self.repository.get_stats()
    
    def get_paper_by_id(self, paper_id: int) -> Optional[Dict]:
        """Get paper metadata by ID"""
        return self.repository.get_paper_by_id(paper_id)
    
    def get_all_papers(self) -> List[Dict]:
        """Get all paper metadata"""
        return self.repository.get_all_papers()
    
    def get_total_papers(self) -> int:
        """Get total number of papers in index"""
        return self.repository.index.ntotal if self.repository.index else 0
    
    def is_healthy(self) -> bool:
        """
        Check if index is healthy (no corruption)
        
        Returns:
            True if healthy
        """
        stats = self.get_stats()
        return not stats.get('corrupted', False)
    
    # ==================== OPTIMIZATION ====================
    
    async def optimize(self) -> bool:
        """
        Optimize index (remove duplicates, compact, save)
        
        Returns:
            True if successful
        """
        logger.info("Starting FAISS optimization...")
        
        try:
            # 1. Remove duplicates
            duplicates_removed = await self.remove_duplicates()
            
            # 2. Compact metadata
            orphans_removed = self.compact()
            
            # 3. Save
            self.save()
            
            logger.info(
                f"✅ Optimization complete: "
                f"duplicates={duplicates_removed}, orphans={orphans_removed}"
            )
            
            return True
        
        except Exception as e:
            logger.error(f"Error during optimization: {e}", exc_info=True)
            return False