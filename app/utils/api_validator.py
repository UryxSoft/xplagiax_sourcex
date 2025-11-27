"""
API Validator - Validate external APIs health
"""
import logging
import asyncio
from typing import Dict, List
from dataclasses import dataclass
import httpx

logger = logging.getLogger(__name__)


@dataclass
class APIHealthMetric:
    """Health metric for an API"""
    source: str
    available: bool
    response_time_ms: float
    error: str = None


class APIValidator:
    """Validate external APIs health"""
    
    def __init__(self):
        """Initialize API validator"""
        self.endpoints = {
            'crossref': 'https://api.crossref.org/works?rows=1',
            'pubmed': 'https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi?db=pubmed&retmax=1&retmode=json&term=test',
            'semantic_scholar': 'https://api.semanticscholar.org/graph/v1/paper/search?query=test&limit=1',
            'arxiv': 'http://export.arxiv.org/api/query?search_query=test&max_results=1'
        }
        
        self.metrics: Dict[str, APIHealthMetric] = {}
    
    async def validate_api(
        self,
        source: str,
        http_client: httpx.AsyncClient
    ) -> APIHealthMetric:
        """
        Validate single API
        
        Args:
            source: API source name
            http_client: HTTP client
        
        Returns:
            APIHealthMetric
        """
        if source not in self.endpoints:
            return APIHealthMetric(
                source=source,
                available=False,
                response_time_ms=0,
                error="Unknown API"
            )
        
        url = self.endpoints[source]
        
        try:
            import time
            start = time.time()
            
            response = await http_client.get(url, timeout=5.0)
            
            elapsed_ms = (time.time() - start) * 1000
            
            available = response.status_code == 200
            error = None if available else f"HTTP {response.status_code}"
            
            metric = APIHealthMetric(
                source=source,
                available=available,
                response_time_ms=round(elapsed_ms, 2),
                error=error
            )
            
            self.metrics[source] = metric
            
            return metric
        
        except httpx.TimeoutException:
            metric = APIHealthMetric(
                source=source,
                available=False,
                response_time_ms=5000,
                error="Timeout"
            )
            self.metrics[source] = metric
            return metric
        
        except Exception as e:
            metric = APIHealthMetric(
                source=source,
                available=False,
                response_time_ms=0,
                error=str(e)
            )
            self.metrics[source] = metric
            return metric
    
    async def validate_all_apis(self, http_client: httpx.AsyncClient):
        """Validate all APIs concurrently"""
        tasks = [
            self.validate_api(source, http_client)
            for source in self.endpoints
        ]
        
        await asyncio.gather(*tasks, return_exceptions=True)
    
    def get_health_report(self) -> Dict:
        """
        Get health report for all APIs
        
        Returns:
            Dict with summary and detailed metrics
        """
        available_count = sum(
            1 for m in self.metrics.values() if m.available
        )
        
        total_count = len(self.metrics)
        
        # Calculate average response time for available APIs
        available_times = [
            m.response_time_ms
            for m in self.metrics.values()
            if m.available
        ]
        
        avg_response_time = (
            sum(available_times) / len(available_times)
            if available_times else 0
        )
        
        return {
            'summary': {
                'total_apis': total_count,
                'available': available_count,
                'unavailable': total_count - available_count,
                'overall_health': 'healthy' if available_count == total_count else 'degraded',
                'avg_response_time_ms': round(avg_response_time, 2)
            },
            'apis': {
                source: {
                    'available': metric.available,
                    'response_time_ms': metric.response_time_ms,
                    'error': metric.error
                }
                for source, metric in self.metrics.items()
            }
        }
    
    def get_failing_apis(self) -> List[str]:
        """
        Get list of failing API sources
        
        Returns:
            List of source names
        """
        return [
            source for source, metric in self.metrics.items()
            if not metric.available
        ]


# Global validator instance
_validator = APIValidator()


def get_api_validator() -> APIValidator:
    """
    Get global validator instance
    
    Returns:
        APIValidator singleton
    """
    return _validator