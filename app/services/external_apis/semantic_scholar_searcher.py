"""
Semantic Scholar Searcher
"""
from typing import Dict, List, Tuple
from app.services.external_apis.base_searcher import BaseSearcher


class SemanticScholarSearcher(BaseSearcher):
    """Searcher for Semantic Scholar API"""
    
    def get_source_name(self) -> str:
        return "semantic_scholar"
    
    def build_request(self, query: str, theme: str) -> Tuple[str, Dict, Dict]:
        url = "https://api.semanticscholar.org/graph/v1/paper/search"
        
        params = {
            "query": f"{theme} {query}",
            "limit": self.get_max_results(),
            "fields": "title,authors,abstract,publicationDate,externalIds,url"
        }
        
        headers = {}
        
        return url, params, headers
    
    def parse_response(self, data: Dict) -> List[Dict]:
        papers = []
        
        for item in data.get('data', []):
            # Extract authors
            authors_list = item.get('authors', [])
            authors = ", ".join([a.get('name', '') for a in authors_list])
            
            if not authors:
                authors = "Unknown"
            
            # Extract DOI
            external_ids = item.get('externalIds', {})
            doi = external_ids.get('DOI', '')
            
            paper = {
                'title': item.get('title', 'Untitled'),
                'authors': authors,
                'abstract': item.get('abstract', ''),
                'doi': doi,
                'url': item.get('url'),
                'date': item.get('publicationDate'),
                'type': 'article',
                'source': 'semantic_scholar'
            }
            
            papers.append(paper)
        
        return papers