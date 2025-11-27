"""
Unpaywall Searcher - Open access versions of scholarly articles
"""
from typing import Dict, List, Tuple
from app.services.external_apis.base_searcher import BaseSearcher


class UnpaywallSearcher(BaseSearcher):
    """
    Searcher for Unpaywall API
    
    Unpaywall: Find open access versions of paywalled research papers
    https://unpaywall.org
    
    Note: This searcher is different - it takes DOIs and finds OA versions
    For general search, we'll use a search proxy or skip it
    """
    
    def get_source_name(self) -> str:
        return "unpaywall"
    
    def build_request(self, query: str, theme: str) -> Tuple[str, Dict, Dict]:
        """
        Build Unpaywall request
        
        Note: Unpaywall doesn't have a search API, only DOI lookup
        We'll return empty to skip this in general search
        
        API Docs: https://unpaywall.org/products/api
        """
        # Unpaywall doesn't support general search
        # Only DOI-based lookup
        
        self.logger.debug(
            "Unpaywall doesn't support general search, skipping"
        )
        
        return "", {}, {}
    
    def parse_response(self, data: Dict) -> List[Dict]:
        """Parse Unpaywall response (not used for general search)"""
        return []
    
    def lookup_doi(self, doi: str) -> Dict:
        """
        Look up open access version by DOI
        
        Args:
            doi: DOI to look up
        
        Returns:
            Paper dict with OA link if available
        
        This is a specialized method for DOI lookups
        """
        import httpx
        
        url = f"https://api.unpaywall.org/v2/{doi}"
        
        params = {
            "email": "admin@xplagiax.com"  # Required by Unpaywall
        }
        
        try:
            response = httpx.get(url, params=params, timeout=5.0)
            response.raise_for_status()
            
            data = response.json()
            
            # Check if OA version exists
            is_oa = data.get('is_oa', False)
            
            if is_oa:
                best_oa = data.get('best_oa_location', {})
                
                return {
                    'doi': doi,
                    'is_oa': True,
                    'oa_url': best_oa.get('url'),
                    'oa_version': best_oa.get('version'),
                    'license': best_oa.get('license')
                }
            
            return {'doi': doi, 'is_oa': False}
        
        except Exception as e:
            self.logger.error(f"Error looking up DOI {doi}: {e}")
            return {'doi': doi, 'is_oa': False, 'error': str(e)}