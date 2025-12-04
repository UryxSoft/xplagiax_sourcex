"""
SQLite Repository - Metadata CRUD operations
"""
import sqlite3
import logging
from typing import List, Dict, Optional, Tuple
from datetime import datetime
from contextlib import contextmanager

logger = logging.getLogger(__name__)


class SQLiteRepository:
    """
    Repository for SQLite metadata operations
    
    Handles:
    - Paper metadata storage
    - Deduplication tracking (Bloom filter + DB)
    - Search history
    - Usage statistics
    """
    
    def __init__(self, db_path: str = "data/xplagiax.db"):
        """
        Initialize SQLite repository
        
        Args:
            db_path: Path to SQLite database
        """
        self.db_path = db_path
        self._init_database()
        self._optimize_sqlite()  # ✅ NUEVO
        
        logger.info(f"✅ SQLite repository initialized: {db_path}")
        
    def _optimize_sqlite(self):
        """
        Optimizaciones SQLite para máximo performance
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            # ✅ WAL mode (Write-Ahead Logging) - 10-50x más rápido
            cursor.execute("PRAGMA journal_mode = WAL")
            
            # ✅ Synchronous mode
            cursor.execute("PRAGMA synchronous = NORMAL")  # Balance
            
            # ✅ Cache size (10MB)
            cursor.execute("PRAGMA cache_size = 10000")
            
            # ✅ Page size
            cursor.execute("PRAGMA page_size = 4096")
            
            # ✅ Temp store en RAM
            cursor.execute("PRAGMA temp_store = MEMORY")
            
            # ✅ Memory-mapped I/O (256MB)
            cursor.execute("PRAGMA mmap_size = 268435456")
            
            # ✅ Optimize
            cursor.execute("PRAGMA optimize")
            
            conn.commit()
            
            logger.info("✅ SQLite optimized with WAL, cache, and mmap")
    
    def _init_database(self):
        """Create tables if they don't exist"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            # Papers table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS papers (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    title TEXT NOT NULL,
                    authors TEXT,
                    abstract TEXT,
                    doi TEXT,
                    url TEXT,
                    publication_date TEXT,
                    document_type TEXT,
                    source TEXT NOT NULL,
                    content_hash TEXT UNIQUE NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Index for fast lookups
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_papers_hash 
                ON papers(content_hash)
            """)
            
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_papers_source 
                ON papers(source)
            """)
            
            # Search history table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS search_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    query TEXT NOT NULL,
                    theme TEXT,
                    language TEXT,
                    threshold REAL,
                    results_count INTEGER,
                    search_time_ms REAL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Usage statistics table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS usage_stats (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    endpoint TEXT NOT NULL,
                    method TEXT NOT NULL,
                    status_code INTEGER,
                    response_time_ms REAL,
                    ip_address TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            conn.commit()
            
            logger.info("Database tables initialized")
    
    @contextmanager
    def _get_connection(self):
        """Context manager for database connections"""
        conn = sqlite3.connect(
            self.db_path,
            check_same_thread=False,
            timeout=20.0,
            isolation_level='DEFERRED'  # ✅ Lazy transactions
        )
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        try:
            yield conn
        finally:
            conn.close()
    
    # ==================== PAPER CRUD ====================
    
    def add_paper(self, paper: Dict) -> Optional[int]:
        """
        Add paper to database
        
        Args:
            paper: Paper metadata dict
        
        Returns:
            Paper ID if successful, None otherwise
        """
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                
                cursor.execute("""
                    INSERT INTO papers (
                        title, authors, abstract, doi, url,
                        publication_date, document_type, source, content_hash
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    paper.get('title'),
                    paper.get('authors'),
                    paper.get('abstract'),
                    paper.get('doi'),
                    paper.get('url'),
                    paper.get('date'),
                    paper.get('type'),
                    paper.get('source'),
                    paper.get('content_hash')
                ))
                
                conn.commit()
                
                return cursor.lastrowid
        
        except sqlite3.IntegrityError:
            # Duplicate content_hash
            logger.debug(f"Paper already exists: {paper.get('title')}")
            return None
        
        except Exception as e:
            logger.error(f"Error adding paper: {e}")
            return None
    
    def add_papers_batch(self, papers: List[Dict]) -> int:
        """Batch insert ultra-optimizado"""
        added_count = 0
        
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                
                # ✅ Preparar valores
                values = [
                    (
                        paper.get('title'),
                        paper.get('authors'),
                        paper.get('abstract'),
                        paper.get('doi'),
                        paper.get('url'),
                        paper.get('date'),
                        paper.get('type'),
                        paper.get('source'),
                        paper.get('content_hash')
                    )
                    for paper in papers
                ]
                
                # ✅ executemany (50x más rápido que loops)
                cursor.executemany("""
                    INSERT OR IGNORE INTO papers (
                        title, authors, abstract, doi, url,
                        publication_date, document_type, source, content_hash
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, values)
                
                added_count = cursor.rowcount
                conn.commit()
                
                logger.info(f"✅ Batch insert: {added_count}/{len(papers)} papers")
        
        except Exception as e:
            logger.error(f"Batch insert error: {e}")
        
        return added_count
    
    def get_paper_by_hash(self, content_hash: str) -> Optional[Dict]:
        """
        Get paper by content hash
        
        Args:
            content_hash: Content hash
        
        Returns:
            Paper dict or None
        """
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                
                cursor.execute("""
                    SELECT * FROM papers WHERE content_hash = ?
                """, (content_hash,))
                
                row = cursor.fetchone()
                
                if row:
                    return dict(row)
                
                return None
        
        except Exception as e:
            logger.error(f"Error getting paper by hash: {e}")
            return None
    
    def paper_exists(self, content_hash: str) -> bool:
        """
        Check if paper exists
        
        Args:
            content_hash: Content hash
        
        Returns:
            True if exists
        """
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                
                cursor.execute("""
                    SELECT COUNT(*) FROM papers WHERE content_hash = ?
                """, (content_hash,))
                
                count = cursor.fetchone()[0]
                return count > 0
        
        except Exception as e:
            logger.error(f"Error checking paper existence: {e}")
            return False
    
    def get_papers_by_source(self, source: str, limit: int = 100) -> List[Dict]:
        """
        Get papers from specific source
        
        Args:
            source: Source name
            limit: Maximum number of papers
        
        Returns:
            List of paper dicts
        """
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                
                cursor.execute("""
                    SELECT * FROM papers 
                    WHERE source = ?
                    ORDER BY created_at DESC
                    LIMIT ?
                """, (source, limit))
                
                return [dict(row) for row in cursor.fetchall()]
        
        except Exception as e:
            logger.error(f"Error getting papers by source: {e}")
            return []
    
    def get_total_papers(self) -> int:
        """Get total number of papers"""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                
                cursor.execute("SELECT COUNT(*) FROM papers")
                
                return cursor.fetchone()[0]
        
        except Exception as e:
            logger.error(f"Error getting total papers: {e}")
            return 0
    
    def get_papers_by_source_count(self) -> Dict[str, int]:
        """
        Get paper count by source
        
        Returns:
            Dict mapping source to count
        """
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                
                cursor.execute("""
                    SELECT source, COUNT(*) as count 
                    FROM papers 
                    GROUP BY source
                """)
                
                return {row['source']: row['count'] for row in cursor.fetchall()}
        
        except Exception as e:
            logger.error(f"Error getting source counts: {e}")
            return {}
    
    # ==================== SEARCH HISTORY ====================
    
    def log_search(
        self,
        query: str,
        theme: str,
        language: str,
        threshold: float,
        results_count: int,
        search_time_ms: float
    ) -> bool:
        """
        Log search query to history
        
        Args:
            query: Search query
            theme: Search theme
            language: Language code
            threshold: Similarity threshold
            results_count: Number of results
            search_time_ms: Search time in milliseconds
        
        Returns:
            True if successful
        """
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                
                cursor.execute("""
                    INSERT INTO search_history (
                        query, theme, language, threshold, 
                        results_count, search_time_ms
                    ) VALUES (?, ?, ?, ?, ?, ?)
                """, (query, theme, language, threshold, results_count, search_time_ms))
                
                conn.commit()
                
                return True
        
        except Exception as e:
            logger.error(f"Error logging search: {e}")
            return False
    
    def get_recent_searches(self, limit: int = 50) -> List[Dict]:
        """Get recent search history"""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                
                cursor.execute("""
                    SELECT * FROM search_history 
                    ORDER BY created_at DESC 
                    LIMIT ?
                """, (limit,))
                
                return [dict(row) for row in cursor.fetchall()]
        
        except Exception as e:
            logger.error(f"Error getting recent searches: {e}")
            return []
    
    def get_search_stats(self) -> Dict:
        """Get search statistics"""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                
                # Total searches
                cursor.execute("SELECT COUNT(*) FROM search_history")
                total = cursor.fetchone()[0]
                
                # Average search time
                cursor.execute("SELECT AVG(search_time_ms) FROM search_history")
                avg_time = cursor.fetchone()[0] or 0
                
                # Average results
                cursor.execute("SELECT AVG(results_count) FROM search_history")
                avg_results = cursor.fetchone()[0] or 0
                
                return {
                    'total_searches': total,
                    'avg_search_time_ms': round(avg_time, 2),
                    'avg_results_count': round(avg_results, 2)
                }
        
        except Exception as e:
            logger.error(f"Error getting search stats: {e}")
            return {}
    
    # ==================== USAGE STATISTICS ====================
    
    def log_request(
        self,
        endpoint: str,
        method: str,
        status_code: int,
        response_time_ms: float,
        ip_address: str = None
    ) -> bool:
        """Log API request"""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                
                cursor.execute("""
                    INSERT INTO usage_stats (
                        endpoint, method, status_code, 
                        response_time_ms, ip_address
                    ) VALUES (?, ?, ?, ?, ?)
                """, (endpoint, method, status_code, response_time_ms, ip_address))
                
                conn.commit()
                
                return True
        
        except Exception as e:
            logger.error(f"Error logging request: {e}")
            return False
    
    def get_usage_stats(self, days: int = 7) -> Dict:
        """Get usage statistics for last N days"""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                
                cursor.execute("""
                    SELECT 
                        COUNT(*) as total_requests,
                        AVG(response_time_ms) as avg_response_time,
                        COUNT(CASE WHEN status_code >= 400 THEN 1 END) as error_count
                    FROM usage_stats
                    WHERE created_at >= datetime('now', '-' || ? || ' days')
                """, (days,))
                
                row = cursor.fetchone()
                
                return {
                    'total_requests': row['total_requests'],
                    'avg_response_time_ms': round(row['avg_response_time'] or 0, 2),
                    'error_count': row['error_count'],
                    'error_rate': (row['error_count'] / row['total_requests'] * 100) 
                                  if row['total_requests'] > 0 else 0
                }
        
        except Exception as e:
            logger.error(f"Error getting usage stats: {e}")
            return {}
    
    # ==================== MAINTENANCE ====================
    
    def vacuum(self) -> bool:
        """Optimize database (reclaim space)"""
        try:
            with self._get_connection() as conn:
                conn.execute("VACUUM")
                logger.info("Database vacuumed")
                return True
        
        except Exception as e:
            logger.error(f"Error vacuuming database: {e}")
            return False
    
    def get_db_size_mb(self) -> float:
        """Get database file size in MB"""
        try:
            import os
            size_bytes = os.path.getsize(self.db_path)
            return size_bytes / (1024 * 1024)
        
        except Exception as e:
            logger.error(f"Error getting database size: {e}")
            return 0.0