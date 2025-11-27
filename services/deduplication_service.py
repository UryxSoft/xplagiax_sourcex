"""
Sistema de deduplicación con Bloom Filter + SQLite
"""
import hashlib
import asyncio
import logging
from typing import List, Dict, Optional
from bitarray import bitarray
import aiosqlite
import mmh3

logger = logging.getLogger(__name__)


class PaperDeduplicator:
    """
    Deduplicación de 2 capas:
    1. Bloom Filter (in-memory, 99.9% recall) - O(1)
    2. SQLite (disco, 100% precision) - O(log n)
    """
    
    def __init__(self, db_path="data/papers.db", size=100_000_000, hash_count=7):
        self.db_path = db_path
        
        # Bloom filter para 50M papers con 0.1% false positive rate
        self.bloom = bitarray(size)
        self.bloom.setall(0)
        self.hash_count = hash_count
        self.db_conn = None
    
    async def init_db(self):
        """Inicializa base de datos SQLite"""
        self.db_conn = await aiosqlite.connect(
            self.db_path,
            timeout=30.0,
            check_same_thread=False
        )
        
        # Habilitar WAL mode para concurrencia
        await self.db_conn.execute("PRAGMA journal_mode=WAL")
        await self.db_conn.execute("PRAGMA synchronous=NORMAL")
        await self.db_conn.execute("PRAGMA cache_size=10000")
        
        # Schema optimizado
        await self.db_conn.execute("""
            CREATE TABLE IF NOT EXISTS papers (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                doi TEXT,
                title_hash TEXT UNIQUE NOT NULL,
                title TEXT NOT NULL,
                author TEXT,
                abstract TEXT,
                source TEXT,
                type TEXT,
                year INTEGER,
                faiss_id INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        await self.db_conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_doi ON papers(doi) WHERE doi IS NOT NULL
        """)
        
        await self.db_conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_title_hash ON papers(title_hash)
        """)
        
        await self.db_conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_faiss_id ON papers(faiss_id)
        """)
        
        # Full-text search index
        await self.db_conn.execute("""
            CREATE VIRTUAL TABLE IF NOT EXISTS papers_fts USING fts5(
                title, abstract, content=papers, content_rowid=id
            )
        """)
        
        await self.db_conn.commit()
        
        # Cargar títulos existentes al Bloom Filter
        await self._load_bloom_filter()
        
        logger.info("SQLite database initialized", extra={"path": self.db_path})
    
    async def _load_bloom_filter(self):
        """Carga títulos existentes al Bloom Filter"""
        cursor = await self.db_conn.execute("SELECT title FROM papers")
        rows = await cursor.fetchall()
        
        for row in rows:
            self.bloom_add(row[0])
        
        logger.info(f"Bloom filter loaded with {len(rows)} papers")
    
    def _get_hashes(self, key: str) -> list:
        """Genera N hashes para Bloom filter"""
        return [mmh3.hash(key, i) % len(self.bloom) for i in range(self.hash_count)]
    
    def _normalize_title(self, title: str) -> str:
        """Normaliza título para comparación"""
        import re
        title = title.lower().strip()
        title = re.sub(r'[^\w\s]', '', title)
        title = re.sub(r'\s+', ' ', title)
        return title
    
    def _get_title_hash(self, title: str) -> str:
        """Genera hash único del título"""
        norm_title = self._normalize_title(title)
        return hashlib.sha256(norm_title.encode()).hexdigest()
    
    def bloom_check(self, title: str) -> bool:
        """
        Verifica si el paper PUEDE existir (probabilístico)
        False = definitivamente NO existe
        True = PUEDE existir (requiere verificación en DB)
        """
        norm_title = self._normalize_title(title)
        hashes = self._get_hashes(norm_title)
        return all(self.bloom[h] for h in hashes)
    
    def bloom_add(self, title: str):
        """Agrega título al Bloom filter"""
        norm_title = self._normalize_title(title)
        hashes = self._get_hashes(norm_title)
        for h in hashes:
            self.bloom[h] = 1
    
    async def exists(self, title: str, doi: str = None) -> bool:
        """
        Verifica si paper existe (2 capas)
        """
        # Capa 1: Bloom filter (rápido, in-memory)
        if not self.bloom_check(title):
            return False  # Definitivamente NO existe
        
        # Capa 2: SQLite (preciso, en disco)
        title_hash = self._get_title_hash(title)
        
        if doi:
            cursor = await self.db_conn.execute(
                "SELECT EXISTS(SELECT 1 FROM papers WHERE doi = ? OR title_hash = ? LIMIT 1)",
                (doi, title_hash)
            )
        else:
            cursor = await self.db_conn.execute(
                "SELECT EXISTS(SELECT 1 FROM papers WHERE title_hash = ? LIMIT 1)",
                (title_hash,)
            )
        
        result = await cursor.fetchone()
        return bool(result[0])
    
    async def add_paper(self, paper: dict, faiss_id: int) -> int:
        """
        Agrega paper a SQLite y Bloom filter
        Returns: paper_id
        """
        title_hash = self._get_title_hash(paper['title'])
        
        try:
            cursor = await self.db_conn.execute("""
                INSERT INTO papers (doi, title_hash, title, author, abstract, source, type, year, faiss_id)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(title_hash) DO UPDATE
                SET faiss_id = excluded.faiss_id
            """,
                (
                    paper.get('doi'),
                    title_hash,
                    paper['title'],
                    paper.get('author', 'Unknown'),
                    paper.get('abstract', ''),
                    paper.get('source', 'unknown'),
                    paper.get('type', 'article'),
                    paper.get('year'),
                    faiss_id
                )
            )
            
            await self.db_conn.commit()
            
            # Actualizar Bloom filter
            self.bloom_add(paper['title'])
            
            return cursor.lastrowid
        
        except Exception as e:
            logger.error(f"Error adding paper: {e}")
            await self.db_conn.rollback()
            raise
    
    async def batch_add_papers(self, papers: List[dict], faiss_start_id: int) -> int:
        """
        Agrega múltiples papers en transacción
        Returns: número de papers agregados
        """
        data = []
        for idx, paper in enumerate(papers):
            title_hash = self._get_title_hash(paper['title'])
            data.append((
                paper.get('doi'),
                title_hash,
                paper['title'],
                paper.get('author', 'Unknown'),
                paper.get('abstract', ''),
                paper.get('source', 'unknown'),
                paper.get('type', 'article'),
                paper.get('year'),
                faiss_start_id + idx
            ))
        
        try:
            await self.db_conn.executemany("""
                INSERT OR IGNORE INTO papers (doi, title_hash, title, author, abstract, source, type, year, faiss_id)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, data)
            
            await self.db_conn.commit()
            
            # Actualizar Bloom filter
            for paper in papers:
                self.bloom_add(paper['title'])
            
            logger.info(f"Batch added {len(papers)} papers")
            return len(papers)
        
        except Exception as e:
            logger.error(f"Error in batch add: {e}")
            await self.db_conn.rollback()
            raise
    
    async def get_paper_by_faiss_id(self, faiss_id: int) -> Optional[Dict]:
        """Obtiene paper por su FAISS ID"""
        cursor = await self.db_conn.execute(
            "SELECT * FROM papers WHERE faiss_id = ?",
            (faiss_id,)
        )
        row = await cursor.fetchone()
        
        if row:
            return {
                'id': row[0],
                'doi': row[1],
                'title': row[3],
                'author': row[4],
                'abstract': row[5],
                'source': row[6],
                'type': row[7],
                'year': row[8],
                'faiss_id': row[9]
            }
        return None
    
    async def batch_check_exists(self, papers: List[dict]) -> Dict[str, bool]:
        """
        Verifica existencia de múltiples papers en batch
        Returns: {title_hash: exists_bool}
        """
        results = {}
        
        # Filtro rápido con Bloom
        candidates = []
        for paper in papers:
            title_hash = self._get_title_hash(paper['title'])
            
            if not self.bloom_check(paper['title']):
                results[title_hash] = False
            else:
                candidates.append(title_hash)
        
        # Verificar candidatos en DB
        if candidates:
            placeholders = ','.join('?' * len(candidates))
            cursor = await self.db_conn.execute(
                f"SELECT title_hash FROM papers WHERE title_hash IN ({placeholders})",
                candidates
            )
            rows = await cursor.fetchall()
            existing = {row[0] for row in rows}
            
            for title_hash in candidates:
                results[title_hash] = title_hash in existing
        
        return results
    
    async def get_stats(self) -> Dict:
        """Estadísticas de la base de datos"""
        cursor = await self.db_conn.execute("SELECT COUNT(*) FROM papers")
        total = (await cursor.fetchone())[0]
        
        cursor = await self.db_conn.execute("SELECT COUNT(DISTINCT source) FROM papers")
        sources = (await cursor.fetchone())[0]
        
        return {
            'total_papers': total,
            'unique_sources': sources,
            'bloom_filter_size_mb': len(self.bloom) / 8 / 1024 / 1024
        }
    
    async def close(self):
        """Cierra conexión"""
        if self.db_conn:
            await self.db_conn.close()


# Instancia global
_deduplicator: Optional[PaperDeduplicator] = None


async def get_deduplicator() -> PaperDeduplicator:
    """Retorna instancia global del deduplicator"""
    global _deduplicator
    
    if _deduplicator is None:
        _deduplicator = PaperDeduplicator()
        await _deduplicator.init_db()
    
    return _deduplicator