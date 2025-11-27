"""
Similarity Service - Core plagiarism detection logic
"""
import logging
import asyncio
from typing import List, Tuple, Optional, Dict
from dataclasses import asdict

from app.models.search_result import SearchResult
from app.models.enums import PlagiarismLevel
from app.services.external_apis.api_manager import APIManager
from app.services.text_processing.preprocessor import TextPreprocessor
from app.services.text_processing.embeddings import EmbeddingService
from app.services.text_processing.chunker import TextChunker
from app.services.faiss_service import FAISSService
from app.services.deduplication_service import get_deduplicator
from app.core.extensions import get_faiss_index
from app.utils.cache import CacheManager

logger = logging.getLogger(__name__)


class SimilarityService:
    """
    Core service for similarity search and plagiarism detection
    
    Orchestrates:
    - Text preprocessing
    - Embedding generation
    - FAISS vector search
    - External API searches
    - Result deduplication
    - Similarity calculation
    """
    
    def __init__(self):
        self.api_manager = APIManager()
        self.preprocessor = TextPreprocessor()
        self.embedding_service = EmbeddingService()
        self.chunker = TextChunker()
        self.faiss_service = FAISSService()
        self.cache = CacheManager()
        
        logger.info("✅ SimilarityService initialized")
    
    # ==================== MAIN SEARCH ====================
    
    async def search_similarity(
        self,
        theme: str,
        idiom: str,
        texts: List[Tuple[str, str, str]],
        threshold: float = 0.70,
        use_faiss: bool = True,
        sources: Optional[List[str]] = None
    ) -> List[SearchResult]:
        """
        Search for similar academic papers
        
        Args:
            theme: Search theme/topic
            idiom: Language code (en, es, fr, etc.)
            texts: List of (page, paragraph, text) tuples
            threshold: Similarity threshold (0.0-1.0)
            use_faiss: Whether to use FAISS for fast search
            sources: Specific sources to search (optional)
        
        Returns:
            List of SearchResult objects
        """
        logger.info(
            f"Starting similarity search: theme='{theme}', texts={len(texts)}, "
            f"threshold={threshold}, faiss={use_faiss}"
        )
        
        all_results = []
        
        # Get deduplicator
        deduplicator = await get_deduplicator()
        
        for idx, (page, paragraph, text) in enumerate(texts):
            logger.debug(f"Processing text {idx + 1}/{len(texts)}")
            
            # 1. Preprocess text
            processed_text = self.preprocessor.preprocess(text, idiom)
            
            if len(processed_text.strip()) < 10:
                logger.warning(f"Text {idx} too short after preprocessing, skipping")
                continue
            
            # 2. Check cache
            cache_key = self.cache.generate_key(
                theme, processed_text, threshold, sources or []
            )
            
            cached_results = await self.cache.get_from_cache(cache_key)
            
            if cached_results:
                logger.debug(f"Cache HIT for text {idx}")
                
                # Convert cached dicts to SearchResult objects
                for result_dict in cached_results:
                    result = SearchResult(**result_dict)
                    all_results.append(result)
                
                continue
            
            logger.debug(f"Cache MISS for text {idx}")
            
            # 3. Search in FAISS first (if enabled)
            faiss_results = []
            
            if use_faiss:
                faiss_index = get_faiss_index()
                
                if faiss_index and faiss_index.index.ntotal > 0:
                    try:
                        # Generate embedding for query
                        query_embedding = self.embedding_service.encode_single(processed_text)
                        
                        # Search FAISS
                        faiss_results = self.faiss_service.search_similar(
                            query_embedding=query_embedding,
                            k=20,  # Get more results for better coverage
                            threshold=threshold
                        )
                        
                        logger.debug(f"FAISS returned {len(faiss_results)} results")
                    except Exception as e:
                        logger.error(f"FAISS search error: {e}", exc_info=True)
            
            # 4. Search external APIs
            api_results = await self.api_manager.search_all_sources(
                query=processed_text,
                theme=theme,
                sources=sources
            )
            
            logger.debug(f"External APIs returned {len(api_results)} papers")
            
            # 5. Combine results (FAISS + APIs)
            all_papers = faiss_results + api_results
            
            if not all_papers:
                logger.debug(f"No papers found for text {idx}")
                continue
            
            # 6. Deduplicate papers
            unique_papers = await deduplicator.deduplicate_papers(all_papers)
            
            logger.debug(
                f"Deduplication: {len(all_papers)} → {len(unique_papers)} papers"
            )
            
            # 7. Calculate similarity with embeddings
            matches = await self._calculate_similarities(
                original_text=text,
                processed_text=processed_text,
                papers=unique_papers,
                threshold=threshold,
                page=page,
                paragraph=paragraph
            )
            
            # 8. Save to FAISS for future searches
            if matches and use_faiss:
                await self._save_to_faiss(unique_papers, processed_text)
            
            # 9. Cache results
            if matches:
                await self.cache.save_to_cache(
                    cache_key,
                    [result.to_dict() for result in matches]
                )
            
            all_results.extend(matches)
        
        logger.info(
            f"Similarity search completed: {len(all_results)} results found"
        )
        
        return all_results
    
    # ==================== PLAGIARISM CHECK ====================
    
    async def check_plagiarism(
        self,
        theme: str,
        idiom: str,
        texts: List[Tuple[str, str, str]],
        threshold: float = 0.70,
        chunk_mode: str = 'sentences',
        min_chunk_words: int = 15,
        sources: Optional[List[str]] = None
    ) -> Dict:
        """
        Comprehensive plagiarism detection with text chunking
        
        Args:
            theme: Search theme
            idiom: Language code
            texts: List of (page, paragraph, text) tuples
            threshold: Similarity threshold
            chunk_mode: 'sentences' or 'sliding'
            min_chunk_words: Minimum words per chunk
            sources: Specific sources to search
        
        Returns:
            Dict with plagiarism analysis
        """
        logger.info(
            f"Starting plagiarism check: texts={len(texts)}, mode={chunk_mode}, "
            f"min_words={min_chunk_words}"
        )
        
        all_chunks = []
        chunk_map = {}  # Track which chunk belongs to which original text
        
        # 1. Chunk all texts
        for text_idx, (page, paragraph, text) in enumerate(texts):
            if chunk_mode == 'sentences':
                chunks = self.chunker.chunk_by_sentences(
                    text, 
                    min_words=min_chunk_words
                )
            elif chunk_mode == 'sliding':
                chunks = self.chunker.chunk_sliding_window(
                    text,
                    window_size=min_chunk_words,
                    overlap=5
                )
            else:
                # Default to sentences
                chunks = self.chunker.chunk_by_sentences(text, min_words=min_chunk_words)
            
            for chunk_idx, chunk_text in enumerate(chunks):
                all_chunks.append((page, paragraph, chunk_text))
                chunk_map[len(all_chunks) - 1] = {
                    'original_idx': text_idx,
                    'chunk_idx': chunk_idx,
                    'original_text': text
                }
        
        logger.info(f"Text chunked into {len(all_chunks)} segments")
        
        # 2. Search for each chunk
        results = await self.search_similarity(
            theme=theme,
            idiom=idiom,
            texts=all_chunks,
            threshold=threshold,
            use_faiss=True,
            sources=sources
        )
        
        # 3. Analyze results
        plagiarism_detected = len(results) > 0
        
        # Group by plagiarism level
        by_level = {
            PlagiarismLevel.HIGH.value: [],
            PlagiarismLevel.MEDIUM.value: [],
            PlagiarismLevel.LOW.value: []
        }
        
        for result in results:
            level = result.plagiarism_level
            if isinstance(level, PlagiarismLevel):
                level = level.value
            
            by_level[level].append(result.to_dict())
        
        # Summary
        summary = {
            PlagiarismLevel.HIGH.value: len(by_level[PlagiarismLevel.HIGH.value]),
            PlagiarismLevel.MEDIUM.value: len(by_level[PlagiarismLevel.MEDIUM.value]),
            PlagiarismLevel.LOW.value: len(by_level[PlagiarismLevel.LOW.value])
        }
        
        # Calculate coverage percentage
        chunks_with_matches = len(set(
            chunk_map[i]['original_idx'] 
            for i, result in enumerate(results) 
            if i < len(chunk_map)
        ))
        
        coverage_percent = (chunks_with_matches / len(texts) * 100) if texts else 0
        
        logger.info(
            f"Plagiarism check completed: detected={plagiarism_detected}, "
            f"high={summary[PlagiarismLevel.HIGH.value]}, "
            f"medium={summary[PlagiarismLevel.MEDIUM.value]}, "
            f"low={summary[PlagiarismLevel.LOW.value]}, "
            f"coverage={coverage_percent:.1f}%"
        )
        
        return {
            'plagiarism_detected': plagiarism_detected,
            'chunks_analyzed': len(all_chunks),
            'total_matches': len(results),
            'coverage_percent': round(coverage_percent, 2),
            'summary': summary,
            'by_level': by_level,
            'threshold_used': threshold,
            'faiss_enabled': True,
            'chunk_mode': chunk_mode
        }
    
    # ==================== HELPER METHODS ====================
    
    async def _calculate_similarities(
        self,
        original_text: str,
        processed_text: str,
        papers: List[Dict],
        threshold: float,
        page: str,
        paragraph: str
    ) -> List[SearchResult]:
        """
        Calculate semantic similarity between text and papers
        
        Args:
            original_text: Original unprocessed text
            processed_text: Preprocessed text
            papers: List of paper dicts
            threshold: Similarity threshold
            page: Page number
            paragraph: Paragraph number
        
        Returns:
            List of SearchResult objects above threshold
        """
        if not papers:
            return []
        
        # Extract paper texts (prefer abstract, fallback to title)
        paper_texts = [
            p.get('abstract', p.get('title', '')) for p in papers
        ]
        
        # Filter out empty texts
        valid_papers = [
            (paper, text) for paper, text in zip(papers, paper_texts)
            if text and len(text.strip()) > 0
        ]
        
        if not valid_papers:
            logger.warning("No valid paper texts to compare")
            return []
        
        papers, paper_texts = zip(*valid_papers)
        papers = list(papers)
        paper_texts = list(paper_texts)
        
        # Calculate embeddings
        try:
            query_embedding = self.embedding_service.encode_single(processed_text)
            paper_embeddings = self.embedding_service.encode(paper_texts)
        except Exception as e:
            logger.error(f"Error generating embeddings: {e}", exc_info=True)
            return []
        
        # Calculate cosine similarities
        from sklearn.metrics.pairwise import cosine_similarity
        import numpy as np
        
        similarities = cosine_similarity(
            query_embedding.reshape(1, -1),
            paper_embeddings
        )[0]
        
        # Filter by threshold and create results
        results = []
        
        for idx, similarity in enumerate(similarities):
            if similarity >= threshold:
                paper = papers[idx]
                
                # Determine plagiarism level using enum
                level = PlagiarismLevel.from_similarity(similarity)
                
                result = SearchResult(
                    fuente=paper.get('source', 'unknown'),
                    texto_original=original_text,
                    texto_encontrado=paper.get('abstract', paper.get('title', '')),
                    porcentaje_match=float(similarity),
                    documento_coincidente=paper.get('title', 'Unknown'),
                    autor=paper.get('authors', 'Unknown'),
                    type_document=paper.get('type', 'article'),
                    plagiarism_level=level.value,
                    publication_date=paper.get('date'),
                    doi=paper.get('doi'),
                    url=paper.get('url')
                )
                
                results.append(result)
        
        # Sort by similarity (highest first)
        results.sort(key=lambda r: r.porcentaje_match, reverse=True)
        
        return results
    
    async def _save_to_faiss(self, papers: List[Dict], query_text: str):
        """
        Save papers to FAISS for future searches
        
        Args:
            papers: List of paper dicts
            query_text: Query that found these papers
        """
        try:
            # Filter papers that might not be in FAISS yet
            new_papers = []
            
            for paper in papers:
                # Check if paper has content hash (from deduplicator)
                if not paper.get('content_hash'):
                    new_papers.append(paper)
            
            if not new_papers:
                logger.debug("All papers already in FAISS")
                return
            
            # Generate embeddings
            paper_texts = [
                p.get('abstract', p.get('title', ''))
                for p in new_papers
            ]
            
            embeddings = self.embedding_service.encode(paper_texts)
            
            # Add to FAISS
            await self.faiss_service.add_papers(embeddings, new_papers)
            
            logger.debug(f"Added {len(new_papers)} new papers to FAISS")
        
        except Exception as e:
            logger.error(f"Error saving to FAISS: {e}", exc_info=True)
    
    # ==================== BATCH PROCESSING ====================
    
    async def search_similarity_batch(
        self,
        requests: List[Dict]
    ) -> List[List[SearchResult]]:
        """
        Process multiple search requests in batch
        
        Args:
            requests: List of search request dicts, each containing:
                - theme: str
                - idiom: str
                - texts: List[Tuple]
                - threshold: float (optional)
                - use_faiss: bool (optional)
                - sources: List[str] (optional)
        
        Returns:
            List of result lists (one per request)
        """
        logger.info(f"Starting batch similarity search: {len(requests)} requests")
        
        tasks = [
            self.search_similarity(
                theme=req['theme'],
                idiom=req['idiom'],
                texts=req['texts'],
                threshold=req.get('threshold', 0.70),
                use_faiss=req.get('use_faiss', True),
                sources=req.get('sources')
            )
            for req in requests
        ]
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Handle exceptions
        final_results = []
        for idx, result in enumerate(results):
            if isinstance(result, Exception):
                logger.error(f"Request {idx} failed: {result}")
                final_results.append([])
            else:
                final_results.append(result)
        
        logger.info(f"Batch search completed: {len(final_results)} results")
        
        return final_results