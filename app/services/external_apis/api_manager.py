"""
API Manager - Orchestrates all searchers
"""
import logging
import asyncio
from typing import List, Dict, Optional

from app.core.extensions import get_http_client
from app.services.external_apis.crossref_searcher import CrossrefSearcher
from app.services.external_apis.pubmed_searcher import PubMedSearcher
from app.services.external_apis.semantic_scholar_searcher import SemanticScholarSearcher
from app.services.external_apis.arxiv_searcher import ArXivSearcher
from app.services.external_apis.openalex_searcher import OpenAlexSearcher
from app.services.external_apis.europepmc_searcher import EuropePMCSearcher
from app.services.external_apis.doaj_searcher import DOAJSearcher
from app.services.external_apis.zenodo_searcher import ZenodoSearcher
from app.services.external_apis.core_searcher import CORESearcher
from app.services.external_apis.internet_archive_searcher import InternetArchiveScholarSearcher
from app.services.external_apis.unpaywall_searcher import UnpaywallSearcher
from app.services.external_apis.hal_searcher import HALSearcher

logger = logging.getLogger(__name__)


class APIManager:
    """Manages all external API searchers"""
    
    def __init__(self):
        """Initialize all searchers"""
        self.searchers = {
            'crossref': CrossrefSearcher(),
            'pubmed': PubMedSearcher(),
            'semantic_scholar': SemanticScholarSearcher(),
            'arxiv': ArXivSearcher(),
            'openalex': OpenAlexSearcher(),
            'europepmc': EuropePMCSearcher(),
            'doaj': DOAJSearcher(),
            'zenodo': ZenodoSearcher(),
            'core': CORESearcher(),
            'internet_archive': InternetArchiveScholarSearcher(),
            'unpaywall': UnpaywallSearcher(),
            'hal': HALSearcher(),
        }
        
        logger.info(f"✅ APIManager initialized with {len(self.searchers)} searchers")
    
    async def search_all_sources(
        self,
        query: str,
        theme: str,
        sources: Optional[List[str]] = None
    ) -> List[Dict]:
        """
        Search all sources in parallel
        
        Args:
            query: Search query
            theme: Search theme
            sources: Specific sources to search (None = all)
        
        Returns:
            Combined list of papers from all sources
        """
        http_client = get_http_client()
        
        if not http_client:
            logger.error("HTTP client not available")
            return []
        
        # Determine which sources to search
        if sources:
            active_searchers = {
                k: v for k, v in self.searchers.items()
                if k in sources
            }
        else:
            active_searchers = self.searchers
        
        if not active_searchers:
            logger.warning("No searchers available")
            return []
        
        # Search all sources concurrently
        tasks = [
            searcher.search(query, theme, http_client)
            for searcher in active_searchers.values()
        ]
        
        responses = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Collect papers
        all_papers = []
        
        for idx, response in enumerate(responses):
            if isinstance(response, Exception):
                logger.error(f"Searcher {idx} failed: {response}")
                continue
            
            if response.success:
                all_papers.extend(response.papers)
                
                logger.debug(
                    f"{response.source}: {len(response.papers)} papers"
                )
            else:
                logger.warning(
                    f"{response.source} failed: {response.error}"
                )
        
        logger.info(
            f"API search completed: {len(all_papers)} total papers from "
            f"{len(active_searchers)} sources"
        )
        
        return all_papers
    
    def get_available_sources(self) -> List[str]:
        """Get list of available source names"""
        return list(self.searchers.keys())
    
    def get_searcher(self, source: str):
        """Get specific searcher by name"""
        return self.searchers.get(source)