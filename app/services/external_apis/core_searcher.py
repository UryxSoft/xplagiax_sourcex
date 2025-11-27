"""
CORE Searcher - Aggregator of open access research papers
"""
import os
from typing import Dict, List, Tuple
from app.services.external_apis.base_searcher import BaseSearcher


class CORESearcher(BaseSearcher):
    """
    Searcher for CORE API
    
    CORE: World's largest collection of open access research papers
    https://core.ac.uk
    
    Note: Requires API key (free registration)
    """
    
    def get_source_name(self) -> str:
        return "core"
    
    def build_request(self, query: str, theme: str) -> Tuple[str, Dict, Dict]:
        """
        Build CORE API request
        
        API Docs: https://core.ac.uk/services/api
        """
        # Get API key from environment
        api_key = os.getenv('CORE_API_KEY')
        
        if not api_key or api_key == "YOUR_API_KEY":
            self.logger.warning(
                "CORE API key not configured. Set CORE_API_KEY environment variable."
            )
            # Return empty request that will fail gracefully
            return "", {}, {}
        
        url = "https://api.core.ac.uk/v3/search/works"
        
        # Build query
        search_query = f"{theme} {query}"
        
        params = {
            "q": search_query,
            "limit": self.get_max_results()
        }
        
        headers = {
            "Authorization": f"Bearer {api_key}"
        }
        
        return url, params, headers
    
    def parse_response(self, data: Dict) -> List[Dict]:
        """
        Parse CORE response
        
        Response structure:
        {
            "results": [
                {
                    "title": "...",
                    "authors": ["...", "..."],
                    "abstract": "...",
                    "doi": "...",
                    "downloadUrl": "...",
                    "publishedDate": "..."
                }
            ]
        }
        """
        papers = []
        
        results = data.get('results', [])
        
        for item in results:
            # Extract title
            title = item.get('title', 'Untitled')
            
            # Extract authors
            author_list = item.get('authors', [])
            
            if isinstance(author_list, list):
                # Handle list of author objects or strings
                authors = ", ".join([
                    author if isinstance(author, str) else author.get('name', '')
                    for author in author_list
                ])
            else:
                authors = str(author_list) if author_list else "Unknown"
            
            if not authors:
                authors = "Unknown"
            
            # Extract abstract
            abstract = item.get('abstract', '')
            
            # Extract DOI
            doi = item.get('doi', '')
            
            # Extract URL
            url = item.get('downloadUrl') or item.get('sourceFulltextUrls', [None])[0]
            
            # Extract publication date
            pub_date = item.get('publishedDate')
            
            # Document type
            doc_type = item.get('documentType', 'article')
            
            paper = {
                'title': title,
                'authors': authors,
                'abstract': abstract,
                'doi': doi,
                'url': url,
                'date': pub_date,
                'type': doc_type,
                'source': 'core'
            }
            
            papers.append(paper)
        
        return papers
    
    def get_timeout(self) -> float:
        return 15.0  # CORE can be slower