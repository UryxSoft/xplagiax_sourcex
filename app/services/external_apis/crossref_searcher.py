"""
Crossref Searcher - Implementation for Crossref API
"""
from typing import Dict, List, Tuple
from app.services.external_apis.base_searcher import BaseSearcher


class CrossrefSearcher(BaseSearcher):
    """Searcher for Crossref API"""
    
    def get_source_name(self) -> str:
        return "crossref"
    
    def build_request(self, query: str, theme: str) -> Tuple[str, Dict, Dict]:
        url = "https://api.crossref.org/works"
        
        params = {
            "query": f"{theme} {query}",
            "rows": self.get_max_results()
        }
        
        headers = {}
        
        return url, params, headers
    
    def parse_response(self, data: Dict) -> List[Dict]:
        papers = []
        
        items = data.get('message', {}).get('items', [])
        
        for item in items:
            # Extract authors
            authors_list = item.get('author', [])
            authors = ", ".join([
                f"{a.get('given', '')} {a.get('family', '')}".strip()
                for a in authors_list
            ])
            
            if not authors:
                authors = "Unknown"
            
            # Extract title
            title_list = item.get('title', [])
            title = title_list[0] if title_list else "Untitled"
            
            # Extract abstract (if available)
            abstract = item.get('abstract', '')
            
            # Extract DOI
            doi = item.get('DOI', '')
            
            # Build URL
            url = f"https://doi.org/{doi}" if doi else None
            
            # Extract date
            date_parts = item.get('published-print', {}).get('date-parts', [[]])[0]
            date = '-'.join(map(str, date_parts)) if date_parts else None
            
            paper = {
                'title': title,
                'authors': authors,
                'abstract': abstract,
                'doi': doi,
                'url': url,
                'date': date,
                'type': item.get('type', 'article'),
                'source': 'crossref'
            }
            
            papers.append(paper)
        
        return papers