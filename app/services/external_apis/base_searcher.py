"""
Base Searcher - Template Method Pattern for API searchers
"""
import logging
from abc import ABC, abstractmethod
from typing import Optional, Dict, List, Tuple
from dataclasses import dataclass
import httpx

from app.utils.rate_limiter import RateLimiter

logger = logging.getLogger(__name__)


@dataclass
class SearchResponse:
    """Standardized search response"""
    papers: List[Dict]
    source: str
    success: bool
    error: Optional[str] = None


class BaseSearcher(ABC):
    """
    Abstract base class for academic API searchers
    
    Template Method Pattern: Defines the skeleton of the search algorithm
    """
    
    def __init__(self):
        self.rate_limiter = RateLimiter()
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
    
    # ==================== TEMPLATE METHOD ====================
    
    async def search(
        self,
        query: str,
        theme: str,
        http_client: httpx.AsyncClient
    ) -> SearchResponse:
        """
        Template method: Defines the search algorithm skeleton
        
        This method orchestrates the search flow and should NOT be overridden.
        Subclasses customize behavior by overriding hook methods.
        
        Args:
            query: Processed search query
            theme: Search theme/topic
            http_client: Async HTTP client
        
        Returns:
            SearchResponse with papers or error
        """
        source_name = self.get_source_name()
        
        try:
            # 1. Check rate limit
            if not await self.rate_limiter.check_limit(source_name):
                self.logger.warning(f"Rate limit exceeded for {source_name}")
                return SearchResponse(
                    papers=[],
                    source=source_name,
                    success=False,
                    error="Rate limit exceeded"
                )
            
            # 2. Build request (implemented by subclass)
            url, params, headers = self.build_request(query, theme)
            
            self.logger.debug(
                f"Searching {source_name}: url={url}, params={params}"
            )
            
            # 3. Make HTTP request
            timeout = self.get_timeout()
            
            response = await http_client.get(
                url,
                params=params,
                headers=headers,
                timeout=timeout
            )
            
            response.raise_for_status()
            
            # 4. Parse response (implemented by subclass)
            data = response.json()
            papers = self.parse_response(data)
            
            self.logger.info(
                f"{source_name} returned {len(papers)} papers"
            )
            
            return SearchResponse(
                papers=papers,
                source=source_name,
                success=True
            )
        
        except httpx.HTTPStatusError as e:
            self.logger.warning(
                f"{source_name} HTTP error: {e.response.status_code}"
            )
            return SearchResponse(
                papers=[],
                source=source_name,
                success=False,
                error=f"HTTP {e.response.status_code}"
            )
        
        except httpx.TimeoutException:
            self.logger.warning(f"{source_name} timeout")
            return SearchResponse(
                papers=[],
                source=source_name,
                success=False,
                error="Timeout"
            )
        
        except Exception as e:
            self.logger.error(
                f"{source_name} unexpected error: {e}",
                exc_info=True
            )
            return SearchResponse(
                papers=[],
                source=source_name,
                success=False,
                error=str(e)
            )
    
    # ==================== ABSTRACT METHODS (MUST IMPLEMENT) ====================
    
    @abstractmethod
    def get_source_name(self) -> str:
        """Return the source name (e.g., 'crossref', 'pubmed')"""
        pass
    
    @abstractmethod
    def build_request(self, query: str, theme: str) -> Tuple[str, Dict, Dict]:
        """
        Build HTTP request components
        
        Returns:
            Tuple of (url, params, headers)
        """
        pass
    
    @abstractmethod
    def parse_response(self, data: Dict) -> List[Dict]:
        """
        Parse API response into standardized paper format
        
        Returns:
            List of paper dicts with keys:
            - title: str
            - authors: str
            - abstract: str (optional)
            - doi: str (optional)
            - url: str (optional)
            - date: str (optional)
            - type: str
            - source: str
        """
        pass
    
    # ==================== HOOK METHODS (OPTIONAL OVERRIDE) ====================
    
    def get_timeout(self) -> float:
        """Override to customize timeout (default: 10s)"""
        return 10.0
    
    def get_max_results(self) -> int:
        """Override to customize max results (default: 5)"""
        return 5