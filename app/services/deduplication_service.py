"""
Deduplication Service - Bloom filter for duplicate detection
"""
import logging
import hashlib
import asyncio
from typing import List, Dict, Optional, Set
from pybloom_live import BloomFilter

from app.repositories.sqlite_repository import SQLiteRepository

logger = logging.getLogger(__name__)


class DeduplicationService:
    """
    Service for detecting and removing duplicate papers
    
    Uses:
    - Bloom filter for fast probabilistic checking (in-memory)
    - SQLite for persistent storage and verification
    
    Strategy:
    1. Check Bloom filter first (O(1), may have false positives)
    2. If Bloom says "maybe exists", verify in SQLite
    3. Add new papers to both Bloom and SQLite
    """
    
    def __init__(
        self,
        capacity: int = 1_000_000,
        error_rate: float = 0.001,
        db_path: str = "data/xplagiax.db"
    ):
        """
        Initialize deduplication service
        
        Args:
            capacity: Expected number of papers
            error_rate: Bloom filter false positive rate
            db_path: Path to SQLite database
        """
        self.capacity = capacity
        self.error_rate = error_rate
        
        # Initialize Bloom filter
        self.bloom = BloomFilter(capacity=capacity, error_rate=error_rate)
        
        # Initialize SQLite repository
        self.repository = SQLiteRepository(db_path=db_path)
        
        # Load existing hashes into Bloom filter
        self._load_existing_hashes()
        
        logger.info(
            f"✅ DeduplicationService initialized: "
            f"capacity={capacity:,}, error_rate={error_rate}"
        )
    
    def _load_existing_hashes(self):
        """Load existing content hashes from database into Bloom filter"""
        try:
            total = self.repository.get_total_papers()
            
            if total == 0:
                logger.info("No existing papers to load into Bloom filter")
                return
            
            logger.info(f"Loading {total:,} papers into Bloom filter...")
            
            # Load in batches to avoid memory issues
            batch_size = 10000
            loaded = 0
            
            with self.repository._get_connection() as conn:
                cursor = conn.cursor()
                
                cursor.execute("SELECT content_hash FROM papers")
                
                while True:
                    rows = cursor.fetchmany(batch_size)
                    
                    if not rows:
                        break
                    
                    for row in rows:
                        content_hash = row['content_hash']
                        if content_hash:
                            self.bloom.add(content_hash)
                            loaded += 1
                    
                    if loaded % 10000 == 0:
                        logger.debug(f"Loaded {loaded:,} hashes...")
            
            logger.info(f"✅ Loaded {loaded:,} hashes into Bloom filter")
        
        except Exception as e:
            logger.error(f"Error loading hashes into Bloom: {e}", exc_info=True)
    
    # ==================== HASH GENERATION ====================
    
    @staticmethod
    def generate_content_hash(paper: Dict) -> str:
        """
        Generate unique hash for paper content
        
        Uses: title + authors + doi (if available)
        
        Args:
            paper: Paper metadata dict
        
        Returns:
            SHA256 hex hash
        """
        # Combine identifying fields
        title = paper.get('title', '').lower().strip()
        authors = paper.get('authors', '').lower().strip()
        doi = paper.get('doi', '').lower().strip()
        
        # Create unique string
        unique_str = f"{title}|{authors}|{doi}"
        
        # Generate hash
        return hashlib.sha256(unique_str.encode('utf-8')).hexdigest()
    
    # ==================== DUPLICATE CHECKING ====================
    
    def is_duplicate(self, content_hash: str) -> bool:
        """
        Check if paper is a duplicate (probabilistic)
        
        Args:
            content_hash: Content hash
        
        Returns:
            True if likely duplicate (may have false positives)
        """
        return content_hash in self.bloom
    
    async def is_duplicate_verified(self, content_hash: str) -> bool:
        """
        Check if paper is duplicate (verified in database)
        
        Args:
            content_hash: Content hash
        
        Returns:
            True if definitely duplicate
        """
        # First check Bloom (fast)
        if not self.is_duplicate(content_hash):
            return False
        
        # Verify in database
        return self.repository.paper_exists(content_hash)
    
    # ==================== DEDUPLICATION ====================
    
    async def deduplicate_papers(self, papers: List[Dict]) -> List[Dict]:
        """
        Remove duplicate papers from list
        
        Args:
            papers: List of paper dicts
        
        Returns:
            List of unique papers (duplicates removed)
        """
        if not papers:
            return []
        
        unique_papers = []
        seen_hashes = set()
        
        for paper in papers:
            # Generate hash if not present
            if 'content_hash' not in paper:
                paper['content_hash'] = self.generate_content_hash(paper)
            
            content_hash = paper['content_hash']
            
            # Check if already seen in this batch
            if content_hash in seen_hashes:
                continue
            
            # Check if exists in Bloom filter
            if self.is_duplicate(content_hash):
                # Verify in database (Bloom may have false positives)
                if await self.is_duplicate_verified(content_hash):
                    logger.debug(f"Duplicate found: {paper.get('title', 'Unknown')}")
                    continue
            
            # Add to unique papers
            unique_papers.append(paper)
            seen_hashes.add(content_hash)
        
        logger.debug(
            f"Deduplication: {len(papers)} → {len(unique_papers)} papers"
        )
        
        return unique_papers
    
    # ==================== ADD OPERATIONS ====================
    
    async def add_paper(self, paper: Dict) -> bool:
        """
        Add paper to deduplication system
        
        Args:
            paper: Paper metadata dict
        
        Returns:
            True if added (not duplicate), False if duplicate
        """
        # Generate hash
        if 'content_hash' not in paper:
            paper['content_hash'] = self.generate_content_hash(paper)
        
        content_hash = paper['content_hash']
        
        # Check if duplicate
        if await self.is_duplicate_verified(content_hash):
            logger.debug(f"Paper already exists: {paper.get('title')}")
            return False
        
        # Add to database
        paper_id = self.repository.add_paper(paper)
        
        if paper_id is None:
            return False
        
        # Add to Bloom filter
        self.bloom.add(content_hash)
        
        logger.debug(f"Paper added: {paper.get('title')}")
        
        return True
    
    async def add_papers_batch(self, papers: List[Dict]) -> int:
        """
        Add multiple papers in batch
        
        Args:
            papers: List of paper dicts
        
        Returns:
            Number of papers added
        """
        # Generate hashes
        for paper in papers:
            if 'content_hash' not in paper:
                paper['content_hash'] = self.generate_content_hash(paper)
        
        # Deduplicate
        unique_papers = await self.deduplicate_papers(papers)
        
        if not unique_papers:
            return 0
        
        # Add to database
        added_count = self.repository.add_papers_batch(unique_papers)
        
        # Add to Bloom filter
        for paper in unique_papers:
            self.bloom.add(paper['content_hash'])
        
        logger.info(f"Batch add: {added_count}/{len(papers)} papers added")
        
        return added_count
    
    # ==================== STATISTICS ====================
    
    async def get_stats(self) -> Dict:
        """
        Get deduplication statistics
        
        Returns:
            Dict with stats
        """
        total_papers = self.repository.get_total_papers()
        source_counts = self.repository.get_papers_by_source_count()
        
        # Estimate Bloom filter size
        bloom_size_bytes = len(self.bloom.bitarray.tobytes())
        bloom_size_mb = bloom_size_bytes / (1024 * 1024)
        
        return {
            'total_papers': total_papers,
            'unique_sources': len(source_counts),
            'papers_by_source': source_counts,
            'bloom_filter': {
                'capacity': self.capacity,
                'error_rate': self.error_rate,
                'size_mb': round(bloom_size_mb, 2),
                'num_bits': len(self.bloom.bitarray),
                'num_hashes': self.bloom.num_hashes
            },
            'database': {
                'size_mb': round(self.repository.get_db_size_mb(), 2)
            }
        }
    
    # ==================== MAINTENANCE ====================
    
    def rebuild_bloom_filter(self):
        """Rebuild Bloom filter from database (useful after corruption)"""
        logger.info("Rebuilding Bloom filter from database...")
        
        # Create new Bloom filter
        self.bloom = BloomFilter(
            capacity=self.capacity,
            error_rate=self.error_rate
        )
        
        # Load hashes
        self._load_existing_hashes()
        
        logger.info("✅ Bloom filter rebuilt")
    
    def vacuum_database(self) -> bool:
        """Optimize database (reclaim space)"""
        return self.repository.vacuum()


# ==================== SINGLETON ====================

_deduplicator: Optional[DeduplicationService] = None
_deduplicator_lock = asyncio.Lock()


async def get_deduplicator() -> DeduplicationService:
    """
    Get global deduplicator instance (singleton)
    
    Returns:
        DeduplicationService instance
    """
    global _deduplicator
    
    if _deduplicator is None:
        async with _deduplicator_lock:
            # Double-check after acquiring lock
            if _deduplicator is None:
                _deduplicator = DeduplicationService()
    
    return _deduplicator


def reset_deduplicator():
    """Reset deduplicator (for testing)"""
    global _deduplicator
    _deduplicator = None